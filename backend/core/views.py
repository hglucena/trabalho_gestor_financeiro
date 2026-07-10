import csv
import io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import connections
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import viewsets, generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import (
    AutorizacaoConsultor,
    Categoria,
    Conta,
    ContaAPagar,
    DivisaoDespesa,
    Grupo,
    MembroGrupo,
    Mesada,
    MetaEconomia,
    Orcamento,
    Recomendacao,
    Transacao,
    Usuario,
)
from core.permissions import (
    IsAdminOnly,
    IsAutorizacaoOwner,
    IsConsultorAutorizado,
    IsConsultorPodeComentar,
    IsDonoOuGestorDaMesada,
    IsGestorDaMesada,
    IsGestorDoGrupoByKwarg,
    IsOwner,
    IsOwnerOrGestorForWrite,
    IsOwnerOrGrupoMemberRead,
    IsOwnerOrReadOnly,
    NaoAdmin,
)
from core.serializers import (
    AutorizacaoConsultorSerializer,
    CadastroSerializer,
    CategoriaAdminSerializer,
    CategoriaSerializer,
    ContaAPagarSerializer,
    ContaSerializer,
    DivisaoDespesaSerializer,
    GrupoSerializer,
    MembroGrupoSerializer,
    MesadaSerializer,
    MetaEconomiaSerializer,
    OrcamentoSerializer,
    RecomendacaoSerializer,
    TransacaoCreateSerializer,
    TransacaoSerializer,
    UsuarioAdminSerializer,
    UsuarioSerializer,
)


# ══════════════════════════════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════════════════════════════

def health_check(request):
    db_ok = False
    try:
        connections["default"].cursor()
        db_ok = True
    except Exception:
        pass
    return JsonResponse({
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    })


class RegistroView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = CadastroSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=usuario)
        return Response({
            "token": token.key,
            "usuario": UsuarioSerializer(usuario).data,
        })


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ══════════════════════════════════════════════════════════════════════════
# Usuário (Admin)
# ══════════════════════════════════════════════════════════════════════════

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsAdminOnly]


# ══════════════════════════════════════════════════════════════════════════
# Conta
# ══════════════════════════════════════════════════════════════════════════

class ContaViewSet(viewsets.ModelViewSet):
    serializer_class = ContaSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsOwner]

    def get_queryset(self):
        return Conta.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# ══════════════════════════════════════════════════════════════════════════
# Categoria
# ══════════════════════════════════════════════════════════════════════════

class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.papel_sistema == "admin":
            return Categoria.objects.filter(usuario__isnull=True)
        return Categoria.objects.filter(
            Q(usuario=user) | Q(padrao=True)
        )

    def get_serializer_class(self):
        if self.request.user.papel_sistema == "admin":
            return CategoriaAdminSerializer
        return CategoriaSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            if self.request.user.papel_sistema == "admin":
                return [permissions.IsAuthenticated(), IsAdminOnly()]
            return [permissions.IsAuthenticated(), NaoAdmin(), IsOwner()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        if self.request.user.papel_sistema == "admin":
            serializer.save(usuario=None, padrao=True)
        else:
            serializer.save(usuario=self.request.user)


# ══════════════════════════════════════════════════════════════════════════
# Grupo
# ══════════════════════════════════════════════════════════════════════════

class GrupoViewSet(viewsets.ModelViewSet):
    serializer_class = GrupoSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        return Grupo.objects.filter(
            membros__usuario=self.request.user
        ).exclude(
            membros__usuario=self.request.user, membros__papel_no_grupo="dependente"
        ).distinct()

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsOwnerOrReadOnly()]
        return [permissions.IsAuthenticated(), NaoAdmin()]

    def perform_create(self, serializer):
        grupo = serializer.save(responsavel=self.request.user)
        MembroGrupo.objects.create(
            grupo=grupo,
            usuario=self.request.user,
            papel_no_grupo="responsavel",
        )

    @action(detail=True, methods=["get"])
    def saldo(self, request, pk=None):
        grupo = self.get_object()
        transacoes = Transacao.objects.filter(grupo=grupo)
        total_receitas = sum(t.valor for t in transacoes if t.tipo == "receita")
        total_despesas = sum(t.valor for t in transacoes if t.tipo == "despesa")
        return Response({
            "grupo": grupo.nome,
            "total_receitas": total_receitas,
            "total_despesas": total_despesas,
            "saldo": total_receitas - total_despesas,
            "quantidade_membros": MembroGrupo.objects.filter(grupo=grupo).count(),
        })

    @action(detail=True, methods=["get"])
    def quem_deve_a_quem(self, request, pk=None):
        grupo = self.get_object()
        membros = MembroGrupo.objects.filter(grupo=grupo).select_related("usuario")
        transacoes = Transacao.objects.filter(grupo=grupo).prefetch_related("divisoes")

        balances = defaultdict(Decimal)
        for m in membros:
            balances[m.usuario_id] = Decimal("0")

        for t in transacoes:
            balances[t.usuario_id] += t.valor
            for div in t.divisoes.all():
                balances[div.participante_id] -= div.valor_devido

        resultado = []
        for m in membros:
            saldo_liquido = balances[m.usuario_id]
            if saldo_liquido > 0:
                status = "a_receber"
            elif saldo_liquido < 0:
                status = "deve"
            else:
                status = "quitado"
            resultado.append({
                "usuario_id": m.usuario_id,
                "nome": m.usuario.nome,
                "papel": m.papel_no_grupo,
                "saldo": float(round(saldo_liquido, 2)),
                "status": status,
            })

        return Response({
            "grupo": grupo.nome,
            "membros": resultado,
        })

    @action(detail=True, methods=["get"])
    def orcamento_resumo(self, request, pk=None):
        grupo = self.get_object()
        orcamentos = Orcamento.objects.filter(grupo=grupo).select_related("categoria")

        resumo = []
        for orc in orcamentos:
            realizado = Transacao.objects.filter(
                grupo=grupo, categoria=orc.categoria, tipo="despesa",
            ).aggregate(total=Sum("valor"))["total"] or 0
            resumo.append({
                "categoria": orc.categoria.nome,
                "periodo": str(orc.periodo),
                "previsto": float(orc.valor_limite),
                "realizado": float(realizado),
                "diferenca": float(orc.valor_limite - realizado),
            })

        return Response({
            "grupo": grupo.nome,
            "orcamentos": resumo,
        })


# ══════════════════════════════════════════════════════════════════════════
# MembroGrupo (aninhado em grupo)
# ══════════════════════════════════════════════════════════════════════════

class MembroGrupoViewSet(viewsets.ModelViewSet):
    serializer_class = MembroGrupoSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsGestorDoGrupoByKwarg]

    def get_queryset(self):
        return MembroGrupo.objects.filter(grupo_id=self.kwargs["grupo_pk"])

    def perform_create(self, serializer):
        serializer.save(grupo_id=self.kwargs["grupo_pk"])


# ══════════════════════════════════════════════════════════════════════════
# Transação
# ══════════════════════════════════════════════════════════════════════════

class TransacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        user = self.request.user
        is_dependente = MembroGrupo.objects.filter(
            usuario=user, papel_no_grupo="dependente"
        ).exists()
        if is_dependente:
            queryset = Transacao.objects.filter(usuario=user)
        else:
            grupos_ids = MembroGrupo.objects.filter(usuario=user).values_list("grupo_id", flat=True)
            queryset = Transacao.objects.filter(
                Q(usuario=user) | Q(grupo_id__in=grupos_ids)
            )
        return self._aplicar_filtros(queryset).order_by("-data")

    def _aplicar_filtros(self, queryset):
        params = self.request.query_params
        data_inicio = self._parse_data(params.get("data_inicio"))
        data_fim = self._parse_data(params.get("data_fim"))
        if data_inicio:
            queryset = queryset.filter(data__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__date__lte=data_fim)
        if params.get("categoria", "").isdigit():
            queryset = queryset.filter(categoria_id=params["categoria"])
        if params.get("tipo") in ("receita", "despesa"):
            queryset = queryset.filter(tipo=params["tipo"])
        if params.get("grupo", "").isdigit():
            queryset = queryset.filter(grupo_id=params["grupo"])
        return queryset

    @staticmethod
    def _parse_data(valor):
        if not valor:
            return None
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            return None

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TransacaoCreateSerializer
        return TransacaoSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsOwnerOrGrupoMemberRead()]
        return [permissions.IsAuthenticated(), NaoAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        tipo = serializer.validated_data.get("tipo", "")
        valor = serializer.validated_data.get("valor", 0)

        if tipo == "despesa":
            mesada = Mesada.objects.filter(dependente=user).first()
            if mesada:
                mesada.recarregar_se_devido()
                if valor > mesada.saldo_atual:
                    raise PermissionDenied(
                        f"Gasto acima do limite da mesada. Saldo disponível: R$ {mesada.saldo_atual}"
                    )

        transacao = serializer.save(usuario=user)

        if transacao.tipo == "despesa":
            mesada = Mesada.objects.filter(dependente=user).first()
            if mesada:
                mesada.saldo_atual -= transacao.valor
                mesada.save(update_fields=["saldo_atual"])

    @action(detail=False, methods=["post"])
    def importar_csv(self, request):
        """Importa transações em lote de um CSV com colunas: data,descricao,valor,tipo,categoria."""
        user = request.user
        if MembroGrupo.objects.filter(usuario=user, papel_no_grupo="dependente").exists():
            raise PermissionDenied("Dependentes não podem importar extrato.")

        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return Response({"detail": "Envie o arquivo CSV no campo 'arquivo'."}, status=status.HTTP_400_BAD_REQUEST)

        conta = Conta.objects.filter(id=request.data.get("conta"), usuario=user).first()
        if not conta:
            return Response({"detail": "Informe uma conta válida sua no campo 'conta'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            texto = arquivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "O arquivo deve estar em UTF-8."}, status=status.HTTP_400_BAD_REQUEST)

        importadas = 0
        erros = []
        for numero, linha in enumerate(csv.DictReader(io.StringIO(texto)), start=2):
            try:
                transacao = self._linha_para_transacao(linha, user, conta)
            except ValueError as exc:
                erros.append({"linha": numero, "erro": str(exc)})
                continue
            try:
                transacao.save()
            except ValidationError as exc:
                erros.append({"linha": numero, "erro": "; ".join(exc.messages)})
                continue
            importadas += 1

        return Response({"importadas": importadas, "erros": erros}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _linha_para_transacao(linha, user, conta):
        data_txt = (linha.get("data") or "").strip()
        data = None
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                data = datetime.strptime(data_txt, formato)
                break
            except ValueError:
                continue
        if data is None:
            raise ValueError(f"Data inválida: '{data_txt}' (use AAAA-MM-DD ou DD/MM/AAAA).")
        data = timezone.make_aware(data)

        try:
            valor = Decimal((linha.get("valor") or "").strip().replace(",", "."))
        except InvalidOperation:
            raise ValueError(f"Valor inválido: '{linha.get('valor')}'.")
        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")

        tipo = (linha.get("tipo") or "despesa").strip().lower()
        if tipo not in ("receita", "despesa"):
            raise ValueError(f"Tipo inválido: '{tipo}' (use receita ou despesa).")

        nome_categoria = (linha.get("categoria") or "").strip()
        if not nome_categoria:
            raise ValueError("A coluna 'categoria' é obrigatória.")
        categoria = Categoria.objects.filter(
            Q(usuario=user) | Q(padrao=True), nome__iexact=nome_categoria
        ).first()
        if categoria is None:
            categoria = Categoria.objects.create(usuario=user, nome=nome_categoria, tipo=tipo)

        return Transacao(
            usuario=user,
            conta=conta,
            categoria=categoria,
            tipo=tipo,
            valor=valor,
            descricao=(linha.get("descricao") or "").strip(),
            data=data,
        )


# ══════════════════════════════════════════════════════════════════════════
# Orçamento
# ══════════════════════════════════════════════════════════════════════════

class OrcamentoViewSet(viewsets.ModelViewSet):
    serializer_class = OrcamentoSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        user = self.request.user
        is_dependente = MembroGrupo.objects.filter(
            usuario=user, papel_no_grupo="dependente"
        ).exists()
        if is_dependente:
            return Orcamento.objects.filter(usuario=user)
        grupos_ids = MembroGrupo.objects.filter(usuario=user).values_list("grupo_id", flat=True)
        return Orcamento.objects.filter(
            Q(usuario=user) | Q(grupo_id__in=grupos_ids)
        )

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsOwnerOrGestorForWrite()]
        return [permissions.IsAuthenticated(), NaoAdmin()]

    def perform_create(self, serializer):
        grupo = serializer.validated_data.get("grupo")
        if grupo:
            if not MembroGrupo.objects.filter(
                grupo=grupo, usuario=self.request.user, papel_no_grupo="responsavel"
            ).exists():
                raise PermissionDenied("Apenas o responsável do grupo pode criar orçamentos para o grupo.")
            serializer.save()
        else:
            serializer.save(usuario=self.request.user)


# ══════════════════════════════════════════════════════════════════════════
# Divisão de Despesa (aninhada em transação ou grupo)
# ══════════════════════════════════════════════════════════════════════════

class DivisaoDespesaViewSet(viewsets.ModelViewSet):
    serializer_class = DivisaoDespesaSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsGestorDoGrupoByKwarg]

    def get_queryset(self):
        return DivisaoDespesa.objects.filter(
            transacao__grupo_id=self.kwargs["grupo_pk"]
        )


# ══════════════════════════════════════════════════════════════════════════
# Mesada (Dependente)
# ══════════════════════════════════════════════════════════════════════════

class MesadaViewSet(viewsets.ModelViewSet):
    serializer_class = MesadaSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        user = self.request.user
        is_dependente = MembroGrupo.objects.filter(
            usuario=user, papel_no_grupo="dependente"
        ).exists()
        if is_dependente:
            queryset = Mesada.objects.filter(dependente=user)
        else:
            grupos_ids = MembroGrupo.objects.filter(
                usuario=user, papel_no_grupo="responsavel"
            ).values_list("grupo_id", flat=True)
            queryset = Mesada.objects.filter(grupo_id__in=grupos_ids)
        for mesada in queryset:
            mesada.recarregar_se_devido()
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsGestorDaMesada()]
        return [permissions.IsAuthenticated(), NaoAdmin(), IsDonoOuGestorDaMesada()]

    def perform_create(self, serializer):
        grupo = serializer.validated_data["grupo"]
        if not MembroGrupo.objects.filter(
            grupo=grupo, usuario=self.request.user, papel_no_grupo="responsavel"
        ).exists():
            raise PermissionDenied("Apenas o responsável do grupo pode criar mesadas.")
        mesada = serializer.save()
        if mesada.saldo_atual == 0:
            mesada.saldo_atual = mesada.valor
            mesada.save(update_fields=["saldo_atual"])

    @action(detail=True, methods=["post"])
    def recarregar(self, request, pk=None):
        """Recarga manual pelo gestor: soma ao saldo o valor da mesada (ou um valor informado)."""
        mesada = self.get_object()
        valor_txt = str(request.data.get("valor", mesada.valor))
        try:
            valor = Decimal(valor_txt.replace(",", "."))
        except InvalidOperation:
            return Response({"detail": f"Valor inválido: '{valor_txt}'."}, status=status.HTTP_400_BAD_REQUEST)
        if valor <= 0:
            return Response({"detail": "O valor da recarga deve ser maior que zero."}, status=status.HTTP_400_BAD_REQUEST)
        mesada.saldo_atual += valor
        mesada.save(update_fields=["saldo_atual"])
        return Response(MesadaSerializer(mesada).data)


# ══════════════════════════════════════════════════════════════════════════
# Conta a pagar
# ══════════════════════════════════════════════════════════════════════════

class ContaAPagarViewSet(viewsets.ModelViewSet):
    serializer_class = ContaAPagarSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsOwner]

    def get_queryset(self):
        queryset = ContaAPagar.objects.filter(usuario=self.request.user)
        pago = self.request.query_params.get("pago")
        if pago in ("true", "false"):
            queryset = queryset.filter(pago=(pago == "true"))
        return queryset.order_by("vencimento")

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        """Marca como paga e lança a despesa correspondente na conta do usuário
        (campo 'conta' opcional; padrão: primeira conta ativa)."""
        conta_a_pagar = self.get_object()
        if conta_a_pagar.pago:
            return Response({"detail": "Esta conta já está paga."}, status=status.HTTP_400_BAD_REQUEST)

        conta = _conta_do_usuario(request)
        if conta is None:
            return Response(
                {"detail": "Crie uma conta antes de registrar o pagamento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        categoria, _ = Categoria.objects.get_or_create(
            usuario=None, nome="Contas", defaults={"tipo": "despesa", "padrao": True},
        )
        Transacao.objects.create(
            usuario=request.user, conta=conta, categoria=categoria,
            tipo="despesa", valor=conta_a_pagar.valor,
            descricao=f"Pagamento: {conta_a_pagar.descricao}",
        )
        conta_a_pagar.pago = True
        conta_a_pagar.save(update_fields=["pago"])
        return Response(ContaAPagarSerializer(conta_a_pagar).data)


def _conta_do_usuario(request):
    """Resolve a conta informada no body (se for do usuário) ou a primeira conta ativa."""
    conta_id = request.data.get("conta")
    queryset = Conta.objects.filter(usuario=request.user, ativa=True)
    if conta_id:
        return queryset.filter(id=conta_id).first()
    return queryset.first()


# ══════════════════════════════════════════════════════════════════════════
# Meta de economia
# ══════════════════════════════════════════════════════════════════════════

class MetaEconomiaViewSet(viewsets.ModelViewSet):
    serializer_class = MetaEconomiaSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsOwner]

    def get_queryset(self):
        return MetaEconomia.objects.filter(usuario=self.request.user).order_by("-criada_em")

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def aportar(self, request, pk=None):
        """Adiciona um valor guardado à meta e lança a despesa correspondente
        (o dinheiro sai do saldo da conta do usuário)."""
        meta = self.get_object()
        valor_txt = str(request.data.get("valor", ""))
        try:
            valor = Decimal(valor_txt.replace(",", "."))
        except InvalidOperation:
            return Response({"detail": f"Valor inválido: '{valor_txt}'."}, status=status.HTTP_400_BAD_REQUEST)
        if valor <= 0:
            return Response({"detail": "O valor do aporte deve ser maior que zero."}, status=status.HTTP_400_BAD_REQUEST)

        conta = _conta_do_usuario(request)
        if conta is None:
            return Response(
                {"detail": "Crie uma conta antes de fazer um aporte."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Dependente: o aporte sai da mesada — respeita o saldo e o deduz
        mesada = Mesada.objects.filter(dependente=request.user).first()
        if mesada:
            mesada.recarregar_se_devido()
            if valor > mesada.saldo_atual:
                return Response(
                    {"detail": f"Aporte acima do saldo da mesada. Saldo disponível: R$ {mesada.saldo_atual}"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        categoria, _ = Categoria.objects.get_or_create(
            usuario=None, nome="Poupanca", defaults={"tipo": "despesa", "padrao": True},
        )
        Transacao.objects.create(
            usuario=request.user, conta=conta, categoria=categoria,
            tipo="despesa", valor=valor,
            descricao=f"Aporte na meta: {meta.nome}",
        )
        if mesada:
            mesada.saldo_atual -= valor
            mesada.save(update_fields=["saldo_atual"])
        meta.valor_atual += valor
        meta.save(update_fields=["valor_atual"])
        return Response(MetaEconomiaSerializer(meta).data)


# ══════════════════════════════════════════════════════════════════════════
# Consultor
# ══════════════════════════════════════════════════════════════════════════

class AutorizacaoConsultorViewSet(viewsets.ModelViewSet):
    serializer_class = AutorizacaoConsultorSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        user = self.request.user
        return AutorizacaoConsultor.objects.filter(
            Q(consultor=user) | Q(cliente=user)
        )

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsAutorizacaoOwner()]
        return [permissions.IsAuthenticated(), NaoAdmin()]

    def perform_create(self, serializer):
        # Quem autoriza é sempre o próprio cliente logado — impede que um
        # "consultor" se autoautorize nas finanças de terceiros.
        serializer.save(cliente=self.request.user)


class RecomendacaoViewSet(viewsets.ModelViewSet):
    serializer_class = RecomendacaoSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        user = self.request.user
        return Recomendacao.objects.filter(
            Q(consultor=user) | Q(cliente=user)
        ).order_by("-data")

    def get_permissions(self):
        if self.action in ("create",):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsConsultorPodeComentar()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), NaoAdmin(), IsConsultorPodeComentar()]
        return [permissions.IsAuthenticated(), NaoAdmin()]

    def perform_create(self, serializer):
        serializer.save(consultor=self.request.user)


class ConsultorClientesView(generics.ListAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin]

    def get_queryset(self):
        return Usuario.objects.filter(
            autorizacoes_como_cliente__consultor=self.request.user,
            autorizacoes_como_cliente__status=True,
        ).distinct()


class ConsultorClienteTransacoesView(generics.ListAPIView):
    serializer_class = TransacaoSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsConsultorAutorizado]

    def get_queryset(self):
        cliente_id = self.kwargs["cliente_pk"]
        return Transacao.objects.filter(usuario_id=cliente_id).order_by("-data")


class ConsultorClienteContasView(generics.ListAPIView):
    serializer_class = ContaSerializer
    permission_classes = [permissions.IsAuthenticated, NaoAdmin, IsConsultorAutorizado]

    def get_queryset(self):
        cliente_id = self.kwargs["cliente_pk"]
        return Conta.objects.filter(usuario_id=cliente_id)

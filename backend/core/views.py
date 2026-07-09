from collections import defaultdict
from decimal import Decimal

from django.db import connections
from django.db.models import Q, Sum
from django.http import JsonResponse
from rest_framework import viewsets, generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import (
    Categoria,
    Conta,
    DivisaoDespesa,
    Grupo,
    MembroGrupo,
    Mesada,
    Orcamento,
    Transacao,
    Usuario,
)
from core.permissions import (
    IsAdminOnly,
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
    CadastroSerializer,
    CategoriaAdminSerializer,
    CategoriaSerializer,
    ContaSerializer,
    DivisaoDespesaSerializer,
    GrupoSerializer,
    MembroGrupoSerializer,
    MesadaSerializer,
    OrcamentoSerializer,
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
            return Transacao.objects.filter(usuario=user).order_by("-data")
        grupos_ids = MembroGrupo.objects.filter(usuario=user).values_list("grupo_id", flat=True)
        return Transacao.objects.filter(
            Q(usuario=user) | Q(grupo_id__in=grupos_ids)
        ).order_by("-data")

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
            return Mesada.objects.filter(dependente=user)
        grupos_ids = MembroGrupo.objects.filter(
            usuario=user, papel_no_grupo="responsavel"
        ).values_list("grupo_id", flat=True)
        return Mesada.objects.filter(grupo_id__in=grupos_ids)

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

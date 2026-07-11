from rest_framework import serializers

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


# ─── Usuário ───────────────────────────────────────────────────────────

class CadastroSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "senha"]

    def create(self, validated_data):
        senha = validated_data.pop("senha")
        return Usuario.objects.create_user(
            password=senha,
            papel_sistema="comum",
            **validated_data,
        )


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "papel_sistema", "data_criacao"]
        read_only_fields = ["id", "papel_sistema", "data_criacao"]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "papel_sistema", "is_active", "senha", "data_criacao"]
        read_only_fields = ["id", "data_criacao"]

    def validate(self, data):
        if self.instance is None and not data.get("senha"):
            raise serializers.ValidationError({"senha": "Informe uma senha para o novo usuário."})
        return data

    def create(self, validated_data):
        senha = validated_data.pop("senha")
        # admin criado pela API também precisa acessar o Django Admin
        if validated_data.get("papel_sistema") == "admin":
            validated_data["is_staff"] = True
        return Usuario.objects.create_user(password=senha, **validated_data)

    def update(self, instance, validated_data):
        senha = validated_data.pop("senha", None)
        if validated_data.get("papel_sistema") == "admin":
            validated_data["is_staff"] = True
        usuario = super().update(instance, validated_data)
        if senha:
            usuario.set_password(senha)
            usuario.save(update_fields=["password"])
        return usuario


# ─── Conta ─────────────────────────────────────────────────────────────

class ContaSerializer(serializers.ModelSerializer):
    saldo_atual = serializers.SerializerMethodField()

    class Meta:
        model = Conta
        fields = ["id", "nome", "saldo_inicial", "saldo_atual", "ativa", "usuario"]
        read_only_fields = ["id", "usuario"]

    def get_saldo_atual(self, obj):
        """Saldo vivo: saldo inicial + receitas - despesas da conta."""
        from django.db.models import Sum

        receitas = obj.transacoes.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
        despesas = obj.transacoes.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0
        return obj.saldo_inicial + receitas - despesas


# ─── Categoria ─────────────────────────────────────────────────────────

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome", "tipo", "padrao", "usuario"]
        read_only_fields = ["id", "usuario"]


class CategoriaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome", "tipo", "padrao"]
        read_only_fields = ["id"]


# ─── Grupo ─────────────────────────────────────────────────────────────

class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = ["id", "nome", "descricao", "responsavel", "data_criacao", "ativo"]
        read_only_fields = ["id", "responsavel", "data_criacao"]


class MembroGrupoSerializer(serializers.ModelSerializer):
    nome_usuario = serializers.CharField(source="usuario.nome", read_only=True)
    email_usuario = serializers.CharField(source="usuario.email", read_only=True)

    class Meta:
        model = MembroGrupo
        fields = ["id", "grupo", "usuario", "nome_usuario", "email_usuario", "papel_no_grupo", "data_entrada"]
        read_only_fields = ["id", "grupo", "nome_usuario", "email_usuario", "data_entrada"]


# ─── Transação ─────────────────────────────────────────────────────────

class DivisaoDespesaSerializer(serializers.ModelSerializer):
    nome_participante = serializers.CharField(source="participante.nome", read_only=True)

    class Meta:
        model = DivisaoDespesa
        fields = ["id", "transacao", "participante", "nome_participante", "valor_devido", "pago"]
        read_only_fields = ["id", "transacao", "nome_participante"]


class TransacaoSerializer(serializers.ModelSerializer):
    divisoes = DivisaoDespesaSerializer(many=True, read_only=True)
    nome_conta = serializers.CharField(source="conta.nome", read_only=True)
    nome_categoria = serializers.CharField(source="categoria.nome", read_only=True)

    class Meta:
        model = Transacao
        fields = [
            "id", "usuario", "conta", "nome_conta", "categoria", "nome_categoria",
            "tipo", "valor", "descricao", "data", "grupo", "fixa", "divisoes",
        ]
        read_only_fields = ["id", "usuario", "nome_conta", "nome_categoria"]


class TransacaoCreateSerializer(serializers.ModelSerializer):
    dividir_igualmente = serializers.BooleanField(default=False, write_only=True)
    participantes_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = Transacao
        fields = [
            "id", "conta", "categoria", "tipo", "valor", "descricao",
            "data", "grupo", "fixa", "dividir_igualmente", "participantes_ids",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        raw = self.initial_data
        divisoes = raw.get("divisoes") or []
        dividir = raw.get("dividir_igualmente", False)
        participantes = raw.get("participantes_ids") or []
        valor = raw.get("valor", 0)

        if dividir and participantes:
            if len(participantes) == 0:
                raise serializers.ValidationError("Informe ao menos um participante para a divisão.")
        elif divisoes:
            total_divisoes = sum(float(d["valor_devido"]) for d in divisoes)
            if abs(total_divisoes - float(valor)) > 0.01:
                raise serializers.ValidationError(
                    "A soma das partes da divisão deve ser igual ao valor total da transação."
                )
        return data

    def create(self, validated_data):
        raw = self.initial_data
        divisoes_data = raw.get("divisoes") or []
        dividir = raw.get("dividir_igualmente", False)
        participantes_ids = raw.get("participantes_ids") or []

        validated_data.pop("dividir_igualmente", None)
        validated_data.pop("participantes_ids", None)

        transacao = Transacao.objects.create(**validated_data)

        if dividir and participantes_ids:
            valor = float(transacao.valor)
            parte = round(valor / len(participantes_ids), 2)
            ajuste = round(valor - parte * len(participantes_ids), 2)
            for i, pid in enumerate(participantes_ids):
                valor_final = parte + (ajuste if i == 0 else 0)
                DivisaoDespesa.objects.create(
                    transacao=transacao,
                    participante_id=pid,
                    valor_devido=valor_final,
                )
        else:
            for div in divisoes_data:
                DivisaoDespesa.objects.create(
                    transacao=transacao,
                    participante_id=div["participante"],
                    valor_devido=div["valor_devido"],
                )
        return transacao


# ─── Orçamento ─────────────────────────────────────────────────────────

class OrcamentoSerializer(serializers.ModelSerializer):
    nome_categoria = serializers.CharField(source="categoria.nome", read_only=True)

    class Meta:
        model = Orcamento
        fields = ["id", "usuario", "grupo", "categoria", "nome_categoria", "valor_limite", "periodo"]
        read_only_fields = ["id", "nome_categoria"]


# ─── Mesada ────────────────────────────────────────────────────────────

class MesadaSerializer(serializers.ModelSerializer):
    nome_dependente = serializers.CharField(source="dependente.nome", read_only=True)
    nome_grupo = serializers.CharField(source="grupo.nome", read_only=True)

    class Meta:
        model = Mesada
        fields = [
            "id", "dependente", "nome_dependente", "grupo", "nome_grupo",
            "valor", "periodo_recarga", "saldo_atual", "ultima_recarga",
        ]
        read_only_fields = ["id", "nome_dependente", "nome_grupo", "ultima_recarga"]


# ─── Conta a pagar ─────────────────────────────────────────────────────

class ContaAPagarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContaAPagar
        fields = ["id", "usuario", "descricao", "valor", "vencimento", "recorrencia", "pago"]
        read_only_fields = ["id", "usuario"]


# ─── Meta de economia ──────────────────────────────────────────────────

class MetaEconomiaSerializer(serializers.ModelSerializer):
    concluida = serializers.BooleanField(read_only=True)
    percentual = serializers.SerializerMethodField()

    class Meta:
        model = MetaEconomia
        fields = [
            "id", "usuario", "nome", "valor_alvo", "valor_atual",
            "prazo", "criada_em", "concluida", "percentual",
        ]
        read_only_fields = ["id", "usuario", "criada_em"]

    def get_percentual(self, obj):
        if not obj.valor_alvo:
            return 0.0
        return round(min(float(obj.valor_atual) / float(obj.valor_alvo) * 100, 100), 1)

    def validate_valor_alvo(self, valor):
        if valor <= 0:
            raise serializers.ValidationError("O valor alvo deve ser maior que zero.")
        return valor


# ─── Consultor ─────────────────────────────────────────────────────────

class AutorizacaoConsultorSerializer(serializers.ModelSerializer):
    nome_consultor = serializers.CharField(source="consultor.nome", read_only=True)
    nome_cliente = serializers.CharField(source="cliente.nome", read_only=True)
    email_consultor = serializers.EmailField(source="consultor.email", read_only=True)
    consultor_email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = AutorizacaoConsultor
        fields = [
            "id", "consultor", "nome_consultor", "email_consultor",
            "cliente", "nome_cliente", "nivel", "status", "consultor_email",
        ]
        read_only_fields = ["id", "cliente", "nome_consultor", "email_consultor", "nome_cliente"]
        extra_kwargs = {"consultor": {"required": False}}
        validators = []  # unicidade validada manualmente (cliente vem do request)

    def validate(self, data):
        email = data.pop("consultor_email", None)
        if self.instance is not None:
            return data  # updates só alteram nivel/status

        if not data.get("consultor"):
            if not email:
                raise serializers.ValidationError("Informe o consultor (id) ou consultor_email.")
            consultor = Usuario.objects.filter(email__iexact=email, papel_sistema="comum").first()
            if consultor is None:
                raise serializers.ValidationError(f"Nenhum usuário encontrado com o e-mail {email}.")
            data["consultor"] = consultor

        cliente = self.context["request"].user
        if data["consultor"].id == cliente.id:
            raise serializers.ValidationError("Você não pode ser consultor de si mesmo.")
        if AutorizacaoConsultor.objects.filter(consultor=data["consultor"], cliente=cliente).exists():
            raise serializers.ValidationError("Já existe uma autorização para este consultor.")
        return data


class RecomendacaoSerializer(serializers.ModelSerializer):
    nome_consultor = serializers.CharField(source="consultor.nome", read_only=True)
    nome_cliente = serializers.CharField(source="cliente.nome", read_only=True)

    class Meta:
        model = Recomendacao
        fields = ["id", "consultor", "nome_consultor", "cliente", "nome_cliente", "texto", "data"]
        read_only_fields = ["id", "consultor", "nome_consultor", "nome_cliente", "data"]

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    PAPEL_SISTEMA_CHOICES = [
        ("comum", "Comum"),
        ("admin", "Administrador"),
    ]

    username = None
    email = models.EmailField("email", unique=True)
    nome = models.CharField("nome", max_length=150)
    papel_sistema = models.CharField(
        "papel no sistema",
        max_length=10,
        choices=PAPEL_SISTEMA_CHOICES,
        default="comum",
    )
    data_criacao = models.DateTimeField("data de criação", default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return f"{self.nome} ({self.email})"


class Conta(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contas",
        verbose_name="usuário",
    )
    nome = models.CharField("nome", max_length=100)
    saldo_inicial = models.DecimalField(
        "saldo inicial", max_digits=12, decimal_places=2, default=0
    )
    ativa = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "conta"
        verbose_name_plural = "contas"

    def __str__(self):
        return f"{self.nome} ({self.usuario.nome})"


class Categoria(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categorias",
        verbose_name="usuário",
        null=True,
        blank=True,
    )
    nome = models.CharField("nome", max_length=100)
    tipo = models.CharField("tipo", max_length=10, choices=TIPO_CHOICES)
    padrao = models.BooleanField("padrão", default=False)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "nome"],
                name="categoria_unica_por_usuario",
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class Grupo(models.Model):
    nome = models.CharField("nome", max_length=150)
    descricao = models.TextField("descrição", blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grupos_responsavel",
        verbose_name="responsável",
    )
    data_criacao = models.DateTimeField("data de criação", default=timezone.now)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "grupo"
        verbose_name_plural = "grupos"

    def __str__(self):
        return self.nome


class MembroGrupo(models.Model):
    PAPEL_CHOICES = [
        ("responsavel", "Responsável"),
        ("membro", "Membro"),
        ("dependente", "Dependente"),
    ]

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="membros",
        verbose_name="grupo",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participacoes",
        verbose_name="usuário",
    )
    papel_no_grupo = models.CharField(
        "papel no grupo",
        max_length=20,
        choices=PAPEL_CHOICES,
        default="membro",
    )
    data_entrada = models.DateTimeField("data de entrada", default=timezone.now)

    class Meta:
        verbose_name = "membro do grupo"
        verbose_name_plural = "membros do grupo"
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "usuario"],
                name="membro_unico_por_grupo",
            )
        ]

    def __str__(self):
        return f"{self.usuario.nome} ({self.papel_no_grupo}) em {self.grupo.nome}"


class Transacao(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transacoes",
        verbose_name="usuário",
    )
    conta = models.ForeignKey(
        Conta,
        on_delete=models.PROTECT,
        related_name="transacoes",
        verbose_name="conta",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="transacoes",
        verbose_name="categoria",
    )
    tipo = models.CharField("tipo", max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    descricao = models.TextField("descrição", blank=True)
    data = models.DateTimeField("data", default=timezone.now)
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transacoes",
        verbose_name="grupo",
    )
    fixa = models.BooleanField("fixa", default=False)

    class Meta:
        verbose_name = "transação"
        verbose_name_plural = "transações"

    def __str__(self):
        return f"{self.descricao or self.tipo} — R$ {self.valor}"

    def clean(self):
        if self.conta.usuario_id != self.usuario_id:
            raise ValidationError("A conta deve pertencer ao mesmo usuário da transação.")
        if self.categoria.usuario_id is not None and self.categoria.usuario_id != self.usuario_id:
            raise ValidationError("A categoria pessoal deve pertencer ao mesmo usuário da transação.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Orcamento(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orcamentos",
        verbose_name="usuário",
        null=True,
        blank=True,
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="orcamentos",
        verbose_name="grupo",
        null=True,
        blank=True,
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="orcamentos",
        verbose_name="categoria",
    )
    valor_limite = models.DecimalField(
        "valor limite", max_digits=12, decimal_places=2
    )
    periodo = models.DateField("período")

    class Meta:
        verbose_name = "orçamento"
        verbose_name_plural = "orçamentos"

    def __str__(self):
        escopo = self.usuario.nome if self.usuario else self.grupo.nome
        return f"Orçamento {self.categoria.nome} — {escopo}"

    def clean(self):
        if not self.usuario and not self.grupo:
            raise ValidationError("O orçamento deve pertencer a um usuário ou a um grupo.")
        if self.usuario and self.grupo:
            raise ValidationError("O orçamento não pode pertencer a um usuário e a um grupo ao mesmo tempo.")


class DivisaoDespesa(models.Model):
    transacao = models.ForeignKey(
        Transacao,
        on_delete=models.CASCADE,
        related_name="divisoes",
        verbose_name="transação",
    )
    participante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dividas",
        verbose_name="participante",
    )
    valor_devido = models.DecimalField(
        "valor devido", max_digits=12, decimal_places=2
    )
    pago = models.BooleanField("pago", default=False)

    class Meta:
        verbose_name = "divisão de despesa"
        verbose_name_plural = "divisões de despesas"
        constraints = [
            models.UniqueConstraint(
                fields=["transacao", "participante"],
                name="divisao_unica_por_participante",
            )
        ]

    def __str__(self):
        return f"{self.participante.nome} deve R$ {self.valor_devido}"

    def clean(self):
        if self.transacao.tipo != "despesa":
            raise ValidationError("Somente despesas podem ser divididas.")
        if self.transacao.grupo is None:
            raise ValidationError("Somente transações vinculadas a um grupo podem ser divididas.")
        if self.valor_devido <= 0:
            raise ValidationError("O valor devido deve ser maior que zero.")


# ─── Models de evolução (sem endpoints no MVP) ──────────────────────────


class Mesada(models.Model):
    PERIODO_CHOICES = [
        ("semanal", "Semanal"),
        ("quinzenal", "Quinzenal"),
        ("mensal", "Mensal"),
    ]

    dependente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mesadas",
        verbose_name="dependente",
    )
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name="mesadas",
        verbose_name="grupo",
    )
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    periodo_recarga = models.CharField(
        "período de recarga", max_length=15, choices=PERIODO_CHOICES
    )
    saldo_atual = models.DecimalField(
        "saldo atual", max_digits=12, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = "mesada"
        verbose_name_plural = "mesadas"

    def __str__(self):
        return f"Mesada de {self.dependente.nome} — R$ {self.valor}/{self.periodo_recarga}"


class AutorizacaoConsultor(models.Model):
    NIVEL_CHOICES = [
        ("leitura", "Leitura"),
        ("comentar", "Comentar"),
    ]

    consultor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="autorizacoes_como_consultor",
        verbose_name="consultor",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="autorizacoes_como_cliente",
        verbose_name="cliente",
    )
    nivel = models.CharField("nível", max_length=10, choices=NIVEL_CHOICES, default="leitura")
    status = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "autorização de consultor"
        verbose_name_plural = "autorizações de consultores"
        constraints = [
            models.UniqueConstraint(
                fields=["consultor", "cliente"],
                name="autorizacao_unica_consultor_cliente",
            )
        ]

    def __str__(self):
        return f"{self.consultor.nome} → {self.cliente.nome}"


class ContaAPagar(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contas_a_pagar",
        verbose_name="usuário",
    )
    descricao = models.CharField("descrição", max_length=200)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    vencimento = models.DateField("vencimento")
    recorrencia = models.BooleanField("recorrência", default=False)
    pago = models.BooleanField("pago", default=False)

    class Meta:
        verbose_name = "conta a pagar"
        verbose_name_plural = "contas a pagar"

    def __str__(self):
        return f"{self.descricao} — R$ {self.valor}"


class Recomendacao(models.Model):
    consultor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recomendacoes_feitas",
        verbose_name="consultor",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recomendacoes_recebidas",
        verbose_name="cliente",
    )
    texto = models.TextField("texto")
    data = models.DateTimeField("data", default=timezone.now)

    class Meta:
        verbose_name = "recomendação"
        verbose_name_plural = "recomendações"

    def __str__(self):
        return f"Recomendação de {self.consultor.nome} para {self.cliente.nome}"

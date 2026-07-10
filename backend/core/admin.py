from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

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


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ["email", "nome", "papel_sistema", "is_active", "data_criacao"]
    list_filter = ["papel_sistema", "is_active"]
    search_fields = ["email", "nome"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "nome", "password")}),
        ("Permissões", {"fields": ("papel_sistema", "is_active", "is_staff", "is_superuser")}),
        ("Datas", {"fields": ("last_login", "data_criacao")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nome", "password1", "password2", "papel_sistema"),
        }),
    )
    readonly_fields = ["data_criacao"]


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ["nome", "usuario", "saldo_inicial", "ativa"]
    list_filter = ["ativa"]
    search_fields = ["nome", "usuario__nome", "usuario__email"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "usuario", "padrao"]
    list_filter = ["tipo", "padrao"]
    search_fields = ["nome", "usuario__nome"]


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "usuario", "conta", "categoria", "data", "grupo"]
    list_filter = ["tipo", "data", "fixa"]
    search_fields = ["descricao", "usuario__nome", "usuario__email"]
    date_hierarchy = "data"


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ["nome", "responsavel", "data_criacao", "ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome", "responsavel__nome"]


@admin.register(MembroGrupo)
class MembroGrupoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "grupo", "papel_no_grupo", "data_entrada"]
    list_filter = ["papel_no_grupo"]
    search_fields = ["usuario__nome", "grupo__nome"]


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ["categoria", "valor_limite", "periodo", "usuario", "grupo"]
    list_filter = ["periodo"]
    search_fields = ["categoria__nome", "usuario__nome", "grupo__nome"]


@admin.register(DivisaoDespesa)
class DivisaoDespesaAdmin(admin.ModelAdmin):
    list_display = ["transacao", "participante", "valor_devido", "pago"]
    list_filter = ["pago"]
    search_fields = ["participante__nome", "transacao__descricao"]


@admin.register(Mesada)
class MesadaAdmin(admin.ModelAdmin):
    list_display = ["dependente", "grupo", "valor", "periodo_recarga", "saldo_atual"]
    list_filter = ["periodo_recarga"]


@admin.register(AutorizacaoConsultor)
class AutorizacaoConsultorAdmin(admin.ModelAdmin):
    list_display = ["consultor", "cliente", "nivel", "status"]
    list_filter = ["nivel", "status"]


@admin.register(ContaAPagar)
class ContaAPagarAdmin(admin.ModelAdmin):
    list_display = ["descricao", "usuario", "valor", "vencimento", "pago", "recorrencia"]
    list_filter = ["pago", "recorrencia"]


@admin.register(MetaEconomia)
class MetaEconomiaAdmin(admin.ModelAdmin):
    list_display = ["nome", "usuario", "valor_alvo", "valor_atual", "prazo"]
    search_fields = ["nome", "usuario__nome"]


@admin.register(Recomendacao)
class RecomendacaoAdmin(admin.ModelAdmin):
    list_display = ["consultor", "cliente", "data"]
    list_filter = ["data"]

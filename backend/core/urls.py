from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    CategoriaViewSet,
    ContaViewSet,
    DivisaoDespesaViewSet,
    GrupoViewSet,
    health_check,
    LoginView,
    MeView,
    MembroGrupoViewSet,
    MesadaViewSet,
    OrcamentoViewSet,
    RegistroView,
    TransacaoViewSet,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")
router.register(r"contas", ContaViewSet, basename="conta")
router.register(r"categorias", CategoriaViewSet, basename="categoria")
router.register(r"grupos", GrupoViewSet, basename="grupo")
router.register(r"transacoes", TransacaoViewSet, basename="transacao")
router.register(r"orcamentos", OrcamentoViewSet, basename="orcamento")
router.register(r"mesadas", MesadaViewSet, basename="mesada")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/registro/", RegistroView.as_view(), name="registro"),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/grupos/<int:grupo_pk>/membros/", MembroGrupoViewSet.as_view({"get": "list", "post": "create"}), name="grupo-membros-list"),
    path("api/grupos/<int:grupo_pk>/membros/<int:pk>/", MembroGrupoViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="grupo-membros-detail"),
    path("api/grupos/<int:grupo_pk>/divisoes/", DivisaoDespesaViewSet.as_view({"get": "list", "post": "create"}), name="grupo-divisoes-list"),
    path("api/", include(router.urls)),
]

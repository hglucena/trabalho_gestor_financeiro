from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.models import MembroGrupo


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        return obj.usuario_id == request.user.id


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.papel_sistema == "admin"


class IsAdminOuReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.papel_sistema == "admin"


class IsOwnerOrAdminForWrite(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return True
        usuario_id = getattr(obj, "usuario_id", None)
        if usuario_id is None and hasattr(obj, "dependente_id"):
            usuario_id = obj.dependente_id
        return usuario_id == request.user.id


class IsGestorDoGrupo(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        grupo = self._get_grupo(obj)
        if grupo is None:
            return False
        if request.method in SAFE_METHODS:
            return MembroGrupo.objects.filter(
                grupo=grupo, usuario=request.user
            ).exists()
        return MembroGrupo.objects.filter(
            grupo=grupo, usuario=request.user, papel_no_grupo="responsavel"
        ).exists()

    def _get_grupo(self, obj):
        if hasattr(obj, "grupo"):
            return obj.grupo
        if hasattr(obj, "grupo_id"):
            from core.models import Grupo
            return Grupo.objects.get(id=obj.grupo_id)
        return None


class IsMembroDoGrupo(BasePermission):
    """Usado para ações em nível de view (list/create do grupo)."""
    def has_permission(self, request, view):
        if request.user.papel_sistema == "admin":
            return False
        grupo_id = view.kwargs.get("grupo_pk") or request.data.get("grupo")
        if not grupo_id:
            return False
        return MembroGrupo.objects.filter(
            grupo_id=grupo_id, usuario=request.user
        ).exists()


class IsGestorDoGrupoByKwarg(BasePermission):
    """Usado para views aninhadas onde o grupo_pk vem da URL."""
    def has_permission(self, request, view):
        if request.user.papel_sistema == "admin":
            return False
        grupo_id = view.kwargs.get("grupo_pk")
        if not grupo_id:
            return False
        if request.method in SAFE_METHODS:
            return MembroGrupo.objects.filter(
                grupo_id=grupo_id, usuario=request.user
            ).exclude(papel_no_grupo="dependente").exists()
        return MembroGrupo.objects.filter(
            grupo_id=grupo_id, usuario=request.user, papel_no_grupo="responsavel"
        ).exists()


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        if request.method in SAFE_METHODS:
            return True
        if hasattr(obj, "usuario_id"):
            return obj.usuario_id == request.user.id
        if hasattr(obj, "responsavel_id"):
            return obj.responsavel_id == request.user.id
        return False


class NaoAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.papel_sistema != "admin"


class IsOwnerOrGestorForWrite(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        if request.method in SAFE_METHODS:
            return True
        if hasattr(obj, "usuario_id") and obj.usuario_id == request.user.id:
            return True
        grupo = getattr(obj, "grupo", None)
        if grupo:
            return MembroGrupo.objects.filter(
                grupo=grupo, usuario=request.user, papel_no_grupo="responsavel"
            ).exists()
        return False


class IsOwnerOrGrupoMemberRead(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        if obj.usuario_id == request.user.id:
            return True
        if obj.grupo_id and request.method in SAFE_METHODS:
            return MembroGrupo.objects.filter(
                grupo_id=obj.grupo_id, usuario=request.user
            ).exists()
        return False


class IsGestorDaMesada(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        return MembroGrupo.objects.filter(
            grupo=obj.grupo, usuario=request.user, papel_no_grupo="responsavel"
        ).exists()


class IsDonoOuGestorDaMesada(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.papel_sistema == "admin":
            return False
        if request.method in SAFE_METHODS:
            if obj.dependente_id == request.user.id:
                return True
            return MembroGrupo.objects.filter(
                grupo=obj.grupo, usuario=request.user
            ).exists()
        return MembroGrupo.objects.filter(
            grupo=obj.grupo, usuario=request.user, papel_no_grupo="responsavel"
        ).exists()

from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class IsAdminUser(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a usuários admin (is_staff=True).
    """
    message = "Acesso restrito a administradores."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed(
                detail="Token de autenticação não fornecido ou inválido.",
                code="authentication_required"
            )

        if not request.user.is_staff:
            raise PermissionDenied(
                detail=self.message,
                code="admin_required"
            )

        return True


class IsSuperUser(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a superusuários.
    """
    message = "Acesso restrito a superusuários."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed(
                detail="Token de autenticação não fornecido ou inválido.",
                code="authentication_required"
            )

        if not request.user.is_superuser:
            raise PermissionDenied(
                detail=self.message,
                code="superuser_required"
            )

        return True


class IsAuthenticated(permissions.BasePermission):
    """
    Permissão que permite acesso apenas a usuários autenticados.
    """
    message = "Autenticação necessária."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed(
                detail="Token de autenticação não fornecido ou inválido.",
                code="authentication_required"
            )

        if not request.user.is_active:
            raise AuthenticationFailed(
                detail="Usuário inativo.",
                code="user_inactive"
            )

        return True


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Permite leitura para todos, escrita apenas para autenticados.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed(
                detail="Token de autenticação necessário para esta operação.",
                code="authentication_required"
            )

        return True

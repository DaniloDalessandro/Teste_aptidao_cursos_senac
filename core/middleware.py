import json
import logging
from django.http import JsonResponse
from django.urls import resolve
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware:
    """
    Middleware para autenticação JWT em rotas protegidas.
    Protege automaticamente rotas /api/v1/admin/*.
    """

    PROTECTED_PREFIXES = [
        '/api/v1/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        # Verifica se a rota precisa de proteção
        if self._is_protected_route(request.path):
            auth_result = self._authenticate(request)

            if auth_result is not None:
                return auth_result

            # Verifica se é admin
            if not self._is_admin(request):
                return self._forbidden_response(
                    "Acesso restrito a administradores.",
                    "admin_required"
                )

        response = self.get_response(request)
        return response

    def _is_protected_route(self, path):
        """
        Verifica se o path está em uma rota protegida.
        """
        for prefix in self.PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _authenticate(self, request):
        """
        Tenta autenticar o usuário via JWT.
        Retorna None se autenticação bem-sucedida, ou JsonResponse de erro.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            logger.warning(f"Tentativa de acesso sem token: {request.path}")
            return self._unauthorized_response(
                "Token de autenticação não fornecido.",
                "token_missing"
            )

        try:
            # Valida o token
            validated_token = self.jwt_auth.get_validated_token(
                self._get_raw_token(auth_header)
            )
            user = self.jwt_auth.get_user(validated_token)

            if user is None:
                logger.warning(f"Token válido mas usuário não encontrado: {request.path}")
                return self._unauthorized_response(
                    "Usuário não encontrado.",
                    "user_not_found"
                )

            if not user.is_active:
                logger.warning(f"Tentativa de acesso com usuário inativo: {user.username}")
                return self._unauthorized_response(
                    "Usuário inativo.",
                    "user_inactive"
                )

            # Anexa o usuário à request
            request.user = user
            request.auth = validated_token

            logger.info(f"Usuário {user.username} autenticado para {request.path}")
            return None

        except InvalidToken as e:
            logger.warning(f"Token inválido: {str(e)}")
            return self._unauthorized_response(
                "Token inválido ou expirado.",
                "token_invalid"
            )
        except TokenError as e:
            logger.warning(f"Erro no token: {str(e)}")
            return self._unauthorized_response(
                "Erro ao processar token.",
                "token_error"
            )
        except Exception as e:
            logger.error(f"Erro inesperado na autenticação: {str(e)}")
            return self._unauthorized_response(
                "Erro na autenticação.",
                "authentication_error"
            )

    def _get_raw_token(self, auth_header):
        """
        Extrai o token do header Authorization.
        """
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            return parts[1].encode()
        return auth_header.encode()

    def _is_admin(self, request):
        """
        Verifica se o usuário é admin.
        """
        return hasattr(request, 'user') and request.user.is_staff

    def _unauthorized_response(self, message, code):
        """
        Retorna resposta 401 Unauthorized padronizada.
        """
        return JsonResponse({
            "success": False,
            "message": message,
            "data": None,
            "errors": [{"code": code, "detail": message}]
        }, status=401)

    def _forbidden_response(self, message, code):
        """
        Retorna resposta 403 Forbidden padronizada.
        """
        return JsonResponse({
            "success": False,
            "message": message,
            "data": None,
            "errors": [{"code": code, "detail": message}]
        }, status=403)


class RequestLoggingMiddleware:
    """
    Middleware para logging de requisições à API.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('api.requests')

    def __call__(self, request):
        # Log da requisição
        if request.path.startswith('/api/'):
            self.logger.info(
                f"{request.method} {request.path} - "
                f"User: {getattr(request.user, 'username', 'anonymous')} - "
                f"IP: {self._get_client_ip(request)}"
            )

        response = self.get_response(request)

        # Log da resposta para erros
        if request.path.startswith('/api/') and response.status_code >= 400:
            self.logger.warning(
                f"{request.method} {request.path} - "
                f"Status: {response.status_code} - "
                f"User: {getattr(request.user, 'username', 'anonymous')}"
            )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

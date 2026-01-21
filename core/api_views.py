import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.auth import authenticate
from django.conf import settings

from core.utils import success_response, error_response
from core.models import LoginLog

logger = logging.getLogger(__name__)

# Configurações de rate limiting
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


class LoginAPIView(APIView):
    """
    POST /api/v1/auth/login/
    Autenticação via JWT com logging de tentativas.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        # Validação básica
        if not username or not password:
            return error_response(
                message="Username e password são obrigatórios",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Verifica rate limiting
        ip_address = LoginLog.get_client_ip(request)
        failed_attempts = LoginLog.get_recent_failed_attempts(
            username=username,
            ip_address=ip_address,
            minutes=LOCKOUT_MINUTES
        )

        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            LoginLog.log_attempt(
                request=request,
                username=username,
                status='blocked',
                message=f'Bloqueado após {failed_attempts} tentativas falhas'
            )
            logger.warning(f"Login bloqueado para {username} de {ip_address}: muitas tentativas")
            return error_response(
                message=f"Conta temporariamente bloqueada. Tente novamente em {LOCKOUT_MINUTES} minutos.",
                errors=[{"code": "account_locked", "detail": "Muitas tentativas de login falhas"}],
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Tenta autenticar
        user = authenticate(username=username, password=password)

        if user is None:
            LoginLog.log_attempt(
                request=request,
                username=username,
                status='failed',
                message='Credenciais inválidas'
            )
            logger.warning(f"Login falhou para {username} de {ip_address}: credenciais inválidas")
            return error_response(
                message="Credenciais inválidas",
                errors=[{"code": "invalid_credentials", "detail": "Username ou password incorretos"}],
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            LoginLog.log_attempt(
                request=request,
                username=username,
                status='failed',
                message='Usuário inativo',
                user=user
            )
            logger.warning(f"Login falhou para {username}: usuário inativo")
            return error_response(
                message="Usuário inativo",
                errors=[{"code": "user_inactive", "detail": "Conta desativada"}],
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Login bem-sucedido
        refresh = RefreshToken.for_user(user)

        LoginLog.log_attempt(
            request=request,
            username=username,
            status='success',
            message='Login bem-sucedido',
            user=user
        )
        logger.info(f"Login bem-sucedido para {username} de {ip_address}")

        return success_response(
            message="Login realizado com sucesso",
            data={
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'expires_in': int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                'token_type': 'Bearer',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                }
            }
        )


class TokenRefreshAPIView(APIView):
    """
    POST /api/v1/auth/token/refresh/
    Atualiza o access token usando o refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return error_response(
                message="Refresh token é obrigatório",
                errors=[{"code": "refresh_required", "detail": "Forneça o refresh token"}],
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)

            # Gera novo access token
            access_token = str(refresh.access_token)

            # Opcionalmente, rotaciona o refresh token
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                new_refresh = str(refresh)
            else:
                new_refresh = refresh_token

            logger.info(f"Token refreshed for user_id: {refresh.payload.get('user_id')}")

            return success_response(
                message="Token atualizado com sucesso",
                data={
                    'access': access_token,
                    'refresh': new_refresh,
                    'expires_in': int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                    'token_type': 'Bearer',
                }
            )

        except TokenError as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            return error_response(
                message="Refresh token inválido ou expirado",
                errors=[{"code": "token_invalid", "detail": str(e)}],
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class TokenVerifyAPIView(APIView):
    """
    POST /api/v1/auth/token/verify/
    Verifica se um token é válido.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return error_response(
                message="Token é obrigatório",
                errors=[{"code": "token_required", "detail": "Forneça o token para verificação"}],
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            from rest_framework_simplejwt.tokens import AccessToken
            AccessToken(token)

            return success_response(
                message="Token válido",
                data={'valid': True}
            )

        except TokenError as e:
            return error_response(
                message="Token inválido ou expirado",
                errors=[{"code": "token_invalid", "detail": str(e)}],
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class LogoutAPIView(APIView):
    """
    POST /api/v1/auth/logout/
    Invalida o refresh token (logout).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return error_response(
                message="Refresh token é obrigatório",
                errors=[{"code": "refresh_required", "detail": "Forneça o refresh token para logout"}],
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"Logout realizado - token blacklisted")

            return success_response(
                message="Logout realizado com sucesso",
                data=None
            )

        except TokenError as e:
            # Mesmo se o token já expirou, consideramos logout bem-sucedido
            logger.info(f"Logout com token já inválido: {str(e)}")
            return success_response(
                message="Logout realizado com sucesso",
                data=None
            )


class PasswordForgotAPIView(APIView):
    """
    POST /api/v1/auth/password/forgot/
    Solicitação de reset de senha (placeholder).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()

        if not email:
            return error_response(
                message="Email é obrigatório",
                errors=[{"code": "email_required", "detail": "Forneça o email para recuperação"}],
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Por segurança, sempre retornamos sucesso para não revelar se o email existe
        logger.info(f"Password reset requested for: {email}")

        return success_response(
            message="Se o email existir em nossa base, você receberá instruções para redefinir sua senha",
            data=None
        )


class MeAPIView(APIView):
    """
    GET /api/v1/auth/me/
    Retorna os dados do usuário autenticado.
    """
    from core.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return success_response(
            message="Dados do usuário",
            data={
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
        )

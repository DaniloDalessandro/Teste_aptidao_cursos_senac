import logging
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError, AuthenticationFailed

logger = logging.getLogger(__name__)


def api_response(success, message, data=None, errors=None, status_code=status.HTTP_200_OK):
    """
    Formato padronizado de resposta da API.
    """
    return Response({
        "success": success,
        "message": message,
        "data": data,
        "errors": errors
    }, status=status_code)


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Resposta de sucesso padronizada.
    """
    return api_response(
        success=True,
        message=message,
        data=data,
        errors=None,
        status_code=status_code
    )


def error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Resposta de erro padronizada.
    """
    return api_response(
        success=False,
        message=message,
        data=None,
        errors=errors,
        status_code=status_code
    )


def custom_exception_handler(exc, context):
    """
    Handler customizado de exceções para manter o formato padronizado.
    Inclui tratamento especial para erros de JWT.
    """
    # Log do erro
    request = context.get('request')
    view = context.get('view')
    logger.warning(
        f"Exception in {view.__class__.__name__ if view else 'unknown'}: "
        f"{exc.__class__.__name__}: {str(exc)}"
    )

    # Tratamento especial para erros de JWT
    if isinstance(exc, InvalidToken):
        return Response({
            "success": False,
            "message": "Token inválido ou expirado.",
            "data": None,
            "errors": [{
                "code": "token_invalid",
                "detail": str(exc.detail.get('detail', 'Token inválido'))
            }]
        }, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, TokenError):
        return Response({
            "success": False,
            "message": "Erro no processamento do token.",
            "data": None,
            "errors": [{
                "code": "token_error",
                "detail": str(exc)
            }]
        }, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, AuthenticationFailed):
        return Response({
            "success": False,
            "message": "Falha na autenticação.",
            "data": None,
            "errors": [{
                "code": getattr(exc, 'code', 'authentication_failed'),
                "detail": str(exc.detail) if hasattr(exc, 'detail') else str(exc)
            }]
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Tratamento para rate limiting (throttling)
    if isinstance(exc, Throttled):
        wait_seconds = exc.wait
        if wait_seconds is not None:
            wait_minutes = int(wait_seconds / 60) + 1
            message = f"Muitas requisições. Tente novamente em {wait_minutes} minuto(s)."
        else:
            message = "Muitas requisições. Tente novamente mais tarde."

        return Response({
            "success": False,
            "message": message,
            "data": None,
            "errors": [{
                "code": "rate_limit_exceeded",
                "detail": f"Limite de requisições excedido. Aguarde {int(wait_seconds or 60)} segundos."
            }]
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # Handler padrão do DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Determina a mensagem apropriada
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                message = exc.detail.get('detail', 'Erro na requisição')
            elif isinstance(exc.detail, list):
                message = exc.detail[0] if exc.detail else 'Erro na requisição'
            else:
                message = str(exc.detail)
        else:
            message = "Erro interno"

        # Determina o código do erro
        error_code = getattr(exc, 'code', 'error')
        if response.status_code == 401:
            error_code = 'authentication_required'
        elif response.status_code == 403:
            error_code = 'permission_denied'
        elif response.status_code == 404:
            error_code = 'not_found'

        custom_response = {
            "success": False,
            "message": message,
            "data": None,
            "errors": [{
                "code": error_code,
                "detail": response.data if isinstance(response.data, (str, dict)) else response.data
            }] if not isinstance(response.data, list) else [
                {"code": error_code, "detail": item} for item in response.data
            ]
        }
        response.data = custom_response

    return response

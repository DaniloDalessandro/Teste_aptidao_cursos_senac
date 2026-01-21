"""
Exceções customizadas para o serviço de IA.
"""


class AIServiceError(Exception):
    """Exceção base para erros do serviço de IA."""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or 'ai_error'
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'message': self.message,
            'details': self.details
        }


class AITimeoutError(AIServiceError):
    """Exceção para timeout na chamada à API."""

    def __init__(self, message: str = "Timeout na comunicação com a IA", details: dict = None):
        super().__init__(message, code='ai_timeout', details=details)


class AIRateLimitError(AIServiceError):
    """Exceção para rate limit excedido."""

    def __init__(self, message: str = "Limite de requisições excedido", retry_after: int = None):
        details = {'retry_after': retry_after} if retry_after else {}
        super().__init__(message, code='ai_rate_limit', details=details)


class AIInvalidResponseError(AIServiceError):
    """Exceção para respostas inválidas da API."""

    def __init__(self, message: str = "Resposta inválida da IA", raw_response: str = None):
        details = {'raw_response': raw_response[:500] if raw_response else None}
        super().__init__(message, code='ai_invalid_response', details=details)


class AIAuthenticationError(AIServiceError):
    """Exceção para erros de autenticação com a API."""

    def __init__(self, message: str = "Erro de autenticação com a API de IA"):
        super().__init__(message, code='ai_authentication_error')


class AIContextTooLongError(AIServiceError):
    """Exceção para contexto que excede o limite de tokens."""

    def __init__(self, message: str = "Contexto da conversa muito longo", token_count: int = None):
        details = {'token_count': token_count} if token_count else {}
        super().__init__(message, code='ai_context_too_long', details=details)

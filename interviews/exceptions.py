class AIServiceError(Exception):
    """Erro base para serviços de IA."""
    pass


class AITimeoutError(AIServiceError):
    """Erro de timeout na comunicação com a IA."""
    def __init__(self, message="O serviço de IA demorou muito para responder."):
        self.message = message
        super().__init__(self.message)


class AIConnectionError(AIServiceError):
    """Erro de conexão com o serviço de IA."""
    def __init__(self, message="Erro ao comunicar com o serviço de IA."):
        self.message = message
        super().__init__(self.message)


class AIRateLimitError(AIServiceError):
    """Erro de rate limit da API."""
    def __init__(self, retry_after=60, message=None):
        self.retry_after = retry_after
        self.message = message or f"Limite de requisições excedido. Tente novamente em {retry_after} segundos."
        super().__init__(self.message)


class AIResponseError(AIServiceError):
    """Erro na resposta da IA."""
    def __init__(self, message="Resposta inválida do serviço de IA."):
        self.message = message
        super().__init__(self.message)


class AIAuthenticationError(AIServiceError):
    """Erro de autenticação com a API."""
    def __init__(self, message="Erro de autenticação com o serviço de IA."):
        self.message = message
        super().__init__(self.message)


class ChatCompletedError(Exception):
    """Erro quando tenta enviar mensagem para chat já concluído."""
    def __init__(self, message="Esta entrevista já foi concluída."):
        self.message = message
        super().__init__(self.message)

"""
Serviço centralizado de integração com APIs de IA.
"""
import logging
import time
from typing import List, Dict, Optional, Union
from functools import wraps

import requests
from requests.exceptions import Timeout, RequestException
from django.conf import settings

from .exceptions import (
    AIServiceError,
    AITimeoutError,
    AIRateLimitError,
    AIInvalidResponseError,
    AIAuthenticationError,
    AIContextTooLongError,
)
from .response import AIResponse
from .context import ConversationContext, Message
from .prompts import PromptRegistry, PromptVersion

logger = logging.getLogger(__name__)


def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    Decorator para retry com backoff exponencial.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (AITimeoutError, AIRateLimitError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                            f"Aguardando {wait_time}s antes de retry..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Todas as {max_retries} tentativas falharam.")
                except AIServiceError:
                    raise
            raise last_exception
        return wrapper
    return decorator


class AIService:
    """
    Serviço centralizado para integração com APIs de IA.

    Características:
    - Retry automático com backoff exponencial
    - Timeout configurável
    - Logging de sucesso e falha
    - Validação de respostas
    - Gerenciamento de contexto
    """

    DEFAULT_TIMEOUT = 30  # segundos
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MAX_TOKENS = 1000

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        timeout: int = None,
        max_retries: int = None,
        prompt_version: PromptVersion = None,
    ):
        """
        Inicializa o serviço de IA.

        Args:
            model: Modelo a usar (default: settings.GPT_MODEL)
            api_key: Chave da API (default: settings.OPEN_AI_API_KEY)
            base_url: URL base da API (default: settings.OPEN_AI_BASE_URL)
            timeout: Timeout em segundos
            max_retries: Número máximo de retentativas
            prompt_version: Versão dos prompts a usar
        """
        self._model = model or getattr(settings, 'GPT_MODEL', 'gpt-3.5-turbo')
        self._api_key = api_key or getattr(settings, 'OPEN_AI_API_KEY', '')
        self._base_url = base_url or getattr(settings, 'OPEN_AI_BASE_URL', 'https://api.openai.com/v1')
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self._prompt_version = prompt_version or PromptVersion.V1

        if not self._api_key:
            logger.warning("API key não configurada para o serviço de IA")

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> PromptVersion:
        return self._prompt_version

    def get_prompt(self, name: str, **variables) -> str:
        """
        Obtém e renderiza um prompt pelo nome.

        Args:
            name: Nome do prompt
            **variables: Variáveis para substituição

        Returns:
            Prompt renderizado
        """
        template = PromptRegistry.get(name, self._prompt_version)
        if not template:
            raise AIServiceError(
                f"Prompt '{name}' não encontrado para versão {self._prompt_version.value}",
                code='prompt_not_found'
            )

        missing = template.validate_variables(**variables)
        if missing:
            logger.warning(f"Variáveis faltantes no prompt '{name}': {missing}")

        return template.render(**variables)

    @with_retry(max_retries=3, backoff_factor=1.0)
    def chat_completion(
        self,
        messages: Union[List[Dict], ConversationContext],
        max_tokens: int = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        Envia mensagens para a API e obtém uma resposta.

        Args:
            messages: Lista de mensagens ou ConversationContext
            max_tokens: Limite de tokens na resposta
            temperature: Criatividade da resposta (0-2)
            **kwargs: Parâmetros adicionais para a API

        Returns:
            AIResponse com a resposta da IA
        """
        # Converte contexto para formato de API se necessário
        if isinstance(messages, ConversationContext):
            api_messages = messages.to_api_format()
        else:
            api_messages = messages

        # Valida mensagens
        if not api_messages:
            raise AIServiceError("Nenhuma mensagem fornecida", code='empty_messages')

        # Prepara payload
        payload = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens or self.DEFAULT_MAX_TOKENS,
            "temperature": temperature,
            **kwargs
        }

        # Headers
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Log de início
        logger.info(
            f"AI Request: model={self._model}, "
            f"messages={len(api_messages)}, "
            f"max_tokens={payload['max_tokens']}"
        )

        start_time = time.time()

        try:
            response = requests.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout
            )

            elapsed_time = time.time() - start_time

            # Trata códigos de erro HTTP
            self._handle_http_errors(response)

            # Parse da resposta
            data = response.json()

            # Valida resposta
            ai_response = self._parse_response(data)

            # Log de sucesso
            logger.info(
                f"AI Response: status=success, "
                f"model={ai_response.model}, "
                f"tokens={ai_response.total_tokens}, "
                f"time={elapsed_time:.2f}s"
            )

            return ai_response

        except Timeout:
            elapsed_time = time.time() - start_time
            logger.error(f"AI Timeout após {elapsed_time:.2f}s")
            raise AITimeoutError(
                f"Timeout após {self._timeout} segundos",
                details={'elapsed_time': elapsed_time}
            )

        except RequestException as e:
            elapsed_time = time.time() - start_time
            logger.error(f"AI Request Error: {str(e)}")
            raise AIServiceError(
                f"Erro na comunicação com a API: {str(e)}",
                code='request_error',
                details={'elapsed_time': elapsed_time}
            )

    def _handle_http_errors(self, response: requests.Response) -> None:
        """Trata erros HTTP da resposta."""
        if response.status_code == 200:
            return

        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Erro desconhecido')
        except Exception:
            error_message = response.text[:500]

        if response.status_code == 401:
            logger.error("AI Authentication Error")
            raise AIAuthenticationError()

        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            logger.warning(f"AI Rate Limit: retry_after={retry_after}")
            raise AIRateLimitError(retry_after=int(retry_after) if retry_after else None)

        elif response.status_code == 400:
            if 'context_length' in error_message.lower():
                logger.error(f"AI Context Too Long: {error_message}")
                raise AIContextTooLongError(message=error_message)
            else:
                logger.error(f"AI Bad Request: {error_message}")
                raise AIServiceError(error_message, code='bad_request')

        else:
            logger.error(f"AI HTTP Error {response.status_code}: {error_message}")
            raise AIServiceError(
                f"Erro HTTP {response.status_code}: {error_message}",
                code=f'http_{response.status_code}'
            )

    def _parse_response(self, data: dict) -> AIResponse:
        """
        Parse e valida a resposta da API.
        """
        if not data:
            raise AIInvalidResponseError("Resposta vazia da API")

        if 'error' in data:
            error_msg = data['error'].get('message', 'Erro desconhecido')
            logger.error(f"AI API Error: {error_msg}")
            raise AIServiceError(error_msg, code='api_error')

        choices = data.get('choices', [])
        if not choices:
            raise AIInvalidResponseError(
                "Resposta sem choices",
                raw_response=str(data)[:500]
            )

        message = choices[0].get('message', {})
        content = message.get('content', '').strip()

        if not content:
            raise AIInvalidResponseError(
                "Resposta com conteúdo vazio",
                raw_response=str(data)[:500]
            )

        return AIResponse.from_openai_response(data, self._model)

    def create_interview_context(
        self,
        job_title: str,
        job_requirements: str,
        job_responsibilities: str,
        job_level: str = None,
        max_tokens: int = 4000,
    ) -> ConversationContext:
        """
        Cria um contexto de conversa para uma entrevista.

        Args:
            job_title: Título do curso/vaga
            job_requirements: Requisitos do curso
            job_responsibilities: Responsabilidades/competências
            job_level: Nível do curso (opcional, para v2)
            max_tokens: Limite de tokens no contexto

        Returns:
            ConversationContext configurado
        """
        context = ConversationContext(max_tokens=max_tokens)

        # Obtém e renderiza o prompt do sistema
        variables = {
            'job_title': job_title,
            'job_requirements': job_requirements,
            'job_responsibilities': job_responsibilities,
        }

        if job_level and self._prompt_version == PromptVersion.V2:
            variables['job_level'] = job_level

        system_prompt = self.get_prompt('interview_system', **variables)
        context.set_system_message(system_prompt)

        logger.info(f"Interview context created: job='{job_title}', version={self._prompt_version.value}")

        return context

    def get_feedback_prompt(self, job_title: str = None) -> str:
        """
        Obtém o prompt para geração de feedback.

        Args:
            job_title: Título do curso (opcional, para v2)

        Returns:
            Prompt de feedback
        """
        variables = {}
        if job_title and self._prompt_version == PromptVersion.V2:
            variables['job_title'] = job_title

        return self.get_prompt('interview_feedback', **variables)


# Singleton instance para uso global
_default_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    Obtém a instância padrão do serviço de IA.
    Use esta função para obter o serviço em vez de instanciar diretamente.
    """
    global _default_service
    if _default_service is None:
        _default_service = AIService()
    return _default_service


def reset_ai_service() -> None:
    """Reseta a instância padrão (útil para testes)."""
    global _default_service
    _default_service = None

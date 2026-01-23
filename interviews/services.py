"""
Serviço de Chat para entrevistas.
Usa LangChain por padrão, com fallback para implementação legacy.
"""
import logging
import time
import requests

from django.conf import settings
from django.db import transaction

from .exceptions import (
    AITimeoutError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseError,
    AIAuthenticationError,
    ChatCompletedError,
)

logger = logging.getLogger(__name__)


def get_chat_service():
    """
    Factory para obter o serviço de chat apropriado.
    Usa LangChain por padrão, fallback para legacy se não configurado.
    """
    provider = settings.AI_SERVICE.get('PROVIDER', 'gemini')

    # Usa LangChain para providers modernos
    if provider in ('gemini', 'openai'):
        try:
            from .services_langchain import ChatServiceLangChain
            logger.info(f"Usando ChatServiceLangChain com provider: {provider}")
            return ChatServiceLangChain()
        except ImportError as e:
            logger.warning(f"LangChain não disponível, usando legacy: {e}")

    # Fallback para implementação legacy
    logger.info("Usando ChatService legacy")
    return ChatService()


class GptService:
    def __init__(self):
        self.__model = settings.GPT_MODEL
        self.__open_ai_api_key = settings.OPEN_AI_API_KEY
        self.__open_ai_base_url = settings.OPEN_AI_BASE_URL
        self.__timeout = settings.AI_SERVICE.get('TIMEOUT', 30)
        self.__max_retries = settings.AI_SERVICE.get('MAX_RETRIES', 3)

    def get_chat_completion(self, messages):
        """Obtém resposta da IA com retry automático."""
        payload = {
            "model": self.__model,
            "messages": [self.__convert_to_chat_message_format(message) for message in messages]
        }
        headers = {
            "Authorization": f"Bearer {self.__open_ai_api_key}",
            "Content-Type": "application/json"
        }

        last_exception = None

        for attempt in range(self.__max_retries):
            try:
                response = requests.post(
                    f"{self.__open_ai_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.__timeout
                )

                # Trata erros HTTP específicos
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit atingido. Retry-After: {retry_after}s")
                    if attempt < self.__max_retries - 1:
                        time.sleep(min(retry_after, 10))  # Espera no máximo 10s
                        continue
                    raise AIRateLimitError(retry_after=retry_after)

                if response.status_code == 401:
                    logger.error("Erro de autenticação com a API OpenAI")
                    raise AIAuthenticationError()

                if response.status_code == 503:
                    logger.warning(f"Serviço indisponível. Tentativa {attempt + 1}/{self.__max_retries}")
                    if attempt < self.__max_retries - 1:
                        time.sleep(self.__calculate_backoff(attempt))
                        continue

                response.raise_for_status()

                body = response.json()
                content = body["choices"][0]["message"]["content"]
                logger.info(f"Resposta da IA obtida com sucesso. Tentativa: {attempt + 1}")
                return content

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout na tentativa {attempt + 1}/{self.__max_retries}")
                last_exception = AITimeoutError()
                if attempt < self.__max_retries - 1:
                    time.sleep(self.__calculate_backoff(attempt))
                    continue

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Erro de conexão na tentativa {attempt + 1}/{self.__max_retries}: {e}")
                last_exception = AIConnectionError()
                if attempt < self.__max_retries - 1:
                    time.sleep(self.__calculate_backoff(attempt))
                    continue

            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição: {e}")
                last_exception = AIConnectionError(f"Erro na comunicação: {str(e)}")
                break

            except (KeyError, IndexError) as e:
                logger.error(f"Resposta inesperada da API: {e}")
                raise AIResponseError()

            except (AIRateLimitError, AIAuthenticationError):
                raise

        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Todas as {self.__max_retries} tentativas falharam")
        raise last_exception or AIConnectionError()

    def __calculate_backoff(self, attempt):
        """Calcula tempo de espera com backoff exponencial."""
        return min(2 ** attempt, 10)  # Máximo 10 segundos

    def __convert_to_chat_message_format(self, message):
        return {
            "role": message.role,
            "content": message.content
        }


class ChatService:
    def __init__(self):
        self.gpt_service = GptService()
        self.max_questions = settings.INTERVIEW_MAX_QUESTIONS
        self.feedback_prompt = settings.INTERVIEW_FEEDBACK_PROMPT

    def process_user_message(self, chat, content):
        """
        Processa uma mensagem do usuário e gera resposta da IA.
        Usa transação para rollback em caso de falha.
        """
        from .models import Message

        if chat.completed:
            raise ChatCompletedError()

        try:
            with transaction.atomic():
                # Cria mensagem do usuário
                user_message = Message.objects.create(
                    chat=chat,
                    role="user",
                    content=content
                )

                # Verifica se atingiu o limite de perguntas
                assistant_count = chat.messages.filter(role="assistant").count()
                is_final = assistant_count >= self.max_questions

                if is_final:
                    # Adiciona prompt de feedback
                    Message.objects.create(
                        chat=chat,
                        role="system",
                        content=self.feedback_prompt
                    )

                # Gera resposta da IA (pode lançar exceção)
                ai_response = self.gpt_service.get_chat_completion(chat.messages.all())

                # Salva resposta da IA
                assistant_message = Message.objects.create(
                    chat=chat,
                    role="assistant",
                    content=ai_response
                )

                # Marca chat como concluído se for a última pergunta
                if is_final:
                    chat.completed = True
                    chat.save()

                return assistant_message

        except (AITimeoutError, AIConnectionError, AIRateLimitError, AIResponseError) as e:
            # Rollback automático pela transação
            logger.error(f"Erro ao processar mensagem: {e}")
            raise

    def create_chat(self, job):
        """Cria um novo chat para uma entrevista."""
        from .models import Chat
        return Chat.objects.create(job=job)

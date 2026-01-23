"""
Serviço de Chat usando LangChain com suporte a Gemini e OpenAI.
"""
import logging
from typing import Optional

from django.conf import settings
from django.db import transaction
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.callbacks import BaseCallbackHandler

from .schemas import FeedbackResult
from .exceptions import (
    AIServiceError,
    AITimeoutError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseError,
    AIAuthenticationError,
    ChatCompletedError,
)

logger = logging.getLogger(__name__)


class TokenCounterCallback(BaseCallbackHandler):
    """Callback para contagem de tokens e logging."""

    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def on_llm_end(self, response, **kwargs):
        """Chamado quando o LLM termina de processar."""
        if hasattr(response, 'llm_output') and response.llm_output:
            usage = response.llm_output.get('token_usage', {})
            self.total_tokens = usage.get('total_tokens', 0)
            self.prompt_tokens = usage.get('prompt_tokens', 0)
            self.completion_tokens = usage.get('completion_tokens', 0)
            logger.info(
                f"Tokens utilizados - Total: {self.total_tokens}, "
                f"Prompt: {self.prompt_tokens}, Completion: {self.completion_tokens}"
            )


def get_llm():
    """
    Factory para criar o LLM baseado no provider configurado.
    Suporta Gemini e OpenAI.
    """
    provider = settings.AI_SERVICE.get('PROVIDER', 'gemini')
    temperature = settings.AI_SERVICE.get('TEMPERATURE', 0.7)
    max_retries = settings.AI_SERVICE.get('MAX_RETRIES', 3)
    timeout = settings.AI_SERVICE.get('TIMEOUT', 30)

    if provider == 'gemini':
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
            convert_system_message_to_human=True,  # Gemini não suporta system message nativamente
        )

    elif provider == 'openai':
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.GPT_MODEL,
            api_key=settings.OPEN_AI_API_KEY,
            base_url=settings.OPEN_AI_BASE_URL,
            temperature=temperature,
            max_retries=max_retries,
            request_timeout=timeout,
        )

    else:
        raise ValueError(f"Provider de LLM não suportado: {provider}")


class LangChainService:
    """
    Serviço de IA usando LangChain.
    Suporta múltiplos providers (Gemini, OpenAI) com interface unificada.
    """

    def __init__(self):
        self.llm = get_llm()
        self.callback = TokenCounterCallback()

        # Parser para output de texto simples
        self.str_parser = StrOutputParser()

        # Parser para feedback estruturado
        self.feedback_parser = PydanticOutputParser(pydantic_object=FeedbackResult)

        # Prompt template para entrevista
        self.interview_prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        # Prompt template para feedback estruturado
        self.feedback_prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="history"),
            ("system", """
Agora, gere o feedback final do candidato em formato JSON.
{format_instructions}

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional.
"""),
        ])

        # Chains
        self.interview_chain = (
            self.interview_prompt
            | self.llm
            | self.str_parser
        )

    def _convert_to_langchain_message(self, message) -> BaseMessage:
        """Converte mensagem do banco para formato LangChain."""
        if message.role == "user":
            return HumanMessage(content=message.content)
        elif message.role == "assistant":
            return AIMessage(content=message.content)
        else:  # system
            return SystemMessage(content=message.content)

    def _convert_history(self, messages) -> list[BaseMessage]:
        """Converte histórico do banco para formato LangChain."""
        return [self._convert_to_langchain_message(m) for m in messages]

    def get_response(self, system_prompt: str, history: list, user_input: str) -> str:
        """
        Obtém resposta do LLM para uma mensagem.

        Args:
            system_prompt: Prompt do sistema com instruções
            history: Histórico de mensagens (objetos do banco)
            user_input: Mensagem do usuário

        Returns:
            Resposta do LLM como string
        """
        try:
            langchain_history = self._convert_history(history)

            response = self.interview_chain.invoke(
                {
                    "system_prompt": system_prompt,
                    "history": langchain_history,
                    "input": user_input,
                },
                config={"callbacks": [self.callback]}
            )

            logger.info(f"Resposta obtida do LLM ({settings.AI_SERVICE.get('PROVIDER')})")
            return response

        except Exception as e:
            logger.error(f"Erro ao obter resposta do LLM: {e}")
            self._handle_exception(e)

    def get_structured_feedback(self, system_prompt: str, history: list) -> FeedbackResult:
        """
        Obtém feedback estruturado do candidato.

        Args:
            system_prompt: Prompt do sistema
            history: Histórico completo da entrevista

        Returns:
            FeedbackResult com dados estruturados
        """
        try:
            langchain_history = self._convert_history(history)

            # Chain com parser estruturado
            feedback_chain = (
                self.feedback_prompt
                | self.llm
                | self.feedback_parser
            )

            response = feedback_chain.invoke(
                {
                    "system_prompt": system_prompt,
                    "history": langchain_history,
                    "format_instructions": self.feedback_parser.get_format_instructions(),
                },
                config={"callbacks": [self.callback]}
            )

            logger.info(f"Feedback estruturado gerado: aderência={response.aderencia_percentual}%")
            return response

        except Exception as e:
            logger.error(f"Erro ao gerar feedback estruturado: {e}")
            # Fallback: retorna feedback básico
            return self._get_fallback_feedback(system_prompt, history)

    def _get_fallback_feedback(self, system_prompt: str, history: list) -> str:
        """Fallback para feedback em texto quando o estruturado falha."""
        try:
            langchain_history = self._convert_history(history)

            fallback_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("system", settings.INTERVIEW_FEEDBACK_PROMPT),
            ])

            fallback_chain = fallback_prompt | self.llm | self.str_parser

            return fallback_chain.invoke(
                {
                    "system_prompt": system_prompt,
                    "history": langchain_history,
                },
                config={"callbacks": [self.callback]}
            )
        except Exception as e:
            logger.error(f"Erro no fallback de feedback: {e}")
            self._handle_exception(e)

    def _handle_exception(self, e: Exception):
        """Converte exceções do LangChain para exceções da aplicação."""
        error_str = str(e).lower()

        if "timeout" in error_str or "timed out" in error_str:
            raise AITimeoutError()
        elif "rate limit" in error_str or "429" in error_str:
            raise AIRateLimitError()
        elif "authentication" in error_str or "401" in error_str or "api key" in error_str:
            raise AIAuthenticationError()
        elif "connection" in error_str or "network" in error_str:
            raise AIConnectionError()
        else:
            raise AIResponseError(f"Erro do LLM: {str(e)}")


class ChatServiceLangChain:
    """
    Serviço de Chat usando LangChain.
    Substitui o ChatService original com implementação mais robusta.
    """

    def __init__(self):
        self.llm_service = LangChainService()
        self.max_questions = settings.INTERVIEW_MAX_QUESTIONS
        self.feedback_prompt = settings.INTERVIEW_FEEDBACK_PROMPT

    def process_user_message(self, chat, content: str):
        """
        Processa uma mensagem do usuário e gera resposta da IA.

        Args:
            chat: Objeto Chat do banco
            content: Conteúdo da mensagem do usuário

        Returns:
            Mensagem do assistente criada
        """
        from .models import Message

        if chat.completed:
            raise ChatCompletedError()

        try:
            with transaction.atomic():
                # Cria mensagem do usuário
                Message.objects.create(
                    chat=chat,
                    role="user",
                    content=content
                )

                # Conta perguntas do assistente
                assistant_count = chat.messages.filter(role="assistant").count()
                is_final = assistant_count >= self.max_questions

                # Obtém o prompt do sistema (primeira mensagem)
                system_message = chat.messages.filter(role="system").first()
                system_prompt = system_message.content if system_message else ""

                # Obtém histórico (excluindo a primeira mensagem do sistema)
                history = list(chat.messages.exclude(id=system_message.id if system_message else 0))

                if is_final:
                    # Gera feedback estruturado na última interação
                    try:
                        feedback = self.llm_service.get_structured_feedback(
                            system_prompt=system_prompt,
                            history=history
                        )
                        # Formata o feedback para exibição
                        ai_response = self._format_feedback(feedback)
                    except Exception:
                        # Fallback para feedback em texto
                        ai_response = self.llm_service._get_fallback_feedback(
                            system_prompt=system_prompt,
                            history=history
                        )
                else:
                    # Resposta normal da entrevista
                    ai_response = self.llm_service.get_response(
                        system_prompt=system_prompt,
                        history=history[:-1],  # Exclui a mensagem atual do histórico
                        user_input=content
                    )

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
            logger.error(f"Erro ao processar mensagem: {e}")
            raise

    def _format_feedback(self, feedback: FeedbackResult) -> str:
        """Formata o feedback estruturado para exibição."""
        positivos = "\n".join(f"  - {p}" for p in feedback.pontos_positivos)
        negativos = "\n".join(f"  - {n}" for n in feedback.pontos_negativos)
        melhorias = "\n".join(f"  - {m}" for m in feedback.melhorias_sugeridas)

        resultado = "APTO" if feedback.apto else "NECESSITA DESENVOLVIMENTO"

        text = f"""
## Feedback da Entrevista

### Resumo
{feedback.resumo}

### Pontos Positivos
{positivos}

### Pontos a Desenvolver
{negativos}

### Sugestões de Melhoria
{melhorias}

### Resultado
- **Aderência ao curso:** {feedback.aderencia_percentual}%
- **Status:** {resultado}
"""

        if feedback.curso_recomendado:
            text += f"- **Curso recomendado:** {feedback.curso_recomendado}\n"

        return text.strip()

    def create_chat(self, job):
        """Cria um novo chat para uma entrevista."""
        from .models import Chat
        return Chat.objects.create(job=job)

"""
Gerenciamento de contexto de conversas para o serviço de IA.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class MessageRole(Enum):
    """Roles possíveis para mensagens."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """
    Representa uma mensagem no contexto da conversa.
    """
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_api_format(self) -> Dict[str, str]:
        """Converte para o formato esperado pela API."""
        return {
            "role": self.role.value,
            "content": self.content
        }

    @classmethod
    def system(cls, content: str, **metadata) -> 'Message':
        """Cria uma mensagem de sistema."""
        return cls(role=MessageRole.SYSTEM, content=content, metadata=metadata)

    @classmethod
    def user(cls, content: str, **metadata) -> 'Message':
        """Cria uma mensagem de usuário."""
        return cls(role=MessageRole.USER, content=content, metadata=metadata)

    @classmethod
    def assistant(cls, content: str, **metadata) -> 'Message':
        """Cria uma mensagem do assistente."""
        return cls(role=MessageRole.ASSISTANT, content=content, metadata=metadata)


class ConversationContext:
    """
    Gerencia o contexto de uma conversa com a IA.
    """

    # Estimativa aproximada de tokens por caractere (para português)
    CHARS_PER_TOKEN = 4

    def __init__(self, max_tokens: int = 4000, max_messages: int = 50):
        """
        Inicializa o contexto da conversa.

        Args:
            max_tokens: Limite máximo estimado de tokens no contexto
            max_messages: Limite máximo de mensagens no histórico
        """
        self._messages: List[Message] = []
        self._max_tokens = max_tokens
        self._max_messages = max_messages
        self._system_message: Optional[Message] = None

    @property
    def messages(self) -> List[Message]:
        """Retorna todas as mensagens incluindo a do sistema."""
        if self._system_message:
            return [self._system_message] + self._messages
        return self._messages

    @property
    def message_count(self) -> int:
        """Número total de mensagens (excluindo sistema)."""
        return len(self._messages)

    @property
    def estimated_tokens(self) -> int:
        """Estimativa do número de tokens no contexto."""
        total_chars = sum(len(m.content) for m in self.messages)
        return total_chars // self.CHARS_PER_TOKEN

    def set_system_message(self, content: str, **metadata) -> None:
        """Define a mensagem de sistema (sempre a primeira)."""
        self._system_message = Message.system(content, **metadata)

    def add_user_message(self, content: str, **metadata) -> None:
        """Adiciona uma mensagem do usuário."""
        self._messages.append(Message.user(content, **metadata))
        self._trim_if_needed()

    def add_assistant_message(self, content: str, **metadata) -> None:
        """Adiciona uma mensagem do assistente."""
        self._messages.append(Message.assistant(content, **metadata))
        self._trim_if_needed()

    def add_message(self, role: str, content: str, **metadata) -> None:
        """Adiciona uma mensagem com role especificado."""
        role_enum = MessageRole(role)
        if role_enum == MessageRole.SYSTEM:
            self.set_system_message(content, **metadata)
        else:
            self._messages.append(Message(role=role_enum, content=content, metadata=metadata))
            self._trim_if_needed()

    def to_api_format(self) -> List[Dict[str, str]]:
        """Converte todas as mensagens para o formato da API."""
        return [m.to_api_format() for m in self.messages]

    def _trim_if_needed(self) -> None:
        """
        Remove mensagens antigas se necessário para respeitar os limites.
        Mantém sempre a mensagem do sistema e as mensagens mais recentes.
        """
        # Trim por número de mensagens
        while len(self._messages) > self._max_messages:
            self._remove_oldest_pair()

        # Trim por tokens estimados
        while self.estimated_tokens > self._max_tokens and len(self._messages) > 2:
            self._remove_oldest_pair()

    def _remove_oldest_pair(self) -> None:
        """
        Remove o par mais antigo de mensagens (user + assistant).
        Isso mantém a coerência da conversa.
        """
        if len(self._messages) >= 2:
            # Remove as duas primeiras mensagens (geralmente user + assistant)
            self._messages = self._messages[2:]
        elif len(self._messages) == 1:
            self._messages = []

    def clear(self) -> None:
        """Limpa todas as mensagens exceto a do sistema."""
        self._messages = []

    def get_summary(self) -> Dict[str, Any]:
        """Retorna um resumo do estado do contexto."""
        return {
            'message_count': self.message_count,
            'estimated_tokens': self.estimated_tokens,
            'has_system_message': self._system_message is not None,
            'max_tokens': self._max_tokens,
            'max_messages': self._max_messages,
        }

    @classmethod
    def from_message_queryset(cls, queryset, max_tokens: int = 4000) -> 'ConversationContext':
        """
        Cria um contexto a partir de um QuerySet de mensagens do Django.

        Args:
            queryset: QuerySet de objetos Message do Django
            max_tokens: Limite máximo de tokens
        """
        context = cls(max_tokens=max_tokens)

        for message in queryset.order_by('created_at'):
            if message.role == 'system' and context._system_message is None:
                context.set_system_message(message.content)
            elif message.role == 'system':
                # Mensagens de sistema adicionais vão como mensagens normais
                context._messages.append(Message.system(message.content))
            else:
                context.add_message(message.role, message.content)

        return context

"""
Modelo de resposta padronizado do serviço de IA.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class AIResponse:
    """
    Resposta padronizada do serviço de IA.
    """
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = 'stop'
    created_at: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Verifica se a resposta foi completada normalmente."""
        return self.finish_reason == 'stop'

    @property
    def was_truncated(self) -> bool:
        """Verifica se a resposta foi truncada por limite de tokens."""
        return self.finish_reason == 'length'

    @property
    def was_filtered(self) -> bool:
        """Verifica se a resposta foi filtrada por conteúdo."""
        return self.finish_reason == 'content_filter'

    def to_dict(self) -> dict:
        """Converte a resposta para dicionário."""
        return {
            'content': self.content,
            'model': self.model,
            'tokens': {
                'prompt': self.prompt_tokens,
                'completion': self.completion_tokens,
                'total': self.total_tokens,
            },
            'finish_reason': self.finish_reason,
            'created_at': self.created_at.isoformat(),
            'request_id': self.request_id,
        }

    @classmethod
    def from_openai_response(cls, response: dict, model: str) -> 'AIResponse':
        """
        Cria uma AIResponse a partir da resposta da API OpenAI.
        """
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})
        usage = response.get('usage', {})

        return cls(
            content=message.get('content', ''),
            model=model,
            prompt_tokens=usage.get('prompt_tokens', 0),
            completion_tokens=usage.get('completion_tokens', 0),
            total_tokens=usage.get('total_tokens', 0),
            finish_reason=choice.get('finish_reason', 'stop'),
            raw_response=response,
            request_id=response.get('id'),
        )

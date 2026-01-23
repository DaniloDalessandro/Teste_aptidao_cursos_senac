"""
Schemas Pydantic para output estruturado do LangChain.
"""
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackResult(BaseModel):
    """Schema para feedback estruturado da entrevista."""

    pontos_positivos: list[str] = Field(
        description="Lista de pontos positivos identificados nas respostas do candidato"
    )
    pontos_negativos: list[str] = Field(
        description="Lista de pontos negativos ou lacunas identificadas"
    )
    melhorias_sugeridas: list[str] = Field(
        description="Lista de sugestões de melhoria para o candidato"
    )
    aderencia_percentual: int = Field(
        ge=0,
        le=100,
        description="Percentual de aderência do candidato ao curso (0-100)"
    )
    curso_recomendado: Optional[str] = Field(
        default=None,
        description="Curso alternativo recomendado, se aplicável (ex: Introdução à Informática)"
    )
    resumo: str = Field(
        description="Resumo geral do desempenho do candidato na entrevista"
    )
    apto: bool = Field(
        description="Indica se o candidato está apto para o curso"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pontos_positivos": [
                    "Demonstrou interesse genuíno pela área",
                    "Possui conhecimentos básicos de informática"
                ],
                "pontos_negativos": [
                    "Pouca experiência prática",
                    "Dificuldade em explicar conceitos técnicos"
                ],
                "melhorias_sugeridas": [
                    "Praticar mais programação básica",
                    "Estudar fundamentos de lógica"
                ],
                "aderencia_percentual": 75,
                "curso_recomendado": None,
                "resumo": "Candidato com bom potencial, necessita desenvolver habilidades práticas.",
                "apto": True
            }
        }

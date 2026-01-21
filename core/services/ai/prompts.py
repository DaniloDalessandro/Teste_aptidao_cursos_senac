"""
Sistema de prompts versionados para o serviço de IA.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class PromptVersion(Enum):
    """Versões disponíveis de prompts."""
    V1 = "v1"
    V2 = "v2"


@dataclass
class PromptTemplate:
    """
    Template de prompt com suporte a variáveis.
    """
    name: str
    version: PromptVersion
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)

    def render(self, **kwargs) -> str:
        """
        Renderiza o template substituindo as variáveis.
        """
        content = self.template
        for var in self.variables:
            placeholder = "{" + var + "}"
            value = kwargs.get(var, "")
            content = content.replace(placeholder, str(value))
        return content

    def validate_variables(self, **kwargs) -> List[str]:
        """
        Valida se todas as variáveis obrigatórias foram fornecidas.
        Retorna lista de variáveis faltantes.
        """
        missing = []
        for var in self.variables:
            if var not in kwargs or kwargs[var] is None:
                missing.append(var)
        return missing


class PromptRegistry:
    """
    Registro centralizado de prompts versionados.
    """

    _prompts: Dict[str, Dict[PromptVersion, PromptTemplate]] = {}
    _default_version: PromptVersion = PromptVersion.V1

    @classmethod
    def register(cls, prompt: PromptTemplate) -> None:
        """Registra um novo prompt."""
        if prompt.name not in cls._prompts:
            cls._prompts[prompt.name] = {}
        cls._prompts[prompt.name][prompt.version] = prompt

    @classmethod
    def get(cls, name: str, version: PromptVersion = None) -> Optional[PromptTemplate]:
        """
        Obtém um prompt pelo nome e versão.
        Se versão não especificada, usa a versão padrão.
        """
        version = version or cls._default_version
        prompts = cls._prompts.get(name, {})
        return prompts.get(version)

    @classmethod
    def set_default_version(cls, version: PromptVersion) -> None:
        """Define a versão padrão de prompts."""
        cls._default_version = version

    @classmethod
    def list_prompts(cls) -> Dict[str, List[str]]:
        """Lista todos os prompts registrados e suas versões."""
        return {
            name: [v.value for v in versions.keys()]
            for name, versions in cls._prompts.items()
        }


# =============================================================================
# PROMPTS V1 - Versão inicial
# =============================================================================

INTERVIEW_SYSTEM_PROMPT_V1 = PromptTemplate(
    name="interview_system",
    version=PromptVersion.V1,
    description="Prompt inicial do sistema para entrevistas de aptidão",
    variables=["job_title", "job_requirements", "job_responsibilities"],
    template="""Você é Ada, uma assistente virtual especializada em avaliar a aptidão de candidatos para cursos técnicos do SENAC.

Curso: {job_title}

Pré-requisitos do curso:
{job_requirements}

Competências desenvolvidas:
{job_responsibilities}

Sua tarefa é conduzir uma entrevista amigável para avaliar se o candidato tem o perfil adequado para este curso.

Diretrizes:
1. Faça perguntas claras e objetivas, uma de cada vez
2. Avalie conhecimentos prévios, motivação e expectativas
3. Seja acolhedor e encoraje o candidato
4. Limite suas respostas a no máximo 3 parágrafos
5. Após 5 interações, você receberá instruções para o feedback final

Comece se apresentando brevemente e fazendo a primeira pergunta ao candidato."""
)

INTERVIEW_FEEDBACK_PROMPT_V1 = PromptTemplate(
    name="interview_feedback",
    version=PromptVersion.V1,
    description="Prompt para geração do feedback final da entrevista",
    variables=[],
    template="""Realize o feedback do candidato ao curso considerando toda a conversa anterior.

O feedback deve conter:

1. **Pontos Positivos**: Destaque os aspectos favoráveis identificados no perfil do candidato.

2. **Pontos a Desenvolver**: Indique áreas que precisam de atenção ou aprimoramento.

3. **Recomendações**: Sugira ações ou cursos complementares se necessário.

4. **Aderência ao Curso**: Apresente uma porcentagem de 0 a 100 indicando a compatibilidade do candidato com o curso.

5. **Conclusão**: Se o candidato não demonstrar conhecimentos básicos de informática, recomende o curso "Introdução à Informática" do SENAC como preparação.

Seja construtivo e motivador em seu feedback."""
)

# =============================================================================
# PROMPTS V2 - Versão aprimorada (futuro)
# =============================================================================

INTERVIEW_SYSTEM_PROMPT_V2 = PromptTemplate(
    name="interview_system",
    version=PromptVersion.V2,
    description="Prompt aprimorado do sistema para entrevistas de aptidão",
    variables=["job_title", "job_requirements", "job_responsibilities", "job_level"],
    template="""Você é Ada, assistente virtual especializada em orientação vocacional do SENAC.

## Curso em Avaliação
**Nome:** {job_title}
**Nível:** {job_level}

## Pré-requisitos
{job_requirements}

## Competências a Desenvolver
{job_responsibilities}

## Sua Missão
Conduzir uma entrevista estruturada para avaliar a aptidão do candidato, considerando:
- Conhecimentos prévios relevantes
- Motivação e objetivos de carreira
- Disponibilidade e comprometimento
- Expectativas realistas sobre o curso

## Regras da Entrevista
1. Uma pergunta por vez, clara e direta
2. Respostas concisas (máximo 200 palavras)
3. Tom profissional mas acolhedor
4. Não faça julgamentos precipitados
5. Após 5 interações, aguarde instruções para o feedback

Inicie com uma apresentação breve e sua primeira pergunta."""
)

INTERVIEW_FEEDBACK_PROMPT_V2 = PromptTemplate(
    name="interview_feedback",
    version=PromptVersion.V2,
    description="Prompt aprimorado para feedback estruturado",
    variables=["job_title"],
    template="""Com base na entrevista realizada para o curso "{job_title}", elabore um relatório de avaliação estruturado.

## Estrutura do Relatório

### 1. Resumo do Perfil
Síntese das principais características identificadas no candidato.

### 2. Análise de Competências
| Competência | Nível Atual | Observações |
|-------------|-------------|-------------|
| (liste as competências avaliadas) |

### 3. Pontos Fortes
- Liste os aspectos positivos identificados

### 4. Áreas de Desenvolvimento
- Liste os pontos que precisam de atenção

### 5. Recomendações
- Cursos preparatórios se necessário
- Materiais de estudo sugeridos
- Próximos passos

### 6. Índice de Aderência
**Porcentagem: X%**
Justificativa da pontuação atribuída.

### 7. Parecer Final
Conclusão com recomendação clara (Apto / Apto com ressalvas / Recomenda-se preparação prévia).

Nota: Se identificar lacunas em informática básica, recomende o curso "Introdução à Informática" do SENAC."""
)


def register_all_prompts():
    """Registra todos os prompts no registry."""
    prompts = [
        INTERVIEW_SYSTEM_PROMPT_V1,
        INTERVIEW_FEEDBACK_PROMPT_V1,
        INTERVIEW_SYSTEM_PROMPT_V2,
        INTERVIEW_FEEDBACK_PROMPT_V2,
    ]
    for prompt in prompts:
        PromptRegistry.register(prompt)


# Registra os prompts ao importar o módulo
register_all_prompts()

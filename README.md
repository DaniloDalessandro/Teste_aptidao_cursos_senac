# Teste de Aptidão - Cursos SENAC

Sistema de avaliação de aptidão para cursos do SENAC utilizando inteligência artificial. A aplicação conduz entrevistas automatizadas com candidatos através de um chatbot alimentado por IA (OpenAI/GPT), avaliando a aderência do candidato ao curso desejado.

## Funcionalidades

- **Gestão de Cursos**: Cadastro de cursos com título, descrição, pré-requisitos, responsabilidades, nível (básico, intermediário, avançado) e skills necessárias
- **Entrevistas Automatizadas**: Chatbot com IA que conduz entrevistas personalizadas baseadas nos requisitos de cada curso
- **Avaliação de Aderência**: Após 5 perguntas, o sistema gera um feedback completo com:
  - Pontos positivos do candidato
  - Pontos a melhorar
  - Porcentagem de aderência ao curso (0-100%)
  - Recomendação do curso de Introdução à Informática quando aplicável
- **API REST**: Endpoints para integração com frontend ou outros sistemas
- **Autenticação JWT**: Sistema seguro de autenticação via tokens

## Tecnologias

- Python 3.11
- Django 4.2
- Django REST Framework
- Simple JWT (autenticação)
- OpenAI API (integração com GPT)
- SQLite (banco de dados)

## Estrutura do Projeto

```
├── core/               # Configurações do projeto Django
├── jobs/               # App de gestão de cursos
│   ├── models.py       # Modelos Job e Skill
│   ├── views.py        # Views dos cursos
│   └── templates/      # Templates HTML
├── interviews/         # App de entrevistas
│   ├── models.py       # Modelos Chat e Message
│   ├── services.py     # Serviço de integração com GPT
│   └── templates/      # Templates HTML
└── templates/          # Templates base
```

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd Teste_aptidao_cursos_senac
```

2. Crie e ative o ambiente virtual:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install django djangorestframework djangorestframework-simplejwt python-decouple requests django-cors-headers
```

4. Configure as variáveis de ambiente criando um arquivo `.env`:
```env
SECRET_KEY=sua-chave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# OpenAI
GPT_MODEL=gpt-3.5-turbo
OPEN_AI_API_KEY=sua-api-key
OPEN_AI_BASE_URL=https://api.openai.com/v1
INITIAL_PROMPT_TEMPLATE=Você é um entrevistador avaliando candidatos para o curso {job_title}.\nRequisitos: {job_requirements}\nResponsabilidades: {job_responsibilities}

# AI Service
AI_TIMEOUT=30
AI_MAX_RETRIES=3
AI_MAX_RESPONSE_TOKENS=1000
AI_CONTEXT_MAX_TOKENS=4000
AI_PROMPT_VERSION=v1

# CORS
CORS_ALLOWED_ORIGINS=
```

5. Execute as migrações:
```bash
python manage.py migrate
```

6. Crie um superusuário:
```bash
python manage.py createsuperuser
```

7. Inicie o servidor:
```bash
python manage.py runserver
```

## Uso

1. Acesse o admin em `http://localhost:8000/admin` para cadastrar cursos
2. Crie um novo curso com título, descrição, pré-requisitos e responsabilidades
3. Inicie uma nova entrevista selecionando o curso
4. O chatbot conduzirá a entrevista e ao final fornecerá o feedback de aderência

## Licença

Este projeto foi desenvolvido para fins educacionais.

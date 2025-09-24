# ValeZap

Aplicação web que simula uma experiência de chat ao estilo WhatsApp Web, conectando-se a um backend externo para orquestrar o fluxo da conversa.

## Tecnologias

- Python 3.11+
- Flask + Gunicorn
- PostgreSQL
- HTML5, CSS3 e JavaScript (frontend responsivo)

## Pré-requisitos

1. Python 3.11 ou superior
2. PostgreSQL 14+ em execução
3. (Opcional) Virtualenv para isolamento do projeto

## Configuração

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Crie o banco de dados e aplique as migrações manuais:

```sql
CREATE DATABASE postgres_python;
\\\\c postgres_python
\i migrations/001_init.sql;
```

> As políticas RLS utilizam a configuração de sessão `app.current_session_id`. A aplicação Flask ajusta esse valor automaticamente para que cada sessão só enxergue as suas próprias mensagens.

## Variáveis de ambiente

| Nome | Descrição | Default |
|------|-----------|---------|
| `SECRET_KEY` | Chave para cookies/CSRF | `valezap-dev-secret` |
| `DATABASE_URL` | URL do PostgreSQL compatível com SQLAlchemy | `postgresql+psycopg://postgres:postgres@localhost:5432/postgres_python` |
| `VALEZAP_BACKEND_URL` | Webhook remoto para disparar mensagens | URL do enunciado |
| `VALEZAP_BACKEND_API_KEY` | API Key opcional enviada ao backend remoto (header `X-API-Key`) | vazio |
| `VALEZAP_WEBHOOK_API_KEY` | Chave obrigatória para validar chamadas recebidas em `/webhook/vale` | `change-me` |
| `VALEZAP_MAX_MESSAGE_LENGTH` | Limite máximo (caracteres) do texto digitado | `700` |
| `VALEZAP_SESSION_HOURS` | Validade (horas) de uma sessão | `2` |
| `VALEZAP_ALLOWED_ORIGINS` | Lista separada por vírgulas para CORS (se necessário) | vazio |

Para desenvolvimento, você pode criar um arquivo `.env` na raiz com os valores acima.

## Executando

```bash
export FLASK_APP=wsgi.py
flask --app wsgi.py run --debug
```

Para produção (via Gunicorn):

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

## Fluxo da aplicação

1. O player acessa `/?player=<ID>`; caso o parâmetro falte, o frontend gera um UUID e atualiza a URL.
2. O frontend solicita uma sessão na API (`POST /api/session`).
3. As mensagens digitadas vão para `POST /api/messages`, que:
   - Valida comprimento/conteúdo;
   - Registra no Postgres;
   - Encaminha para o backend (`VALEZAP_BACKEND_URL`);
   - Persiste a resposta do ValeZap;
   - Finaliza a sessão quando recebe `fim da interação`.
4. O backend externo também pode enviar mensagens assíncronas para `POST /webhook/vale` (obrigatório incluir `X-API-Key`).
5. O frontend formata balões no estilo WhatsApp, suporta *negrito*, _itálico_, ~tachado~ e trechos de código.

## Segurança implementada

- **Banco**: políticas RLS (`migrations/001_init.sql`) restringem leituras/inserções por `session_token`; a aplicação define `SET app.current_session_id` por requisição.
- **Webhook**: endpoint `/webhook/vale` exige API Key, normaliza player/sessão e rejeita payloads inválidos.
- **Frontend**: sanitização de texto, escaping HTML antes de aplicar a formatação, limite de comprimento e mensagens de erro discretas.
- **HTTP**: headers de segurança (CSP, X-Frame-Options, etc.) aplicados após cada resposta.

## Estrutura

```
app/
  __init__.py          # Factory Flask + blueprints
  api.py               # Endpoints REST (sessão e mensagens)
  config.py            # Configurações centralizadas
  database.py          # Engine SQLAlchemy + sessão com RLS
  external.py          # Cliente HTTP para o backend remoto
  models.py            # ORM (ChatSession, Message)
  routes.py            # Página principal (template)
  security.py          # Sanitização/validações extras
  webhook.py           # Endpoint para retorno assíncrono do backend
  templates/index.html # UI estilo WhatsApp
  static/
    css/style.css
    js/app.js
migrations/001_init.sql  # Script SQL com tabelas + RLS
requirements.txt
wsgi.py
Procfile
```

## Próximos passos sugeridos

- Adicionar testes automatizados (PyTest) simulando o fluxo de mensagens.
- Criar pipeline CI para linting (ruff/flake8) e execução das migrações.
- Publicar a aplicação em um serviço (Railway, Render, etc.) com Postgres gerenciado.




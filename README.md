# Automação AutoFlow

Plataforma completa de CRM + central de atendimento inteligente com automação via bot IA e WhatsApp.

---

## Producao

Para producao, mantenha `DEBUG=False` e configure uma `SECRET_KEY` forte no ambiente. Em `FLASK_ENV=production`, o app recusa `DEBUG=True` para evitar subir com modo de depuracao ativo. O arquivo `app.py` respeita `HOST` e `PORT` ao rodar localmente, mas o recomendado para deploy e usar Gunicorn:

```bash
gunicorn -w 3 -b 0.0.0.0:${PORT:-5000} wsgi:app
```

Variaveis importantes para deploy:

* `FLASK_ENV=production`
* `SECRET_KEY` com valor unico e secreto
* `DEBUG=False`
* `DATABASE_PATH` apontando para o SQLite persistente
* `REDIS_URL` ou `RATELIMIT_STORAGE_URI` para rate limit compartilhado
* `LOG_LEVEL=INFO`
* `SESSION_COOKIE_SECURE=True` quando estiver usando HTTPS
* `META_APP_SECRET`, `META_GRAPH_BASE_URL` e `META_GRAPH_VERSION` para webhooks Meta
* `MERCADO_PAGO_WEBHOOK_SECRET` e `MERCADO_PAGO_API_KEY` para validacao de pagamento

O Dockerfile ja inicia a aplicacao com Gunicorn:

```bash
docker-compose up --build
```

Gere uma `SECRET_KEY` forte antes de subir producao:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No Docker Compose, defina `SECRET_KEY` no ambiente ou no arquivo `.env`; o app nao inicia em producao com chave ausente ou curta.

O SQLite continua suportado nesta fase para manter compatibilidade. Para producao com maior volume, a evolucao recomendada e migrar para PostgreSQL, preservando os filtros por `empresa_id`, os indices de busca e as validacoes de ownership ja implementadas.

## 🚀 Funcionalidades implementadas

* ✅ Multiempresa real: isolamento completo por empresa
* ✅ Fluxos operacionais: editor visual e execução bloco a bloco
* ✅ Atendimento humano: assumir conversa, pausar bot e fila profissional
* ✅ Tags funcionais: criar, aplicar e filtrar em automação
* ✅ Logs e eventos: rastreamento detalhado de ações
* ✅ Agendamento inteligente: validação de conflitos e disponibilidade
* ✅ Regras avançadas: prioridade, múltiplas ações e condições complexas
* ✅ Integração com WhatsApp: envio e recebimento de mensagens

---

## ⚙️ Como executar o projeto

### 1. Clonar o repositório

```bash
git clone https://github.com/hilzenirs-ship-it/autoflow-saas.git
cd autoflow-saas
```

---

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

> ⚠️ Se o nome do arquivo no seu projeto for `requirements.txt`, use esse nome no comando.

---

### 3. Configurar ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Depois preencha com suas credenciais.

---

### 4. Inicializar banco de dados

```bash
python init_db.py
```

---

### 5. Rodar o projeto

```bash
python app.py
```

---

### 🐳 Rodar com Docker (opcional)

```bash
docker-compose up
```

---

## 🔐 Variáveis de ambiente

* `SECRET_KEY` → chave secreta do Flask
* `OPENAI_API_KEY` → chave da OpenAI
* `OPENAI_MODEL` → modelo da IA
* `DATABASE_PATH` → caminho do banco SQLite
* `REDIS_URL` → conexão Redis
* `RATELIMIT_STORAGE_URI` -> storage do rate limit
* `LOG_LEVEL` -> nivel dos logs (`INFO`, `WARNING`, `ERROR`)
* `HOST` -> host usado ao rodar `python app.py`
* `PORT` -> porta usada ao rodar `python app.py`
* `SESSION_COOKIE_SECURE` -> use `True` em producao com HTTPS
* `MERCADO_PAGO_WEBHOOK_SECRET` -> segredo usado para validar webhook Mercado Pago
* `MERCADO_PAGO_API_KEY` -> token usado para confirmar pagamentos na API Mercado Pago
* `MERCADO_PAGO_API_BASE_URL` -> URL base da API Mercado Pago
* `TWILIO_ACCOUNT_SID` → SID da conta Twilio
* `TWILIO_AUTH_TOKEN` → token Twilio
* `TWILIO_PHONE_NUMBER` → número do WhatsApp
* `DEBUG` → modo debug (True/False)

---

## 📲 Integração com WhatsApp

1. Configure sua conta no Twilio
2. Ative o WhatsApp Sandbox ou número oficial
3. Configure o webhook:

```
https://seudominio.com/api/webhook/whatsapp
```

4. Teste enviando mensagens

---

## 🧱 Estrutura do projeto

* `app.py` → aplicação principal
* `config.py` → configurações
* `utils/` → utilitários (db, cache, whatsapp, etc)
* `templates/` → HTMLs
* `tests/` → testes
* `init_db.py` → criação do banco
* `migrar.py` → migrações

---

## 🧠 Boas práticas

* Use ambiente virtual (`venv`)
* Nunca suba `.env` para o GitHub
* Nunca suba banco de dados (`.db`)
* Use `.gitignore` corretamente

---

## 📌 Status do projeto

🚧 Em evolução contínua para se tornar um SaaS completo de automação e atendimento inteligente.

---

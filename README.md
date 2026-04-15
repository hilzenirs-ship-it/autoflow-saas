# Automação AutoFlow

Plataforma completa de CRM + central de atendimento inteligente com automação via bot IA e WhatsApp.

---

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
pip install -r requisitos.txt
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

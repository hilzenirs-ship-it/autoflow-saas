# 🚀 AutoFlow SaaS - Deploy Guide

## Quick Start - Deploy em 5 minutos

### Opção 1: Docker Local (Recomendado para Teste) 🐳

**Pré-requisitos:**
- Docker Desktop instalado
- Git

**Passos:**

```bash
# 1. Clone o repositório
git clone https://github.com/hilzenirs-ship-it/autoflow-saas.git
cd autoflow-saas

# 2. Crie um arquivo .env com suas credenciais
cp .env.example .env

# 3. Edite .env com seus valores
nano .env  # ou use seu editor favorito

# 4. Execute o script de deploy
chmod +x deploy.sh
./deploy.sh docker

# 5. Acesse a aplicação
# http://localhost:5000
```

**Parar o deployment:**
```bash
docker-compose down
```

---

### Opção 2: Heroku (Grátis com dyno) 🌩️

**Pré-requisitos:**
- Heroku CLI instalado
- Conta Heroku
- Git

**Passos:**

```bash
# 1. Login no Heroku
heroku login

# 2. Clone o repositório
git clone https://github.com/hilzenirs-ship-it/autoflow-saas.git
cd autoflow-saas

# 3. Execute deploy automatizado
./deploy.sh heroku

# OU manualmente:

# 3a. Crie app
heroku create seu-app-name

# 3b. Adicione Redis
heroku addons:create heroku-redis:premium-0

# 3c. Configure variáveis
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set DATABASE_PATH=/app/database/hilflow.db
# ... outras variáveis

# 3d. Deploy
git push heroku main
```

**Monitorar:**
```bash
heroku logs -f
heroku ps
```

---

### Opção 3: Railway (Moderno & Fácil) 🚀

1. Visite https://railway.app
2. Conecte sua conta GitHub
3. Clique "Deploy from GitHub"
4. Selecione `hilzenirs-ship-it/autoflow-saas`
5. Configure variáveis de ambiente no painel
6. Railway faz deploy automático!

---

### Opção 4: AWS (Production-Ready) ☁️

**Com Elastic Beanstalk:**

```bash
# 1. Instale EB CLI
pip install awsebcli

# 2. Configure credenciais AWS
aws configure

# 3. Inicialize EB
eb init -p python-3.11 autoflow-saas --region us-east-1

# 4. Crie .ebextensions/01_flask.config
# (veja arquivo na seção abaixo)

# 5. Deploy
eb create autoflow-env
eb deploy
```

---

## 📋 Variáveis Obrigatórias

```env
# Flask
SECRET_KEY=seu-secret-key-muito-seguro-32-caracteres-minimo
FLASK_ENV=production
DEBUG=False

# Database
DATABASE_PATH=/app/database/hilflow.db

# Redis (OBRIGATÓRIO em production)
REDIS_URL=redis://redis:6379/0
RATELIMIT_STORAGE_URI=redis://redis:6379/0
CACHE_REDIS_URL=redis://redis:6379/0

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# OpenAI (opcional, só se OPENAI_REQUIRED=True)
OPENAI_API_KEY=sk-...
OPENAI_REQUIRED=False
OPENAI_MODEL=gpt-4o-mini

# Meta Webhooks (opcional)
META_APP_SECRET=seu-secret
META_WEBHOOKS_REQUIRED=False
META_GRAPH_BASE_URL=https://graph.facebook.com
META_GRAPH_VERSION=v19.0

# Mercado Pago (OBRIGATÓRIO em production por padrão)
MERCADO_PAGO_API_KEY=sua-chave-api
MERCADO_PAGO_WEBHOOK_SECRET=seu-webhook-secret
MERCADO_PAGO_REQUIRED=True
MERCADO_PAGO_API_BASE_URL=https://api.mercadopago.com
```

---

## 🔍 Health Check

Após deploy, verifique se está rodando:

```bash
curl http://seu-url/healthz

# Resposta esperada:
# {"status": "ok", "database": "ok", "redis": "ok"}
```

---

## 🆘 Troubleshooting

### Erro: `SECRET_KEY` inválida
```
ValueError: SECRET_KEY deve ser definida, segura (mínimo 32 caracteres)
```
**Solução:** Gere uma chave segura
```bash
openssl rand -hex 32
```

### Erro: Redis não conecta
```
ValueError: RATELIMIT_STORAGE_URI ou REDIS_URL deve ser configurado em producao
```
**Solução:** Certifique-se que Redis está rodando e acessível

### Erro: Banco de dados não inicializado
```bash
python init_db.py
```

### Ver logs
```bash
# Docker
docker-compose logs -f app

# Heroku
heroku logs -f

# Railway
Painel → Logs
```

---

## 📊 Monitoramento

### Docker
```bash
docker stats  # Ver uso de CPU/RAM
docker-compose ps  # Ver status dos containers
```

### Heroku
```bash
heroku addons:open papertrail  # Ver logs em tempo real
heroku pg:info  # Info do banco (se usando PostgreSQL)
```

### Saúde da Aplicação
```bash
curl -i https://seu-url/healthz
```

---

## 🔐 Segurança

**Checklist:**
- [ ] DEBUG=False em produção
- [ ] SECRET_KEY muito segura (32+ caracteres)
- [ ] HTTPS ativado (Heroku/Railway auto)
- [ ] SESSION_COOKIE_SECURE=True
- [ ] Credenciais em `.env`, NUNCA em código
- [ ] Fazer backup do banco SQLite regularmente

---

## 📈 Escalamento

Para maior volume, considere:
1. Migrar SQLite → PostgreSQL
2. Usar CDN para assets estáticos (CloudFront/Cloudflare)
3. Implementar caching mais agressivo
4. Usar Gunicorn com mais workers: `-w 10`

---

## 🤝 Suporte

- 📖 README: [README.md](README.md)
- 🤝 Contribuir: [CONTRIBUTING.md](CONTRIBUTING.md)
- 🐛 Issues: https://github.com/hilzenirs-ship-it/autoflow-saas/issues
- 💬 Discussões: https://github.com/hilzenirs-ship-it/autoflow-saas/discussions

---

**Feito com ❤️ por Hilzenirs**

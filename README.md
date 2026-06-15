# 💜 AutoFlow SaaS

**Intelligent Customer Service Management Platform**

AutoFlow is a comprehensive SaaS platform built with Flask that streamlines customer service operations through intelligent automation, workflow management, and multi-channel integration.

---

## ✨ Core Features

### 📞 Multi-Channel Communication
- **WhatsApp Integration** - Direct messaging via Meta's Graph API
- **Instagram Direct Messages** - Reach customers on Instagram
- **Conversation Management** - Unified inbox for all channels
- **Message History** - Complete conversation tracking

### 🤖 Intelligent Automation
- **AI-Powered Responses** - OpenAI integration for smart replies
- **Workflow Automation** - Create custom business flows
- **Rule Engine** - Keyword-triggered automated responses
- **Context Awareness** - Maintain conversation history and context

### 📅 Scheduling & CRM
- **Appointment Booking** - Integrated scheduling system
- **Contact Management** - Detailed client profiles and history
- **Service Catalog** - Manage services and pricing
- **Status Tracking** - Monitor service delivery and follow-ups

### 💳 Business Features
- **Multi-Tenant Architecture** - Support multiple companies
- **Plan Limits** - Configurable usage limits per plan
- **Payment Integration** - Mercado Pago integration for billing
- **Rate Limiting** - Protect API with intelligent rate limiting
- **Error Logging** - Comprehensive error tracking and diagnostics

### 🔒 Enterprise Security
- **CSRF Protection** - Built-in CSRF protection
- **Secure Sessions** - HttpOnly, Secure, SameSite cookies
- **Input Validation** - Data normalization and sanitization
- **Environment-Based Config** - Secure configuration management
- **Webhook Verification** - HMAC signature validation

---

## 🛠️ Technology Stack

**Backend**
- **Framework**: Flask with blueprints architecture
- **Database**: SQLite (development) → PostgreSQL (production-ready)
- **Caching**: Redis with Flask-Caching
- **Rate Limiting**: Flask-Limiter with Redis backend
- **Security**: Flask-WTF (CSRF), bcrypt hashing

**Integrations**
- **AI**: OpenAI API (GPT-4o-mini)
- **Messaging**: Meta Graph API (WhatsApp, Instagram)
- **Payments**: Mercado Pago
- **Webhooks**: HMAC-256 signature verification

**DevOps**
- **Containerization**: Docker with Gunicorn
- **Health Checks**: Built-in healthz endpoint
- **Logging**: Structured logging with correlation IDs
- **Environment**: 12-factor app compliant

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Redis (for production rate limiting & caching)
- pip package manager

### Local Development

```bash
# Clone repository
git clone https://github.com/hilzenirs-ship-it/autoflow-saas.git
cd autoflow-saas

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run development server
python app.py
```

Access the application at `http://localhost:5000`

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access at http://localhost:5000
```

---

## 📋 Environment Configuration

### Required Variables (Production)

```bash
# Flask Configuration
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-strong-random-key-32-chars-minimum

# Database
DATABASE_PATH=/data/autoflow.db

# Redis (Required for production rate limiting)
REDIS_URL=redis://redis:6379/0
RATELIMIT_STORAGE_URI=redis://redis:6379/0
CACHE_REDIS_URL=redis://redis:6379/0

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# AI Integration (Optional)
OPENAI_API_KEY=sk-...
OPENAI_REQUIRED=False
OPENAI_MODEL=gpt-4o-mini

# Meta Webhooks (WhatsApp/Instagram)
META_APP_SECRET=your-meta-secret
META_WEBHOOKS_REQUIRED=True
META_GRAPH_BASE_URL=https://graph.instagram.com
META_GRAPH_VERSION=v18.0

# Mercado Pago
MERCADO_PAGO_API_KEY=your-mercado-pago-key
MERCADO_PAGO_WEBHOOK_SECRET=your-mercado-pago-webhook-secret
MERCADO_PAGO_REQUIRED=True

# Seeding (Optional - initial admin)
SEED_ADMIN_EMAIL=admin@yourdomain.com
SEED_ADMIN_PASSWORD=strong-password-12-chars-min
SEED_COMPANY_NAME=Your Company Name
```

---

## 📁 Project Structure

```
autoflow-saas/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── wsgi.py                # WSGI entry point (Gunicorn)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Multi-container setup
│
├── routes/                # Blueprint routes
│   ├── auth.py           # Authentication
│   ├── webhooks.py       # Webhook handlers
│   ├── agendamentos.py   # Appointments
│   ├── conversas.py      # Conversations
│   ├── contatos.py       # Contact management
│   ├── fluxos.py         # Workflow automation
│   ├── regras.py         # Rule engine
│   └── ...
│
├── services/              # Business logic
│   ├── auth_service.py
│   ├── conversas_service.py
│   ├── saas_limits_service.py
│   ├── dashboard_service.py
│   └── ...
│
├── utils/                 # Utilities
│   ├── db.py             # Database connection
│   ├── limiter.py        # Rate limiting setup
│   ├── cache.py          # Caching setup
│   ├── normalizer.py     # Data normalization
│   └── auth.py           # Authentication utilities
│
├── database/
│   └── schema.sql        # Initial database schema
│
├── templates/            # Jinja2 templates
├── static/              # CSS, JS, assets
├── tests/               # Test suite
└── migrations/          # Database migrations
```

---

## 🔌 API Endpoints

### Health Check
```
GET /healthz
```
Returns basic application and database health status.

### Webhooks

**WhatsApp**
```
POST /webhooks/whatsapp/<token>
```

**Instagram**
```
POST /webhooks/instagram/<token>
```

**Mercado Pago**
```
POST /webhooks/mercadopago
```

All webhooks validate HMAC-256 signatures when configured.

---

## 💾 Database Management

### Initialize Database
```bash
python init_db.py
```

### Backup SQLite
```bash
python backup_sqlite.py --backup-dir backups
```

### Run Migrations
```bash
python migrar.py
```

### Upgrade to PostgreSQL (Production)
The schema is designed to migrate to PostgreSQL for production:

```bash
# The app includes tenant isolation (empresa_id) for multi-tenancy
# Indices are optimized for concurrent access
# Foreign keys enforce data integrity
```

---

## 🧪 Testing

```bash
# Run test suite
python -m pytest

# Run specific test file
python -m pytest tests/test_auth.py

# Run with coverage
python -m pytest --cov=.
```

---

## 🔐 Security Features

✅ **CSRF Protection** - All forms protected with tokens  
✅ **Rate Limiting** - Redis-backed distributed rate limiting  
✅ **Secure Cookies** - HttpOnly, Secure, SameSite flags  
✅ **Password Hashing** - bcrypt with salt  
✅ **Webhook Verification** - HMAC-256 signature validation  
✅ **Input Validation** - All inputs normalized and sanitized  
✅ **Environment Isolation** - Production requires explicit configuration  
✅ **Tenant Isolation** - Multi-tenant with empresa_id filtering  
✅ **Error Logging** - Centralized error tracking with correlation IDs

---

## 📊 Performance & Scaling

- **Caching Layer**: Redis cache for frequently accessed data
- **Database Indices**: Optimized queries with strategic indices
- **Connection Pooling**: SQLite connection management (PostgreSQL recommended for production)
- **Rate Limiting**: Distributed rate limiting via Redis
- **Async Webhooks**: Non-blocking webhook processing
- **Gunicorn**: Multi-worker WSGI server (3 workers default)

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production` and `DEBUG=False`
- [ ] Generate strong `SECRET_KEY` (32+ chars)
- [ ] Configure `DATABASE_PATH` to persistent storage
- [ ] Set up Redis for rate limiting and caching
- [ ] Configure HTTPS with `SESSION_COOKIE_SECURE=True`
- [ ] Set up webhook secrets for Meta and Mercado Pago
- [ ] Configure OPENAI_API_KEY if using AI features
- [ ] Set up automated backups for SQLite or migrate to PostgreSQL
- [ ] Configure error logging and monitoring
- [ ] Set up SSL/TLS certificates

### Cloud Deployment Examples

**Heroku**
```bash
heroku create your-app-name
heroku config:set FLASK_ENV=production SECRET_KEY=your-secret
heroku addons:create heroku-redis
git push heroku main
```

**AWS/DigitalOcean/Linode**
```bash
# Use Docker container with Gunicorn
docker build -t autoflow-saas .
docker run -p 5000:5000 autoflow-saas
```

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📈 Roadmap

- [ ] GraphQL API
- [ ] Real-time notifications (WebSockets)
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] AI conversation training
- [ ] Custom integrations marketplace
- [ ] Multi-language support
- [ ] Video call integration

---

## 📞 Support

- 📧 Email: support@autoflow.com
- 🐛 Issues: [GitHub Issues](https://github.com/hilzenirs-ship-it/autoflow-saas/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/hilzenirs-ship-it/autoflow-saas/discussions)

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 👨‍💻 Author

**Hilzenirs**  
- GitHub: [@hilzenirs-ship-it](https://github.com/hilzenirs-ship-it)
- Portfolio: [Your Website]

---

**AutoFlow SaaS** - Built with ❤️ for modern customer service teams

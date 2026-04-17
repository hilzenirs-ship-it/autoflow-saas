import os
import secrets

class Config:
    ENV = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "production")).strip().lower()
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    if ENV in {"development", "testing"}:
        SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    else:
        SECRET_KEY = os.environ.get("SECRET_KEY")
        if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY == "hilflow-connect-dev-secret":
            raise ValueError("SECRET_KEY deve ser definida, segura (mínimo 32 caracteres) e não fraca em produção")
        if DEBUG:
            raise ValueError("DEBUG=True nao e permitido em producao")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "database/hilflow.db")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_STORAGE_URI = (
        os.environ.get("RATELIMIT_STORAGE_URI")
        or os.environ.get("REDIS_URL")
        or "memory://"
    )
    _SESSION_COOKIE_SECURE_DEFAULT = "True" if ENV == "production" else "False"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", _SESSION_COOKIE_SECURE_DEFAULT).lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "").strip()
    MERCADO_PAGO_WEBHOOK_SECRET = os.environ.get("MERCADO_PAGO_WEBHOOK_SECRET", "").strip()
    MERCADO_PAGO_API_BASE_URL = os.environ.get("MERCADO_PAGO_API_BASE_URL", "https://api.mercadopago.com").strip()
    MERCADO_PAGO_API_KEY = os.environ.get("MERCADO_PAGO_API_KEY", "").strip()

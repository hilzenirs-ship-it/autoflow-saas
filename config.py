import os
import secrets

class Config:
    ENV = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "production")).strip().lower()
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    _SECRET_KEYS_FRACAS = {
        "hilflow-connect-dev-secret",
        "replace-with-a-random-secret-key-with-at-least-32-characters",
        "change-me",
        "changeme",
    }
    if ENV in {"development", "testing"}:
        SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    else:
        SECRET_KEY = (os.environ.get("SECRET_KEY") or "").strip()
        if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY.lower() in _SECRET_KEYS_FRACAS:
            raise ValueError("SECRET_KEY deve ser definida, segura (mínimo 32 caracteres) e não fraca em produção")
        if DEBUG:
            raise ValueError("DEBUG=True nao e permitido em producao")
    _OPENAI_API_KEYS_PLACEHOLDER = {
        "your-openai-api-key-here",
        "your-openai-key",
        "replace-with-your-openai-api-key",
    }
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
    if OPENAI_API_KEY.lower() in _OPENAI_API_KEYS_PLACEHOLDER:
        OPENAI_API_KEY = ""
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "database/hilflow.db")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    REDIS_URL = os.environ.get("REDIS_URL", "").strip()
    RATELIMIT_STORAGE_URI = (
        os.environ.get("RATELIMIT_STORAGE_URI", "").strip()
        or REDIS_URL
    )
    if ENV in {"development", "testing"} and not RATELIMIT_STORAGE_URI:
        RATELIMIT_STORAGE_URI = "memory://"
    if ENV == "production" and (not RATELIMIT_STORAGE_URI or RATELIMIT_STORAGE_URI == "memory://"):
        raise ValueError("RATELIMIT_STORAGE_URI ou REDIS_URL deve ser configurado em producao")
    _CACHE_REDIS_FALLBACK = RATELIMIT_STORAGE_URI if RATELIMIT_STORAGE_URI.startswith(("redis://", "rediss://", "unix://")) else ""
    CACHE_REDIS_URL = (
        os.environ.get("CACHE_REDIS_URL", "").strip()
        or REDIS_URL
        or _CACHE_REDIS_FALLBACK
    )
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "").strip()
    if not CACHE_TYPE:
        if ENV in {"development", "testing"} and not CACHE_REDIS_URL:
            CACHE_TYPE = "flask_caching.backends.simplecache.SimpleCache"
        else:
            CACHE_TYPE = "flask_caching.backends.rediscache.RedisCache"
    if ENV == "production" and CACHE_TYPE.endswith("SimpleCache"):
        raise ValueError("CACHE_TYPE SimpleCache nao e permitido em producao")
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

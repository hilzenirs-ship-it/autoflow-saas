import os
import secrets


INTEGRATION_PLACEHOLDERS = {
    "change-me",
    "changeme",
    "your-meta-app-secret",
    "replace-with-your-meta-app-secret",
    "your-mercado-pago-webhook-secret",
    "replace-with-your-mercado-pago-webhook-secret",
    "your-mercado-pago-api-key",
    "replace-with-your-mercado-pago-api-key",
}


def env_sem_placeholder(nome, padrao=""):
    valor = os.environ.get(nome, padrao)
    valor = (valor or "").strip()
    if valor.lower() in INTEGRATION_PLACEHOLDERS:
        return ""
    return valor


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
    _DATABASE_PATH_ENV = os.environ.get("DATABASE_PATH", "").strip()
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
    if OPENAI_API_KEY.lower() in _OPENAI_API_KEYS_PLACEHOLDER:
        OPENAI_API_KEY = ""
    OPENAI_REQUIRED = os.environ.get("OPENAI_REQUIRED", "False").lower() == "true"
    if OPENAI_REQUIRED and not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY deve ser configurada quando OPENAI_REQUIRED=True")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    if ENV == "production" and not _DATABASE_PATH_ENV:
        raise ValueError("DATABASE_PATH deve ser configurado explicitamente em producao")
    DATABASE_PATH = _DATABASE_PATH_ENV or "database/hilflow.db"
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "False").lower() == "true"
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
    META_APP_SECRET = env_sem_placeholder("META_APP_SECRET")
    META_GRAPH_BASE_URL = env_sem_placeholder("META_GRAPH_BASE_URL", "https://graph.facebook.com")
    META_GRAPH_VERSION = env_sem_placeholder("META_GRAPH_VERSION", "v19.0")
    META_WEBHOOKS_REQUIRED = os.environ.get("META_WEBHOOKS_REQUIRED", "False").lower() == "true"
    if META_WEBHOOKS_REQUIRED and not META_APP_SECRET:
        raise ValueError("META_APP_SECRET deve ser configurado quando META_WEBHOOKS_REQUIRED=True")
    MERCADO_PAGO_WEBHOOK_SECRET = env_sem_placeholder("MERCADO_PAGO_WEBHOOK_SECRET")
    MERCADO_PAGO_API_BASE_URL = env_sem_placeholder("MERCADO_PAGO_API_BASE_URL", "https://api.mercadopago.com")
    MERCADO_PAGO_API_KEY = env_sem_placeholder("MERCADO_PAGO_API_KEY")
    MERCADO_PAGO_REQUIRED = os.environ.get(
        "MERCADO_PAGO_REQUIRED",
        "True" if ENV == "production" else "False"
    ).lower() == "true"
    if MERCADO_PAGO_REQUIRED and (not MERCADO_PAGO_WEBHOOK_SECRET or not MERCADO_PAGO_API_KEY):
        raise ValueError("MERCADO_PAGO_WEBHOOK_SECRET e MERCADO_PAGO_API_KEY devem ser configurados")

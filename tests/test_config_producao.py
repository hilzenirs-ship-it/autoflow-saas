import importlib
import sys

import pytest


def carregar_config(monkeypatch, **env):
    for chave in [
        "FLASK_ENV",
        "APP_ENV",
        "SECRET_KEY",
        "DEBUG",
        "OPENAI_API_KEY",
        "OPENAI_REQUIRED",
        "DATABASE_PATH",
        "TRUST_PROXY_HEADERS",
        "META_APP_SECRET",
        "META_WEBHOOKS_REQUIRED",
        "META_GRAPH_BASE_URL",
        "META_GRAPH_VERSION",
        "MERCADO_PAGO_WEBHOOK_SECRET",
        "MERCADO_PAGO_API_KEY",
        "MERCADO_PAGO_REQUIRED",
        "MERCADO_PAGO_API_BASE_URL",
        "SESSION_COOKIE_SECURE",
        "REDIS_URL",
        "RATELIMIT_STORAGE_URI",
        "CACHE_TYPE",
        "CACHE_REDIS_URL",
    ]:
        monkeypatch.delenv(chave, raising=False)
    for chave, valor in env.items():
        monkeypatch.setenv(chave, valor)
    sys.modules.pop("config", None)
    return importlib.import_module("config")


def test_producao_rejeita_debug_true(monkeypatch):
    with pytest.raises(ValueError, match="DEBUG=True"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="True",
            DATABASE_PATH="database/prod.db",
            REDIS_URL="redis://localhost:6379/0",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
        )


def test_producao_rejeita_secret_key_placeholder(monkeypatch):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="replace-with-a-random-secret-key-with-at-least-32-characters",
            DEBUG="False",
            DATABASE_PATH="database/prod.db",
            REDIS_URL="redis://localhost:6379/0",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
        )


def test_producao_exige_database_path(monkeypatch):
    with pytest.raises(ValueError, match="DATABASE_PATH"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            REDIS_URL="redis://localhost:6379/0",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
        )


def test_producao_cookie_secure_padrao_true(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="production",
        SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
        DEBUG="False",
        DATABASE_PATH="database/prod.db",
        REDIS_URL="redis://localhost:6379/0",
        MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
        MERCADO_PAGO_API_KEY="mp-api-key-forte",
    )

    assert config_module.Config.DEBUG is False
    assert config_module.Config.SESSION_COOKIE_SECURE is True
    assert config_module.Config.CACHE_TYPE == "flask_caching.backends.rediscache.RedisCache"
    assert config_module.Config.CACHE_REDIS_URL == "redis://localhost:6379/0"


def test_openai_api_key_placeholder_e_tratado_como_ausente(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="production",
        SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
        DEBUG="False",
        DATABASE_PATH="database/prod.db",
        REDIS_URL="redis://localhost:6379/0",
        MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
        MERCADO_PAGO_API_KEY="mp-api-key-forte",
        OPENAI_API_KEY="your-openai-api-key-here",
    )

    assert config_module.Config.OPENAI_API_KEY == ""


def test_placeholders_de_integracoes_sao_tratados_como_ausentes(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="production",
        SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
        DEBUG="False",
        DATABASE_PATH="database/prod.db",
        REDIS_URL="redis://localhost:6379/0",
        META_APP_SECRET="your-meta-app-secret",
        MERCADO_PAGO_WEBHOOK_SECRET="your-mercado-pago-webhook-secret",
        MERCADO_PAGO_API_KEY="your-mercado-pago-api-key",
        MERCADO_PAGO_REQUIRED="False",
    )

    assert config_module.Config.META_APP_SECRET == ""
    assert config_module.Config.MERCADO_PAGO_WEBHOOK_SECRET == ""
    assert config_module.Config.MERCADO_PAGO_API_KEY == ""


def test_producao_exige_mercado_pago_quando_required(monkeypatch):
    with pytest.raises(ValueError, match="MERCADO_PAGO"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            DATABASE_PATH="database/prod.db",
            REDIS_URL="redis://localhost:6379/0",
            MERCADO_PAGO_REQUIRED="True",
        )


def test_mercado_pago_pode_ser_desabilitado_explicitamente(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="production",
        SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
        DEBUG="False",
        DATABASE_PATH="database/prod.db",
        REDIS_URL="redis://localhost:6379/0",
        MERCADO_PAGO_REQUIRED="False",
    )

    assert config_module.Config.MERCADO_PAGO_REQUIRED is False


def test_openai_required_exige_chave(monkeypatch):
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="testing",
            OPENAI_REQUIRED="True",
            OPENAI_API_KEY="your-openai-api-key-here",
        )


def test_meta_webhooks_required_exige_secret(monkeypatch):
    with pytest.raises(ValueError, match="META_APP_SECRET"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="testing",
            META_WEBHOOKS_REQUIRED="True",
            META_APP_SECRET="your-meta-app-secret",
        )


def test_meta_graph_defaults_configurados(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="testing",
    )

    assert config_module.Config.META_GRAPH_BASE_URL == "https://graph.facebook.com"
    assert config_module.Config.META_GRAPH_VERSION == "v19.0"


def test_producao_exige_rate_limit_storage_compartilhado(monkeypatch):
    with pytest.raises(ValueError, match="RATELIMIT_STORAGE_URI"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            DATABASE_PATH="database/prod.db",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
        )

    with pytest.raises(ValueError, match="RATELIMIT_STORAGE_URI"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            DATABASE_PATH="database/prod.db",
            RATELIMIT_STORAGE_URI="memory://",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
        )


def test_testing_permite_debug_sem_enfraquecer_producao(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="testing",
        DEBUG="True",
    )

    assert config_module.Config.DEBUG is True
    assert config_module.Config.SESSION_COOKIE_SECURE is False
    assert config_module.Config.CACHE_TYPE == "flask_caching.backends.simplecache.SimpleCache"


def test_proxy_headers_desativado_por_padrao(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="testing",
    )

    assert config_module.Config.TRUST_PROXY_HEADERS is False


def test_proxy_headers_pode_ser_habilitado(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="testing",
        TRUST_PROXY_HEADERS="True",
    )

    assert config_module.Config.TRUST_PROXY_HEADERS is True


def test_producao_rejeita_cache_local(monkeypatch):
    with pytest.raises(ValueError, match="CACHE_TYPE SimpleCache"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            DATABASE_PATH="database/prod.db",
            REDIS_URL="redis://localhost:6379/0",
            MERCADO_PAGO_WEBHOOK_SECRET="mp-webhook-secret-forte",
            MERCADO_PAGO_API_KEY="mp-api-key-forte",
            CACHE_TYPE="flask_caching.backends.simplecache.SimpleCache",
        )

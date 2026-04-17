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
        "TRUST_PROXY_HEADERS",
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
        )


def test_producao_rejeita_secret_key_placeholder(monkeypatch):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="replace-with-a-random-secret-key-with-at-least-32-characters",
            DEBUG="False",
            REDIS_URL="redis://localhost:6379/0",
        )


def test_producao_cookie_secure_padrao_true(monkeypatch):
    config_module = carregar_config(
        monkeypatch,
        FLASK_ENV="production",
        SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
        DEBUG="False",
        REDIS_URL="redis://localhost:6379/0",
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
        REDIS_URL="redis://localhost:6379/0",
        OPENAI_API_KEY="your-openai-api-key-here",
    )

    assert config_module.Config.OPENAI_API_KEY == ""


def test_producao_exige_rate_limit_storage_compartilhado(monkeypatch):
    with pytest.raises(ValueError, match="RATELIMIT_STORAGE_URI"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
        )

    with pytest.raises(ValueError, match="RATELIMIT_STORAGE_URI"):
        carregar_config(
            monkeypatch,
            FLASK_ENV="production",
            SECRET_KEY="segredo-forte-com-mais-de-32-caracteres",
            DEBUG="False",
            RATELIMIT_STORAGE_URI="memory://",
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
            REDIS_URL="redis://localhost:6379/0",
            CACHE_TYPE="flask_caching.backends.simplecache.SimpleCache",
        )

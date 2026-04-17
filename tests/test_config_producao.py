import importlib
import sys

import pytest


def carregar_config(monkeypatch, **env):
    for chave in [
        "FLASK_ENV",
        "APP_ENV",
        "SECRET_KEY",
        "DEBUG",
        "SESSION_COOKIE_SECURE",
        "REDIS_URL",
        "RATELIMIT_STORAGE_URI",
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

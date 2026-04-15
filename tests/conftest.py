import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def app_module():
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "test.db"
    if db_path.exists():
        db_path.unlink()

    import utils.db as db

    db.DB_PATH = db_path
    conn = db.get_connection()
    schema_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        CACHE_TYPE="SimpleCache",
    )
    return module


@pytest.fixture()
def flask_app(app_module):
    return app_module.app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture()
def db_conn(app_module):
    conn = app_module.get_connection()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def seed_base(app_module):
    def _seed(prefix="empresa"):
        conn = app_module.get_connection()
        cursor = conn.execute(
            "INSERT INTO users (nome, email, senha_hash) VALUES (?, ?, ?)",
            (f"User {prefix}", f"{prefix}@teste.com", app_module.gerar_hash_senha("senha123")),
        )
        user_id = cursor.lastrowid
        cursor = conn.execute(
            "INSERT INTO empresas (user_id, nome_empresa, nome_exibicao, email) VALUES (?, ?, ?, ?)",
            (user_id, f"Empresa {prefix}", f"Empresa {prefix}", f"{prefix}@teste.com"),
        )
        empresa_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo) VALUES (?, ?, 'owner', 1)",
            (empresa_id, user_id),
        )
        cursor = conn.execute(
            "INSERT INTO contatos (empresa_id, nome, telefone) VALUES (?, ?, ?)",
            (empresa_id, f"Contato {prefix}", f"550000{empresa_id}"),
        )
        contato_id = cursor.lastrowid
        cursor = conn.execute(
            "INSERT INTO conversas (empresa_id, contato_id, status, bot_ativo) VALUES (?, ?, 'aberta', 1)",
            (empresa_id, contato_id),
        )
        conversa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "user_id": user_id,
            "empresa_id": empresa_id,
            "contato_id": contato_id,
            "conversa_id": conversa_id,
            "email": f"{prefix}@teste.com",
        }

    return _seed


def login_session(client, user_id, empresa_id, nome="Teste", email="teste@local"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_nome"] = nome
        sess["user_email"] = email
        sess["empresa_id"] = empresa_id
        sess["empresa_nome"] = f"Empresa {empresa_id}"

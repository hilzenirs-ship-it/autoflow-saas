import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

from utils.db import DB_PATH


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def _senha_seed_segura(senha):
    senha = (senha or "").strip()
    fracas = {"123456", "12345678", "password", "senha", "admin", "admin123"}
    return len(senha) >= 12 and senha.lower() not in fracas


def criar_seed_admin_opcional(conn):
    email = (os.environ.get("SEED_ADMIN_EMAIL") or "").strip().lower()
    senha = (os.environ.get("SEED_ADMIN_PASSWORD") or "").strip()
    nome = (os.environ.get("SEED_ADMIN_NAME") or "Admin").strip()
    empresa_nome = (os.environ.get("SEED_COMPANY_NAME") or "").strip()

    if not email and not senha and not empresa_nome:
        print("Seed admin nao configurado. Banco criado apenas com schema.")
        return

    if not email or not senha or not empresa_nome:
        raise ValueError("Para criar seed admin, defina SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD e SEED_COMPANY_NAME.")

    if not _senha_seed_segura(senha):
        raise ValueError("SEED_ADMIN_PASSWORD deve ter pelo menos 12 caracteres e nao pode ser uma senha fraca.")

    conn.execute(
        """
        INSERT OR IGNORE INTO users (nome, email, senha_hash)
        VALUES (?, ?, ?)
        """,
        (nome, email, generate_password_hash(senha)),
    )

    user = conn.execute(
        "SELECT id FROM users WHERE lower(email) = ? LIMIT 1",
        (email,),
    ).fetchone()
    if not user:
        raise RuntimeError("Nao foi possivel criar ou localizar o usuario seed.")

    conn.execute(
        """
        INSERT OR IGNORE INTO empresas (user_id, nome_empresa, nome_exibicao, email)
        VALUES (?, ?, ?, ?)
        """,
        (user["id"], empresa_nome, empresa_nome, email),
    )

    empresa = conn.execute(
        """
        SELECT id
        FROM empresas
        WHERE user_id = ? AND nome_empresa = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (user["id"], empresa_nome),
    ).fetchone()
    if not empresa:
        raise RuntimeError("Nao foi possivel criar ou localizar a empresa seed.")

    conn.execute(
        """
        INSERT OR IGNORE INTO empresa_membros (empresa_id, user_id, papel, ativo)
        VALUES (?, ?, 'owner', 1)
        """,
        (empresa["id"], user["id"]),
    )
    print(f"Seed admin criado/confirmado para: {email}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    criar_seed_admin_opcional(conn)

    conn.commit()
    conn.close()

    print(f"Banco criado com sucesso em: {DB_PATH}")


if __name__ == "__main__":
    init_db()

import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "banco.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # cria usuário padrão
    conn.execute(
        """
        INSERT OR IGNORE INTO users (id, nome, email, senha_hash)
        VALUES (?, ?, ?, ?)
        """,
        (1, "Admin", "admin@hilflow.com", generate_password_hash("123456"))
    )

    # cria empresa padrão
    conn.execute(
        """
        INSERT OR IGNORE INTO empresas (id, user_id, nome_empresa, nome_exibicao, email, telefone)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "HilFlow Connect",
            "HilFlow Connect",
            "admin@hilflow.com",
            "(16) 99999-9999"
        )
    )

    conn.commit()
    conn.close()

    print(f"Banco criado com sucesso em: {DB_PATH}")

if __name__ == "__main__":
    init_db()

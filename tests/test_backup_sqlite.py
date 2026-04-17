import sqlite3
import uuid
from pathlib import Path

from backup_sqlite import criar_backup_sqlite


def test_criar_backup_sqlite_preserva_banco_original():
    base_dir = Path(__file__).resolve().parent / ".tmp" / f"backup_{uuid.uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=True)
    origem = base_dir / "origem.db"
    backup_dir = base_dir / "backups"

    conn = sqlite3.connect(origem)
    conn.execute("CREATE TABLE exemplo (id INTEGER PRIMARY KEY, nome TEXT NOT NULL)")
    conn.execute("INSERT INTO exemplo (nome) VALUES (?)", ("AutoFlow",))
    conn.commit()
    conn.close()

    destino = criar_backup_sqlite(origem, backup_dir)

    assert destino.exists()
    assert destino.parent == backup_dir
    assert origem.exists()

    origem_conn = sqlite3.connect(origem)
    backup_conn = sqlite3.connect(destino)
    try:
        origem_total = origem_conn.execute("SELECT COUNT(*) FROM exemplo").fetchone()[0]
        backup_total = backup_conn.execute("SELECT COUNT(*) FROM exemplo").fetchone()[0]
        backup_nome = backup_conn.execute("SELECT nome FROM exemplo").fetchone()[0]
    finally:
        origem_conn.close()
        backup_conn.close()

    assert origem_total == 1
    assert backup_total == 1
    assert backup_nome == "AutoFlow"

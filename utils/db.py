import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_path_from_config():
    if not os.environ.get("DATABASE_PATH"):
        return BASE_DIR / "banco.db"

    try:
        from config import Config
        configured_path = Config.DATABASE_PATH
    except Exception:
        configured_path = os.environ.get("DATABASE_PATH")

    db_path = Path(configured_path)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    return db_path


DB_PATH = _database_path_from_config()

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

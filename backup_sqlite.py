import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from utils.db import DB_PATH, BASE_DIR


def resolver_diretorio_backup(valor=None):
    destino = Path(valor or "backups")
    if not destino.is_absolute():
        destino = BASE_DIR / destino
    return destino


def criar_backup_sqlite(origem=None, diretorio_backup=None):
    origem = Path(origem or DB_PATH)
    diretorio_backup = resolver_diretorio_backup(diretorio_backup)

    if not origem.exists():
        raise FileNotFoundError(f"Banco SQLite nao encontrado: {origem}")

    diretorio_backup.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = diretorio_backup / f"{origem.stem}_{timestamp}.db"

    origem_conn = sqlite3.connect(origem)
    try:
        destino_conn = sqlite3.connect(destino)
        try:
            origem_conn.backup(destino_conn)
        finally:
            destino_conn.close()
    finally:
        origem_conn.close()

    return destino


def main():
    parser = argparse.ArgumentParser(description="Cria backup consistente do banco SQLite do AutoFlow.")
    parser.add_argument("--database", default=str(DB_PATH), help="Caminho do banco SQLite de origem.")
    parser.add_argument("--backup-dir", default=None, help="Diretorio de destino. Padrao: ./backups")
    args = parser.parse_args()

    destino = criar_backup_sqlite(args.database, args.backup_dir)
    print(f"Backup criado em: {destino}")


if __name__ == "__main__":
    main()

from utils.db import get_connection

conn = get_connection()

try:
    conn.execute("ALTER TABLE conversas ADD COLUMN etapa TEXT")
    print("Coluna etapa criada 💜")
except Exception as e:
    print("Etapa:", e)

try:
    conn.execute("ALTER TABLE conversas ADD COLUMN contexto_json TEXT")
    print("Coluna contexto_json criada 💜")
except Exception as e:
    print("Contexto:", e)

try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            contato_id INTEGER NOT NULL,
            conversa_id INTEGER,
            servico TEXT,
            data TEXT,
            horario TEXT,
            status TEXT DEFAULT 'confirmado',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE,
            FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE SET NULL
        )
    """)
    print("Tabela agendamentos criada 💜")
except Exception as e:
    print("Agendamentos:", e)

conn.commit()
conn.close()
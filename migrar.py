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

# Novas migrações para hardening de produção
try:
    conn.execute("ALTER TABLE empresa_limites ADD COLUMN status_ciclo_vida TEXT DEFAULT 'trial'")
    print("Coluna status_ciclo_vida criada 💜")
except Exception as e:
    print("Status ciclo vida:", e)

try:
    conn.execute("ALTER TABLE empresa_limites ADD COLUMN payment_id_externo TEXT")
    print("Coluna payment_id_externo criada 💜")
except Exception as e:
    print("Payment ID externo:", e)

try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correlation_id TEXT,
            empresa_id INTEGER,
            user_id INTEGER,
            endpoint TEXT,
            method TEXT,
            error_type TEXT,
            error_message TEXT,
            stack_trace TEXT,
            request_data TEXT,
            user_agent TEXT,
            ip_address TEXT,
            severity TEXT DEFAULT 'error',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    print("Tabela error_logs criada 💜")
except Exception as e:
    print("Error logs:", e)

try:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_correlation_id ON error_logs(correlation_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_empresa_id ON error_logs(empresa_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_criado_em ON error_logs(criado_em)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity)")
    print("Índices error_logs criados 💜")
except Exception as e:
    print("Índices error_logs:", e)

conn.commit()
conn.close()
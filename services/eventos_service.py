from utils.auth import obter_empresa_id_logada
from utils.db import get_connection


def registrar_evento(tipo_evento, referencia_id=None, valor=None, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id or not tipo_evento:
        return

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO metricas_eventos (
            empresa_id,
            tipo_evento,
            referencia_id,
            valor
        )
        VALUES (?, ?, ?, ?)
        """,
        (empresa_id, str(tipo_evento).strip(), referencia_id, valor)
    )
    conn.commit()
    conn.close()

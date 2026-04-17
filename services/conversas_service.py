from utils.db import get_connection


def normalizar_ids(ids):
    ids_limpos = []
    for item_id in ids or []:
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError):
            continue
        if item_id_int not in ids_limpos:
            ids_limpos.append(item_id_int)
    return ids_limpos


def buscar_ultimas_mensagens_conversas(conversa_ids, empresa_id, conn=None):
    ids_limpos = normalizar_ids(conversa_ids)
    if not ids_limpos or not empresa_id:
        return {}

    placeholders = ", ".join(["?"] * len(ids_limpos))
    deve_fechar = conn is None
    conn = conn or get_connection()
    mensagens = conn.execute(
        f"""
        SELECT
            c.id AS conversa_id,
            m.conteudo AS conteudo
        FROM conversas c
        LEFT JOIN (
            SELECT conversa_id, MAX(id) AS ultima_mensagem_id
            FROM mensagens
            WHERE conversa_id IN ({placeholders})
            GROUP BY conversa_id
        ) ultimas ON ultimas.conversa_id = c.id
        LEFT JOIN mensagens m ON m.id = ultimas.ultima_mensagem_id
        WHERE c.id IN ({placeholders})
          AND c.empresa_id = ?
        """,
        tuple(ids_limpos + ids_limpos + [empresa_id])
    ).fetchall()
    if deve_fechar:
        conn.close()

    return {
        row["conversa_id"]: row["conteudo"] or "Sem mensagens ainda"
        for row in mensagens
    }


def contar_mensagens_conversa(conversa_id, empresa_id, conn=None):
    if not conversa_id or not empresa_id:
        return {"total_mensagens": 0, "mensagens_bot": 0, "mensagens_com_regra": 0}

    deve_fechar = conn is None
    conn = conn or get_connection()
    resumo = conn.execute(
        """
        SELECT
            COUNT(m.id) AS total_mensagens,
            SUM(CASE WHEN m.remetente_tipo = 'bot' THEN 1 ELSE 0 END) AS mensagens_bot,
            SUM(CASE WHEN m.regra_id IS NOT NULL THEN 1 ELSE 0 END) AS mensagens_com_regra
        FROM conversas c
        LEFT JOIN mensagens m ON m.conversa_id = c.id
        WHERE c.id = ? AND c.empresa_id = ?
        """,
        (conversa_id, empresa_id)
    ).fetchone()
    if deve_fechar:
        conn.close()

    return {
        "total_mensagens": resumo["total_mensagens"] or 0,
        "mensagens_bot": resumo["mensagens_bot"] or 0,
        "mensagens_com_regra": resumo["mensagens_com_regra"] or 0,
    }

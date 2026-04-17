import json
from datetime import datetime, timedelta

from utils.db import get_connection


PERIODOS_METRICAS_PERMITIDOS = {"7", "15", "30", "90"}


def normalizar_periodo_metricas(periodo_dias):
    periodo = (periodo_dias or "30").strip()
    if periodo not in PERIODOS_METRICAS_PERMITIDOS:
        return "30"
    return periodo


def montar_resumo_evento(valor):
    if not valor:
        return ""

    try:
        payload = json.loads(valor)
        if isinstance(payload, dict):
            return ", ".join([f"{k}: {v}" for k, v in payload.items() if v is not None])[:140]
        return str(payload)[:140]
    except Exception:
        return str(valor)[:140]


def obter_dashboard_data(empresa_id):
    conn = get_connection()

    contadores = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM contatos WHERE empresa_id = ?) AS total_contatos,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ?) AS total_conversas,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ? AND status = 'aberta') AS conversas_abertas,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ? AND status = 'fechada') AS conversas_fechadas,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ?
            ) AS total_mensagens,
            (SELECT COUNT(*) FROM agendamentos WHERE empresa_id = ?) AS agendamentos_criados,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.remetente_tipo = 'humano'
            ) AS mensagens_humano,
            (SELECT COUNT(*) FROM canal_integracoes WHERE empresa_id = ? AND status = 'ativo') AS integracoes_ativas,
            (
                SELECT COUNT(*)
                FROM metricas_eventos
                WHERE empresa_id = ? AND tipo_evento IN ('regra_acionada', 'regra_fluxo_acionada')
            ) AS regras_acionadas,
            (
                SELECT COUNT(*)
                FROM metricas_eventos
                WHERE empresa_id = ? AND tipo_evento = 'fluxo_iniciado'
            ) AS fluxos_iniciados
        """,
        tuple([empresa_id] * 10)
    ).fetchone()

    atividade_recente = conn.execute(
        """
        SELECT tipo_evento, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
        ORDER BY id DESC
        LIMIT 6
        """,
        (empresa_id,)
    ).fetchall()

    conn.close()

    return {
        "total_contatos": contadores["total_contatos"] or 0,
        "total_conversas": contadores["total_conversas"] or 0,
        "conversas_abertas": contadores["conversas_abertas"] or 0,
        "conversas_fechadas": contadores["conversas_fechadas"] or 0,
        "total_mensagens": contadores["total_mensagens"] or 0,
        "agendamentos_criados": contadores["agendamentos_criados"] or 0,
        "mensagens_humano": contadores["mensagens_humano"] or 0,
        "integracoes_ativas": contadores["integracoes_ativas"] or 0,
        "regras_acionadas": contadores["regras_acionadas"] or 0,
        "fluxos_iniciados": contadores["fluxos_iniciados"] or 0,
        "atividade_recente": atividade_recente,
    }


def obter_metricas_data(empresa_id, periodo_dias="30", tipo_evento=""):
    periodo_dias = normalizar_periodo_metricas(periodo_dias)
    tipo_evento = (tipo_evento or "").strip()
    data_inicio = (datetime.now() - timedelta(days=int(periodo_dias))).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()

    top_regras = conn.execute(
        """
        SELECT
            r.nome,
            COUNT(m.id) AS total
        FROM mensagens m
        JOIN regras r ON r.id = m.regra_id AND r.empresa_id = ?
        WHERE m.regra_id IS NOT NULL
          AND m.conversa_id IN (
              SELECT id FROM conversas WHERE empresa_id = ?
          )
        GROUP BY r.nome
        ORDER BY total DESC
        LIMIT 5
        """,
        (empresa_id, empresa_id)
    ).fetchall()

    total_agendamentos = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE empresa_id = ?
        """,
        (empresa_id,)
    ).fetchone()["total"]

    desempenho_atendentes = conn.execute(
        """
        SELECT
            COALESCE(u.nome, ca.nome_atendente, 'Atendente') AS nome,
            COUNT(m.id) AS mensagens,
            COUNT(DISTINCT ca.conversa_id) AS conversas
        FROM conversa_atendentes ca
        LEFT JOIN users u ON u.id = ca.user_id
        LEFT JOIN mensagens m ON m.conversa_id = ca.conversa_id
            AND m.user_id = ca.user_id
            AND m.remetente_tipo = 'humano'
        JOIN conversas c ON c.id = ca.conversa_id
        WHERE c.empresa_id = ?
          AND ca.ativo = 1
        GROUP BY COALESCE(u.nome, ca.nome_atendente, 'Atendente')
        ORDER BY mensagens DESC, conversas DESC
        LIMIT 8
        """,
        (empresa_id,)
    ).fetchall()

    tempo_medio_resposta = conn.execute(
        """
        SELECT AVG(
            (
                SELECT (julianday(m2.criado_em) - julianday(m1.criado_em)) * 24 * 60
                FROM mensagens m2
                WHERE m2.conversa_id = m1.conversa_id
                  AND m2.id > m1.id
                  AND m2.remetente_tipo IN ('bot', 'humano')
                ORDER BY m2.id ASC
                LIMIT 1
            )
        ) AS minutos
        FROM mensagens m1
        WHERE m1.remetente_tipo = 'cliente'
          AND m1.conversa_id IN (
              SELECT id FROM conversas WHERE empresa_id = ?
          )
        """,
        (empresa_id,)
    ).fetchone()["minutos"]

    contadores_metricas = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM contatos WHERE empresa_id = ?) AS total_contatos,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ?) AS total_conversas,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ? AND status = 'aberta') AS conversas_abertas,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ? AND status = 'fechada') AS conversas_fechadas,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ?
            ) AS total_mensagens,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.remetente_tipo = 'bot'
            ) AS mensagens_bot,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.remetente_tipo = 'cliente'
            ) AS mensagens_cliente,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.remetente_tipo = 'humano'
            ) AS mensagens_humano,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.regra_id IS NOT NULL
            ) AS mensagens_com_regra,
            (SELECT COUNT(*) FROM canal_integracoes WHERE empresa_id = ? AND status = 'ativo') AS integracoes_ativas
        """,
        tuple([empresa_id] * 10)
    ).fetchone()

    eventos_metricas = conn.execute(
        """
        SELECT
            SUM(CASE WHEN tipo_evento IN ('regra_acionada', 'regra_fluxo_acionada') THEN 1 ELSE 0 END) AS regras_acionadas,
            SUM(CASE WHEN tipo_evento = 'fluxo_iniciado' THEN 1 ELSE 0 END) AS fluxos_iniciados,
            SUM(CASE WHEN tipo_evento = 'fluxo_finalizado' THEN 1 ELSE 0 END) AS fluxos_finalizados
        FROM metricas_eventos
        WHERE empresa_id = ?
        """,
        (empresa_id,)
    ).fetchone()

    metricas_data = {
        "total_contatos": contadores_metricas["total_contatos"] or 0,
        "total_conversas": contadores_metricas["total_conversas"] or 0,
        "conversas_abertas": contadores_metricas["conversas_abertas"] or 0,
        "conversas_fechadas": contadores_metricas["conversas_fechadas"] or 0,
        "total_mensagens": contadores_metricas["total_mensagens"] or 0,
        "mensagens_bot": contadores_metricas["mensagens_bot"] or 0,
        "mensagens_cliente": contadores_metricas["mensagens_cliente"] or 0,
        "mensagens_humano": contadores_metricas["mensagens_humano"] or 0,
        "mensagens_com_regra": contadores_metricas["mensagens_com_regra"] or 0,
        "total_agendamentos": total_agendamentos,
        "regras_acionadas": eventos_metricas["regras_acionadas"] or 0,
        "fluxos_iniciados": eventos_metricas["fluxos_iniciados"] or 0,
        "fluxos_finalizados": eventos_metricas["fluxos_finalizados"] or 0,
        "integracoes_ativas": contadores_metricas["integracoes_ativas"] or 0,
        "tempo_medio_resposta_min": round(float(tempo_medio_resposta or 0), 1),
        "desempenho_atendentes": desempenho_atendentes,
        "top_regras": top_regras,
        "filtros": {"periodo_dias": periodo_dias, "tipo_evento": tipo_evento},
    }

    params_eventos = [empresa_id, data_inicio]
    filtro_tipo_sql = ""
    if tipo_evento:
        filtro_tipo_sql = " AND tipo_evento = ?"
        params_eventos.append(tipo_evento)

    eventos_recentes = conn.execute(
        f"""
        SELECT id, tipo_evento, referencia_id, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
          {filtro_tipo_sql}
        ORDER BY id DESC
        LIMIT 30
        """,
        tuple(params_eventos)
    ).fetchall()
    metricas_data["top_tipos_evento"] = conn.execute(
        f"""
        SELECT tipo_evento, COUNT(*) AS total
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
          {filtro_tipo_sql}
        GROUP BY tipo_evento
        ORDER BY total DESC
        LIMIT 8
        """,
        tuple(params_eventos)
    ).fetchall()
    metricas_data["tipos_evento_disponiveis"] = [
        row["tipo_evento"]
        for row in conn.execute(
            """
            SELECT DISTINCT tipo_evento
            FROM metricas_eventos
            WHERE empresa_id = ?
            ORDER BY tipo_evento ASC
            """,
            (empresa_id,)
        ).fetchall()
    ]

    metricas_data["eventos_recentes"] = [
        {**dict(evento), "resumo": montar_resumo_evento(evento["valor"])}
        for evento in eventos_recentes
    ]

    conn.close()
    return metricas_data


def obter_teste_banco_data(empresa_id):
    conn = get_connection()

    contadores = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM contatos WHERE empresa_id = ?) AS total_contatos,
            (SELECT COUNT(*) FROM conversas WHERE empresa_id = ?) AS total_conversas,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ?
            ) AS total_mensagens,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ? AND m.regra_id IS NOT NULL
            ) AS total_mensagens_com_regra,
            (SELECT COUNT(*) FROM agendamentos WHERE empresa_id = ?) AS total_agendamentos,
            (SELECT COUNT(*) FROM fluxos WHERE empresa_id = ?) AS total_fluxos
        """,
        tuple([empresa_id] * 6)
    ).fetchone()

    conn.close()

    return {
        "total_contatos": contadores["total_contatos"] or 0,
        "total_conversas": contadores["total_conversas"] or 0,
        "total_mensagens": contadores["total_mensagens"] or 0,
        "total_mensagens_com_regra": contadores["total_mensagens_com_regra"] or 0,
        "total_agendamentos": contadores["total_agendamentos"] or 0,
        "total_fluxos": contadores["total_fluxos"] or 0,
    }

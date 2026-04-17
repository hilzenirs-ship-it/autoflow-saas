from datetime import datetime, timezone

import redis
from flask import Blueprint, jsonify

from config import Config
from services.dashboard_service import obter_teste_banco_data
from services.empresa_service import buscar_nome_empresa
from utils.auth import login_required, obter_empresa_id_logada
from utils.db import get_connection


diagnostico_bp = Blueprint("diagnostico", __name__)


@diagnostico_bp.route("/healthz")
def healthz():
    resultado = {
        "status": "ok",
        "app": "ok",
        "database": "ok",
        "redis": "not_configured",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception:
        resultado["status"] = "error"
        resultado["database"] = "unavailable"

    redis_url = Config.CACHE_REDIS_URL or Config.RATELIMIT_STORAGE_URI or Config.REDIS_URL
    if redis_url and redis_url != "memory://" and redis_url.startswith(("redis://", "rediss://", "unix://")):
        try:
            cliente = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            cliente.ping()
            resultado["redis"] = "ok"
        except Exception:
            resultado["status"] = "error"
            resultado["redis"] = "unavailable"

    status_code = 200 if resultado["status"] == "ok" else 503
    return jsonify(resultado), status_code


@diagnostico_bp.route("/teste-banco")
@login_required
def teste_banco():
    empresa_id = obter_empresa_id_logada()
    contadores = obter_teste_banco_data(empresa_id)

    return f"""
    Banco conectado.<br>
    Empresa logada: {buscar_nome_empresa(empresa_id)}<br>
    Total de contatos: {contadores["total_contatos"] or 0}<br>
    Total de conversas: {contadores["total_conversas"] or 0}<br>
    Total de mensagens: {contadores["total_mensagens"] or 0}<br>
    Total de mensagens com regra: {contadores["total_mensagens_com_regra"] or 0}<br>
    Total de agendamentos: {contadores["total_agendamentos"] or 0}<br>
    Total de fluxos: {contadores["total_fluxos"] or 0}
    """

from flask import Blueprint, jsonify

from services.dashboard_service import obter_teste_banco_data
from services.empresa_service import buscar_nome_empresa
from utils.auth import login_required, obter_empresa_id_logada
from utils.db import get_connection


diagnostico_bp = Blueprint("diagnostico", __name__)


@diagnostico_bp.route("/healthz")
def healthz():
    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception:
        return jsonify({"status": "error", "database": "unavailable"}), 503

    return jsonify({"status": "ok", "database": "ok"}), 200


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

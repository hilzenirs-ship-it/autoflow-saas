import csv
import io
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

from services.dashboard_service import obter_metricas_data
from utils.auth import login_required, obter_empresa_id_logada
from utils.db import get_connection
from utils.limiter import limiter


metricas_bp = Blueprint("metricas", __name__)


@metricas_bp.route("/metricas")
@login_required
def metricas():
    empresa_id = obter_empresa_id_logada()
    periodo_dias = (request.args.get("periodo_dias") or "30").strip()
    tipo_evento = (request.args.get("tipo_evento") or "").strip()
    metricas_data = obter_metricas_data(empresa_id, periodo_dias, tipo_evento)
    return render_template("metricas.html", metricas=metricas_data)


@metricas_bp.route("/metricas/eventos/exportar")
@login_required
@limiter.limit("20 per minute")
def exportar_metricas_eventos():
    empresa_id = obter_empresa_id_logada()
    periodo_dias = (request.args.get("periodo_dias") or "30").strip()
    tipo_evento = (request.args.get("tipo_evento") or "").strip()
    if periodo_dias not in ["7", "15", "30", "90"]:
        periodo_dias = "30"

    data_inicio = (datetime.now() - timedelta(days=int(periodo_dias))).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    query = """
        SELECT id, tipo_evento, referencia_id, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
    """
    params = [empresa_id, data_inicio]
    if tipo_evento:
        query += " AND tipo_evento = ?"
        params.append(tipo_evento)
    query += " ORDER BY id DESC"
    eventos = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Tipo evento", "Referencia", "Valor", "Criado em"])
    for evento in eventos:
        writer.writerow([
            evento["id"],
            evento["tipo_evento"] or "",
            evento["referencia_id"] or "",
            evento["valor"] or "",
            evento["criado_em"] or "",
        ])
    output.seek(0)
    return output.getvalue(), 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=metricas_eventos.csv",
    }

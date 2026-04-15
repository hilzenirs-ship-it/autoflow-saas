from flask import Blueprint, render_template, session, redirect, url_for
from utils.db import get_connection
from utils.auth import login_required, obter_empresa_id_logada

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()

    total_contatos = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    total_conversas = conn.execute(
        "SELECT COUNT(*) AS total FROM conversas WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    conversas_abertas = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM conversas
        WHERE empresa_id = ? AND status = 'aberta'
        """,
        (empresa_id,)
    ).fetchone()["total"]

    total_mensagens = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens
        WHERE conversa_id IN (
            SELECT id FROM conversas WHERE empresa_id = ?
        )
        """,
        (empresa_id,)
    ).fetchone()["total"]

    conn.close()

    return render_template(
        "dashboard.html",
        total_contatos=total_contatos,
        total_conversas=total_conversas,
        conversas_abertas=conversas_abertas,
        total_mensagens=total_mensagens
    )
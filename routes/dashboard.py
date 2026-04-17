from flask import Blueprint, render_template
from services.dashboard_service import obter_dashboard_data
from utils.auth import login_required, obter_empresa_id_logada

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    empresa_id = obter_empresa_id_logada()
    return render_template("dashboard.html", **obter_dashboard_data(empresa_id))

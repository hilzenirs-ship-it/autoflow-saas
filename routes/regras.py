from importlib import import_module

from flask import Blueprint

from utils.auth import login_required
from utils.limiter import limiter


regras_bp = Blueprint("regras", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@regras_bp.route("/regras")
@login_required
def regras():
    return _app_func("regras")()


@regras_bp.route("/regras/nova", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def nova_regra():
    return _app_func("nova_regra")()


@regras_bp.route("/regras/editar/<int:regra_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"])
def editar_regra(regra_id):
    return _app_func("editar_regra")(regra_id)


@regras_bp.route("/regras/<int:regra_id>/toggle", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def toggle_regra(regra_id):
    return _app_func("toggle_regra")(regra_id)


@regras_bp.route("/regras/excluir/<int:regra_id>", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def excluir_regra(regra_id):
    return _app_func("excluir_regra")(regra_id)

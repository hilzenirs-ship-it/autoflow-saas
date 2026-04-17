from importlib import import_module

from flask import Blueprint

from utils.auth import login_required
from utils.limiter import limiter


agendamentos_bp = Blueprint("agendamentos", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@agendamentos_bp.route("/agendamentos")
@login_required
def agendamentos():
    return _app_func("agendamentos")()


@agendamentos_bp.route("/agendamentos/exportar")
@login_required
def exportar_agendamentos():
    return _app_func("exportar_agendamentos")()


@agendamentos_bp.route("/agendamentos/<int:agendamento_id>/cancelar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def cancelar_agendamento(agendamento_id):
    return _app_func("cancelar_agendamento")(agendamento_id)


@agendamentos_bp.route("/agendamentos/<int:agendamento_id>/remarcar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def remarcar_agendamento(agendamento_id):
    return _app_func("remarcar_agendamento")(agendamento_id)

from importlib import import_module

from flask import Blueprint

from utils.auth import login_required
from utils.limiter import limiter


fluxos_bp = Blueprint("fluxos", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@fluxos_bp.route("/fluxos")
@login_required
def fluxos():
    return _app_func("fluxos")()


@fluxos_bp.route("/fluxos/novo", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def novo_fluxo():
    return _app_func("novo_fluxo")()


@fluxos_bp.route("/fluxos/<int:fluxo_id>/editar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def editar_fluxo(fluxo_id):
    return _app_func("editar_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/toggle", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def toggle_fluxo(fluxo_id):
    return _app_func("toggle_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/duplicar", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def duplicar_fluxo(fluxo_id):
    return _app_func("duplicar_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/excluir", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def excluir_fluxo(fluxo_id):
    return _app_func("excluir_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/editor")
@login_required
def fluxo_editor_redirect():
    return _app_func("fluxo_editor_redirect")()


@fluxos_bp.route("/fluxos/editor/<int:fluxo_id>")
@login_required
def fluxo_editor(fluxo_id):
    return _app_func("fluxo_editor")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/debug-execucoes")
@login_required
def fluxo_debug_execucoes(fluxo_id):
    return _app_func("fluxo_debug_execucoes")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/blocos/novo", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def novo_bloco_fluxo(fluxo_id):
    return _app_func("novo_bloco_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/blocos/salvar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def salvar_blocos_fluxo(fluxo_id):
    return _app_func("salvar_blocos_fluxo")(fluxo_id)


@fluxos_bp.route("/fluxos/<int:fluxo_id>/blocos/<int:bloco_id>/excluir", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def excluir_bloco_fluxo(fluxo_id, bloco_id):
    return _app_func("excluir_bloco_fluxo")(fluxo_id, bloco_id)

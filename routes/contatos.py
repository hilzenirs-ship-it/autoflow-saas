from importlib import import_module

from flask import Blueprint

from utils.auth import login_required
from utils.limiter import limiter


contatos_bp = Blueprint("contatos", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@contatos_bp.route("/contatos")
@login_required
def contatos():
    return _app_func("contatos")()


@contatos_bp.route("/contatos/exportar")
@login_required
def exportar_contatos():
    return _app_func("exportar_contatos")()


@contatos_bp.route("/contatos/novo", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"])
def novo_contato():
    return _app_func("novo_contato")()


@contatos_bp.route("/contatos/editar/<int:id>", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"])
def editar_contato(id):
    return _app_func("editar_contato")(id)


@contatos_bp.route("/contatos/excluir/<int:id>", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def excluir_contato(id):
    return _app_func("excluir_contato")(id)


@contatos_bp.route("/tags/nova", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def nova_tag():
    return _app_func("nova_tag")()


@contatos_bp.route("/tags/<int:tag_id>/excluir", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def excluir_tag(tag_id):
    return _app_func("excluir_tag")(tag_id)

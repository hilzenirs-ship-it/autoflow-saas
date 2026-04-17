from importlib import import_module

from flask import Blueprint

from utils.auth import login_required
from utils.limiter import limiter


conversas_bp = Blueprint("conversas", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@conversas_bp.route("/conversas")
@login_required
def conversas():
    return _app_func("conversas")()


@conversas_bp.route("/conversas/exportar")
@login_required
def exportar_conversas():
    return _app_func("exportar_conversas")()


@conversas_bp.route("/conversas/contato/<int:contato_id>")
@login_required
def abrir_conversa_por_contato(contato_id):
    return _app_func("abrir_conversa_por_contato")(contato_id)


@conversas_bp.route("/conversas/<int:conversa_id>")
@login_required
def ver_conversa(conversa_id):
    return _app_func("ver_conversa")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/mensagem", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def enviar_mensagem(conversa_id):
    return _app_func("enviar_mensagem")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/mensagens/recentes")
@login_required
@limiter.limit("120 per minute")
def mensagens_recentes_conversa(conversa_id):
    return _app_func("mensagens_recentes_conversa")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/iniciar-fluxo/<int:fluxo_id>")
@login_required
@limiter.limit("30 per minute")
def iniciar_fluxo_manual_conversa(conversa_id, fluxo_id):
    return _app_func("iniciar_fluxo_manual_conversa")(conversa_id, fluxo_id)


@conversas_bp.route("/conversas/<int:conversa_id>/simular-cliente", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def simular_mensagem_cliente(conversa_id):
    return _app_func("simular_mensagem_cliente")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/status/<novo_status>", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def alterar_status_conversa(conversa_id, novo_status):
    return _app_func("alterar_status_conversa")(conversa_id, novo_status)


@conversas_bp.route("/conversas/<int:conversa_id>/bot/<int:ativo>", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def alterar_bot_conversa(conversa_id, ativo):
    return _app_func("alterar_bot_conversa")(conversa_id, ativo)


@conversas_bp.route("/conversas/<int:conversa_id>/assumir", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def assumir_conversa(conversa_id):
    return _app_func("assumir_conversa")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/aguardando-cliente", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def marcar_conversa_aguardando_cliente(conversa_id):
    return _app_func("marcar_conversa_aguardando_cliente")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/retomar-atendimento", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def retomar_atendimento_conversa(conversa_id):
    return _app_func("retomar_atendimento_conversa")(conversa_id)


@conversas_bp.route("/conversas/<int:conversa_id>/devolver-bot", methods=["POST"])
@login_required
@limiter.limit("60 per minute")
def devolver_conversa_ao_bot(conversa_id):
    return _app_func("devolver_conversa_ao_bot")(conversa_id)

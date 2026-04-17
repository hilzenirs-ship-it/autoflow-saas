from importlib import import_module

from flask import Blueprint

from utils.limiter import limiter


webhooks_bp = Blueprint("webhooks", __name__)


def _app_func(nome):
    return getattr(import_module("app"), nome)


@webhooks_bp.route("/webhooks/whatsapp/<token>", methods=["GET", "POST"])
@limiter.limit("120 per minute", methods=["POST"])
@limiter.limit("30 per minute", methods=["GET"])
def webhook_whatsapp(token):
    return _app_func("webhook_whatsapp")(token)


@webhooks_bp.route("/webhooks/mercadopago", methods=["POST"])
@limiter.limit("60 per minute")
def webhook_mercadopago():
    return _app_func("webhook_mercadopago")()

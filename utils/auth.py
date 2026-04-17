from flask import has_request_context, session, redirect, url_for
from functools import wraps


def usuario_logado():
    if not has_request_context():
        return False
    return "user_id" in session and "empresa_id" in session


def obter_user_id_logado():
    if not has_request_context():
        return None
    return session.get("user_id")


def obter_empresa_id_logada():
    if not has_request_context():
        return None
    return session.get("empresa_id")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not usuario_logado():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

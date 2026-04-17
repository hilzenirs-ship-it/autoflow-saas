from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from services.auth_service import buscar_empresa_do_usuario, buscar_usuario_por_email, gerar_hash_senha, senha_confere
from services.saas_limits_service import garantir_limites_empresa
from utils.auth import usuario_logado
from utils.db import get_connection
from utils.limiter import limiter


auth_bp = Blueprint("auth", __name__)


def registrar_login_log(user_id=None, empresa_id=None, email_tentado=None, status="sucesso", motivo=None):
    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO login_logs (
                user_id, empresa_id, email_tentado, ip, user_agent, status, motivo, criado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                user_id,
                empresa_id,
                (email_tentado or "").strip().lower() or None,
                request.remote_addr,
                request.headers.get("User-Agent"),
                status,
                motivo,
            )
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        current_app.logger.warning("Falha ao registrar login_log: %s", exc)


@auth_bp.route("/", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if usuario_logado():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()

        if not email or not senha:
            registrar_login_log(email_tentado=email, status="falha", motivo="campos_obrigatorios")
            flash("Preencha e-mail e senha.", "erro")
            return render_template("login.html", email=email)

        usuario = buscar_usuario_por_email(email)

        if not usuario:
            registrar_login_log(email_tentado=email, status="falha", motivo="credenciais_invalidas")
            flash("Usuario nao encontrado.", "erro")
            return render_template("login.html", email=email)

        if not senha_confere(senha, usuario["senha_hash"]):
            empresa_log = buscar_empresa_do_usuario(usuario["id"])
            registrar_login_log(
                user_id=usuario["id"],
                empresa_id=empresa_log["id"] if empresa_log else None,
                email_tentado=email,
                status="falha",
                motivo="credenciais_invalidas"
            )
            flash("Senha invalida.", "erro")
            return render_template("login.html", email=email)

        empresa = buscar_empresa_do_usuario(usuario["id"])

        if not empresa:
            registrar_login_log(
                user_id=usuario["id"],
                email_tentado=email,
                status="falha",
                motivo="empresa_nao_vinculada"
            )
            flash("Usuario sem empresa vinculada.", "erro")
            return render_template("login.html", email=email)

        session["user_id"] = usuario["id"]
        session["user_nome"] = usuario["nome"]
        session["user_email"] = usuario["email"]
        session["empresa_id"] = empresa["id"]
        session["empresa_nome"] = empresa["nome_exibicao"] or empresa["nome_empresa"]

        registrar_login_log(
            user_id=usuario["id"],
            empresa_id=empresa["id"],
            email_tentado=email,
            status="sucesso",
            motivo=None
        )

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def cadastro():
    if usuario_logado():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        empresa_nome = (request.form.get("empresa") or "").strip()
        senha = (request.form.get("senha") or "").strip()

        if not nome or not email or not empresa_nome or not senha:
            flash("Preencha todos os campos.", "erro")
            return render_template(
                "cadastro.html",
                nome=nome,
                email=email,
                empresa=empresa_nome
            )

        conn = get_connection()

        usuario_existente = conn.execute(
            """
            SELECT id
            FROM users
            WHERE lower(email) = ?
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            flash("Esse e-mail ja esta cadastrado.", "erro")
            return render_template(
                "cadastro.html",
                nome=nome,
                email=email,
                empresa=empresa_nome
            )

        senha_hash = gerar_hash_senha(senha)

        cursor = conn.execute(
            """
            INSERT INTO users (nome, email, senha_hash)
            VALUES (?, ?, ?)
            """,
            (nome, email, senha_hash)
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """
            INSERT INTO empresas (user_id, nome_empresa, nome_exibicao, email)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, empresa_nome, empresa_nome, email)
        )
        empresa_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo)
            VALUES (?, ?, 'owner', 1)
            """,
            (empresa_id, user_id)
        )
        garantir_limites_empresa(empresa_id, conn=conn)

        conn.commit()
        conn.close()

        session["user_id"] = user_id
        session["user_nome"] = nome
        session["user_email"] = email
        session["empresa_id"] = empresa_id
        session["empresa_nome"] = empresa_nome

        return redirect(url_for("dashboard"))

    return render_template("cadastro.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

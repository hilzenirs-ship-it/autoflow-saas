from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.db import get_connection
from werkzeug.security import check_password_hash, generate_password_hash
from utils.auth import usuario_logado
from utils.limiter import limiter
from typing import Optional

auth_bp = Blueprint('auth', __name__)

def buscar_usuario_por_email(email: str) -> Optional[dict]:
    conn = get_connection()
    usuario = conn.execute(
        """
        SELECT id, nome, email, senha_hash
        FROM users
        WHERE lower(email) = ?
        LIMIT 1
        """,
        (email,)
    ).fetchone()
    conn.close()
    return usuario

def senha_confere(senha: str, senha_hash: str) -> bool:
    return check_password_hash(senha_hash, senha)

def gerar_hash_senha(senha: str) -> str:
    return generate_password_hash(senha)

def buscar_empresa_do_usuario(user_id: int) -> Optional[dict]:
    conn = get_connection()
    empresa = conn.execute(
        """
        SELECT e.id, e.nome_empresa, e.nome_exibicao
        FROM empresas e
        JOIN empresa_membros em ON em.empresa_id = e.id
        WHERE em.user_id = ? AND em.ativo = 1
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return empresa

@auth_bp.route("/", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if usuario_logado():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()

        if not email or not senha:
            flash("Preencha e-mail e senha.", "erro")
            return render_template("login.html", email=email)

        usuario = buscar_usuario_por_email(email)

        if not usuario:
            flash("Usuário não encontrado.", "erro")
            return render_template("login.html", email=email)

        if not senha_confere(senha, usuario["senha_hash"]):
            flash("Senha inválida.", "erro")
            return render_template("login.html", email=email)

        empresa = buscar_empresa_do_usuario(usuario["id"])

        if not empresa:
            flash("Usuário sem empresa vinculada.", "erro")
            return render_template("login.html", email=email)

        session["user_id"] = usuario["id"]
        session["user_nome"] = usuario["nome"]
        session["user_email"] = usuario["email"]
        session["empresa_id"] = empresa["id"]
        session["empresa_nome"] = empresa["nome_exibicao"] or empresa["nome_empresa"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("3 per minute")
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
            flash("Esse e-mail já está cadastrado.", "erro")
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
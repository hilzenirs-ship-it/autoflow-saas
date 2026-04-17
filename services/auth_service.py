import os

from werkzeug.security import check_password_hash, generate_password_hash

from utils.db import get_connection


def _permite_senha_legada_texto_puro():
    ambiente = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "production")).strip().lower()
    return ambiente in {"development", "testing"}


def senha_confere(senha_digitada, senha_salva):
    senha_digitada = (senha_digitada or "").strip()
    senha_salva = (senha_salva or "").strip()

    if not senha_digitada or not senha_salva:
        return False

    try:
        if senha_salva.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            return check_password_hash(senha_salva, senha_digitada)
    except Exception:
        pass

    if _permite_senha_legada_texto_puro():
        return senha_digitada == senha_salva

    return False


def gerar_hash_senha(senha):
    senha = (senha or "").strip()
    if not senha:
        return ""
    return generate_password_hash(senha)


def buscar_usuario_por_email(email):
    email = (email or "").strip().lower()
    if not email:
        return None

    conn = get_connection()
    usuario = conn.execute(
        """
        SELECT *
        FROM users
        WHERE lower(email) = ?
        LIMIT 1
        """,
        (email,)
    ).fetchone()
    conn.close()
    return usuario


def buscar_empresa_do_usuario(user_id):
    conn = get_connection()
    empresa = conn.execute(
        """
        SELECT e.*
        FROM empresas e
        JOIN empresa_membros em ON em.empresa_id = e.id
        WHERE em.user_id = ? AND em.ativo = 1
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, e.id ASC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return empresa


def buscar_empresas_do_usuario(user_id):
    conn = get_connection()
    empresas = conn.execute(
        """
        SELECT
            e.*,
            em.papel
        FROM empresas e
        JOIN empresa_membros em ON em.empresa_id = e.id
        WHERE em.user_id = ? AND em.ativo = 1
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, e.nome_empresa ASC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return empresas

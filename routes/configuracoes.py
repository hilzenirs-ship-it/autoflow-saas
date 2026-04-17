import json
import secrets

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services.agendamento_service import normalizar_horario_agendamento
from services.auth_service import buscar_empresas_do_usuario
from services.eventos_service import registrar_evento
from services.saas_limits_service import flash_limite_bloqueado, montar_status_limites, verificar_limite_recurso
from utils.auth import login_required, obter_empresa_id_logada, obter_user_id_logado
from utils.db import get_connection
from utils.limiter import limiter


configuracoes_bp = Blueprint("configuracoes", __name__)


@configuracoes_bp.route("/configuracoes")
@login_required
def configuracoes():
    conn = get_connection()
    empresas_usuario = buscar_empresas_do_usuario(obter_user_id_logado())
    empresa_id = obter_empresa_id_logada()
    membros_empresa = conn.execute(
        """
        SELECT
            u.nome,
            u.email,
            em.papel,
            em.ativo
        FROM empresa_membros em
        JOIN users u ON u.id = em.user_id
        WHERE em.empresa_id = ?
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, u.nome ASC
        """,
        (empresa_id,)
    ).fetchall()
    disponibilidade = conn.execute(
        """
        SELECT id, dia_semana, hora_inicio, hora_fim, ativo
        FROM agenda_disponibilidade
        WHERE empresa_id = ?
        ORDER BY dia_semana ASC, hora_inicio ASC
        """,
        (empresa_id,)
    ).fetchall()
    integracoes = conn.execute(
        """
        SELECT id, canal, nome, status, webhook_token, phone_number_id,
               business_account_id, instagram_account_id, atualizado_em
        FROM canal_integracoes
        WHERE empresa_id = ?
        ORDER BY canal ASC, id DESC
        """,
        (empresa_id,)
    ).fetchall()
    plano_empresa = conn.execute(
        """
        SELECT el.*, ps.nome AS plano_nome, ps.descricao AS plano_descricao
        FROM empresa_limites el
        LEFT JOIN planos_saas ps ON ps.id = el.plano_id
        WHERE el.empresa_id = ?
        LIMIT 1
        """,
        (empresa_id,)
    ).fetchone()
    status_limites = montar_status_limites(empresa_id, conn=conn)
    conn.close()
    return render_template(
        "configuracoes.html",
        empresas_usuario=empresas_usuario,
        membros_empresa=membros_empresa,
        disponibilidade=disponibilidade,
        integracoes=integracoes,
        plano_empresa=plano_empresa,
        status_limites=status_limites,
        empresa_id_logada=empresa_id,
    )


@configuracoes_bp.route("/configuracoes/trocar-empresa", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def trocar_empresa():
    empresa_id_nova = (request.form.get("empresa_id") or "").strip()
    if not empresa_id_nova.isdigit():
        return redirect(url_for("configuracoes"))

    conn = get_connection()
    membro = conn.execute(
        """
        SELECT e.id, e.nome_exibicao, e.nome_empresa
        FROM empresa_membros em
        JOIN empresas e ON e.id = em.empresa_id
        WHERE em.user_id = ? AND em.empresa_id = ? AND em.ativo = 1
        LIMIT 1
        """,
        (obter_user_id_logado(), int(empresa_id_nova))
    ).fetchone()
    conn.close()

    if not membro:
        flash("Voce nao pertence a essa empresa.", "erro")
        return redirect(url_for("configuracoes"))

    session["empresa_id"] = membro["id"]
    session["empresa_nome"] = membro["nome_exibicao"] or membro["nome_empresa"]
    registrar_evento("troca_contexto_empresa", referencia_id=membro["id"])
    return redirect(url_for("dashboard"))


@configuracoes_bp.route("/configuracoes/membros/adicionar", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def adicionar_membro_empresa():
    email = (request.form.get("email") or "").strip().lower()
    papel = (request.form.get("papel") or "membro").strip().lower()
    papel = papel if papel in ["owner", "admin", "membro"] else "membro"
    if not email:
        return redirect(url_for("configuracoes"))

    conn = get_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE lower(email) = ? LIMIT 1",
        (email,)
    ).fetchone()
    if not user:
        conn.close()
        flash("Usuario nao encontrado para esse e-mail.", "erro")
        return redirect(url_for("configuracoes"))

    existe = conn.execute(
        """
        SELECT id
        FROM empresa_membros
        WHERE empresa_id = ? AND user_id = ?
        LIMIT 1
        """,
        (obter_empresa_id_logada(), user["id"])
    ).fetchone()
    if existe:
        conn.execute(
            """
            UPDATE empresa_membros
            SET ativo = 1, papel = ?
            WHERE id = ? AND empresa_id = ?
            """,
            (papel, existe["id"], obter_empresa_id_logada())
        )
    else:
        limite_ok, mensagem_limite = verificar_limite_recurso(obter_empresa_id_logada(), "atendentes", conn=conn)
        if not limite_ok:
            conn.close()
            flash_limite_bloqueado(mensagem_limite)
            return redirect(url_for("configuracoes"))
        conn.execute(
            """
            INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo)
            VALUES (?, ?, ?, 1)
            """,
            (obter_empresa_id_logada(), user["id"], papel)
        )

    conn.commit()
    conn.close()
    registrar_evento("membro_adicionado", valor=email)
    return redirect(url_for("configuracoes"))


@configuracoes_bp.route("/configuracoes/disponibilidade/adicionar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def adicionar_disponibilidade():
    dia_semana = (request.form.get("dia_semana") or "").strip()
    hora_inicio = (request.form.get("hora_inicio") or "").strip()
    hora_fim = (request.form.get("hora_fim") or "").strip()
    if not dia_semana.isdigit() or not hora_inicio or not hora_fim:
        return redirect(url_for("configuracoes"))

    dia_semana_int = int(dia_semana)
    if dia_semana_int < 0 or dia_semana_int > 6:
        flash("Dia da semana invalido.", "erro")
        return redirect(url_for("configuracoes"))

    hora_inicio_norm, erro_inicio = normalizar_horario_agendamento(hora_inicio)
    hora_fim_norm, erro_fim = normalizar_horario_agendamento(hora_fim)
    if erro_inicio or erro_fim or hora_inicio_norm >= hora_fim_norm:
        flash("Informe uma faixa de horario valida.", "erro")
        return redirect(url_for("configuracoes"))

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO agenda_disponibilidade (empresa_id, dia_semana, hora_inicio, hora_fim, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        (obter_empresa_id_logada(), dia_semana_int, hora_inicio_norm, hora_fim_norm)
    )
    conn.commit()
    conn.close()
    registrar_evento("disponibilidade_adicionada", valor=f"{dia_semana}:{hora_inicio_norm}-{hora_fim_norm}")
    return redirect(url_for("configuracoes"))


@configuracoes_bp.route("/configuracoes/integracoes/salvar", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def salvar_integracao_canal():
    canal = (request.form.get("canal") or "").strip().lower()
    nome = (request.form.get("nome") or "").strip()
    status = (request.form.get("status") or "rascunho").strip().lower()
    access_token = (request.form.get("access_token") or "").strip()
    phone_number_id = (request.form.get("phone_number_id") or "").strip()
    business_account_id = (request.form.get("business_account_id") or "").strip()
    instagram_account_id = (request.form.get("instagram_account_id") or "").strip()
    config_json_texto = (request.form.get("config_json") or "").strip()

    if canal not in ["whatsapp", "instagram"]:
        flash("Canal invalido para integracao.", "erro")
        return redirect(url_for("configuracoes"))
    if status not in ["rascunho", "ativo", "pausado"]:
        status = "rascunho"

    try:
        config_payload = json.loads(config_json_texto) if config_json_texto else {}
        if not isinstance(config_payload, dict):
            config_payload = {}
    except Exception:
        flash("Config JSON invalido. Mantive a integracao sem salvar.", "erro")
        return redirect(url_for("configuracoes"))

    webhook_token = (request.form.get("webhook_token") or "").strip() or secrets.token_urlsafe(24)
    conn = get_connection()
    existente = conn.execute(
        """
        SELECT id, access_token
        FROM canal_integracoes
        WHERE empresa_id = ? AND canal = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (obter_empresa_id_logada(), canal)
    ).fetchone()
    if existente:
        conn.execute(
            """
            UPDATE canal_integracoes
            SET nome = ?, status = ?, access_token = ?, webhook_token = ?, phone_number_id = ?,
                business_account_id = ?, instagram_account_id = ?, config_json = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ?
            """,
            (
                nome or canal.title(),
                status,
                access_token or existente["access_token"],
                webhook_token,
                phone_number_id,
                business_account_id,
                instagram_account_id,
                json.dumps(config_payload, ensure_ascii=False),
                existente["id"],
                obter_empresa_id_logada(),
            )
        )
        integracao_id = existente["id"]
    else:
        limite_ok, mensagem_limite = verificar_limite_recurso(obter_empresa_id_logada(), "integracoes", conn=conn)
        if not limite_ok:
            conn.close()
            flash_limite_bloqueado(mensagem_limite)
            return redirect(url_for("configuracoes"))
        cursor = conn.execute(
            """
            INSERT INTO canal_integracoes (
                empresa_id, canal, nome, status, access_token, webhook_token, phone_number_id,
                business_account_id, instagram_account_id, config_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obter_empresa_id_logada(),
                canal,
                nome or canal.title(),
                status,
                access_token,
                webhook_token,
                phone_number_id,
                business_account_id,
                instagram_account_id,
                json.dumps(config_payload, ensure_ascii=False),
            )
        )
        integracao_id = cursor.lastrowid

    conn.commit()
    conn.close()
    registrar_evento("integracao_salva", referencia_id=integracao_id, valor=canal)
    return redirect(url_for("configuracoes"))

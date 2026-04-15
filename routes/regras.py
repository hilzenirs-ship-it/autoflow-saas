from flask import Blueprint, render_template, request, redirect, url_for
from utils.db import get_connection
from utils.auth import login_required, obter_empresa_id_logada
from services.regras_service import montar_regra_para_template, registrar_evento
import json

regras_bp = Blueprint('regras', __name__)

@regras_bp.route("/regras")
@login_required
def regras():
    conn = get_connection()
    regras_db = conn.execute(
        """
        SELECT r.*, f.nome AS fluxo_nome
        FROM regras r
        LEFT JOIN fluxos f ON f.id = r.fluxo_id
        WHERE r.empresa_id = ?
        ORDER BY r.id DESC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    fluxos_db = conn.execute(
        """
        SELECT id, nome
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()
    tags_db = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    conn.close()

    regras_lista = [montar_regra_para_template(regra) for regra in regras_db]

    return render_template("regras.html", regras=regras_lista, fluxos=fluxos_db, tags=tags_db)

@regras_bp.route("/regras/nova", methods=["POST"])
@login_required
def nova_regra():
    nome = (request.form.get("nome") or "").strip()
    palavras = (request.form.get("palavras_chave") or "").strip()
    resposta = (request.form.get("resposta") or "").strip()
    fluxo_id = (request.form.get("fluxo_id") or "").strip()
    prioridade = (request.form.get("prioridade") or "0").strip()
    etapa_destino = (request.form.get("etapa_destino") or "").strip()
    tag_id = (request.form.get("tag_id") or "").strip()
    operador_palavras = (request.form.get("operador_palavras") or "any").strip().lower()
    excluir_palavras_texto = (request.form.get("excluir_palavras") or "").strip()
    etapa_cond = (request.form.get("etapa_condicao") or "").strip()
    status_cond = (request.form.get("status_condicao") or "").strip()

    if nome and palavras and (resposta or fluxo_id):
        palavras_lista = []
        for p in palavras.split(","):
            p = p.strip()
            if p:
                palavras_lista.append(p)

        condicao_json = json.dumps(
            {
                "palavras_chave": palavras_lista,
                "operador_palavras": "all" if operador_palavras == "all" else "any",
                "excluir_palavras": [p.strip() for p in excluir_palavras_texto.split(",") if p.strip()],
                "etapa": etapa_cond or None,
                "status_conversa": status_cond or None,
            },
            ensure_ascii=False
        )

        acao_json = json.dumps(
            {
                "resposta": resposta,
                "prioridade": int(prioridade) if prioridade.isdigit() else 0,
                "etapa_destino": etapa_destino or None,
                "tag_id": int(tag_id) if tag_id.isdigit() else None,
            },
            ensure_ascii=False
        )

        fluxo_id_valor = int(fluxo_id) if fluxo_id.isdigit() else None

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO regras (
                empresa_id,
                nome,
                tipo_regra,
                condicao_json,
                acao_json,
                fluxo_id,
                ativa
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obter_empresa_id_logada(),
                nome,
                "palavra_chave",
                condicao_json,
                acao_json,
                fluxo_id_valor,
                1
            )
        )
        conn.commit()
        conn.close()
        registrar_evento("regra_criada", valor=nome)

    return redirect(url_for("regras.regras"))

@regras_bp.route("/regras/editar/<int:regra_id>", methods=["GET", "POST"])
@login_required
def editar_regra(regra_id):
    conn = get_connection()

    regra_row = conn.execute(
        """
        SELECT *
        FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    ).fetchone()

    fluxos_db = conn.execute(
        """
        SELECT id, nome
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()
    tags_db = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    if not regra_row:
        conn.close()
        return redirect(url_for("regras.regras"))

    regra = montar_regra_para_template(regra_row)

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        palavras = (request.form.get("palavras_chave") or "").strip()
        resposta = (request.form.get("resposta") or "").strip()
        fluxo_id = (request.form.get("fluxo_id") or "").strip()
        prioridade = (request.form.get("prioridade") or "0").strip()
        etapa_destino = (request.form.get("etapa_destino") or "").strip()
        tag_id = (request.form.get("tag_id") or "").strip()
        operador_palavras = (request.form.get("operador_palavras") or "any").strip().lower()
        excluir_palavras_texto = (request.form.get("excluir_palavras") or "").strip()
        etapa_cond = (request.form.get("etapa_condicao") or "").strip()
        status_cond = (request.form.get("status_condicao") or "").strip()
        ativa = 1 if request.form.get("ativo") == "on" else 0

        if nome and palavras and (resposta or fluxo_id):
            palavras_lista = []
            for p in palavras.split(","):
                p = p.strip()
                if p:
                    palavras_lista.append(p)

            condicao_json = json.dumps(
                {
                    "palavras_chave": palavras_lista,
                    "operador_palavras": "all" if operador_palavras == "all" else "any",
                    "excluir_palavras": [p.strip() for p in excluir_palavras_texto.split(",") if p.strip()],
                    "etapa": etapa_cond or None,
                    "status_conversa": status_cond or None,
                },
                ensure_ascii=False
            )

            acao_json = json.dumps(
                {
                    "resposta": resposta,
                    "prioridade": int(prioridade) if prioridade.isdigit() else 0,
                    "etapa_destino": etapa_destino or None,
                    "tag_id": int(tag_id) if tag_id.isdigit() else None,
                },
                ensure_ascii=False
            )

            fluxo_id_valor = int(fluxo_id) if fluxo_id.isdigit() else None

            conn.execute(
                """
                UPDATE regras
                SET nome = ?,
                    condicao_json = ?,
                    acao_json = ?,
                    fluxo_id = ?,
                    ativa = ?
                WHERE id = ? AND empresa_id = ?
                """,
                (
                    nome,
                    condicao_json,
                    acao_json,
                    fluxo_id_valor,
                    ativa,
                    regra_id,
                    obter_empresa_id_logada()
                )
            )
            conn.commit()
            registrar_evento("regra_editada", referencia_id=regra_id, valor=nome)

        conn.close()
        return redirect(url_for("regras.regras"))

    conn.close()

    return render_template(
        "editar_regra.html",
        regra=regra,
        palavras_chave=regra["palavras_chave"],
        resposta=regra["resposta"],
        fluxos=fluxos_db,
        tags=tags_db
    )

@regras_bp.route("/regras/<int:regra_id>/toggle", methods=["POST"])
@login_required
def toggle_regra(regra_id):
    conn = get_connection()

    regra = conn.execute(
        """
        SELECT ativa
        FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    ).fetchone()

    if regra:
        novo_status = 0 if regra["ativa"] == 1 else 1
        conn.execute(
            """
            UPDATE regras
            SET ativa = ?
            WHERE id = ? AND empresa_id = ?
            """,
            (novo_status, regra_id, obter_empresa_id_logada())
        )
        conn.commit()
        registrar_evento("regra_toggle", referencia_id=regra_id, valor=str(novo_status))

    conn.close()
    return redirect(url_for("regras.regras"))

@regras_bp.route("/regras/excluir/<int:regra_id>", methods=["POST"])
@login_required
def excluir_regra(regra_id):
    conn = get_connection()
    regra = conn.execute(
        "SELECT nome FROM regras WHERE id = ? AND empresa_id = ?",
        (regra_id, obter_empresa_id_logada())
    ).fetchone()
    conn.execute(
        """
        DELETE FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    if regra:
        registrar_evento("regra_excluida", referencia_id=regra_id, valor=regra["nome"])

    return redirect(url_for("regras.regras"))
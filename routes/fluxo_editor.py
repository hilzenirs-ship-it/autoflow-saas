from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.db import get_connection
from utils.auth import login_required, obter_empresa_id_logada
import json

fluxo_editor_bp = Blueprint('fluxo_editor', __name__)

@fluxo_editor_bp.route("/fluxos/<int:fluxo_id>/editor")
@login_required
def fluxo_editor(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT id, nome, descricao
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        flash("Fluxo não encontrado.", "erro")
        return redirect(url_for("fluxos.fluxos"))

    blocos = conn.execute(
        """
        SELECT id, tipo, titulo, conteudo, opcoes_json, proximo_bloco_id, criado_em
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        ORDER BY criado_em ASC
        """,
        (fluxo_id,)
    ).fetchall()
    conn.close()

    # Converter para formato JSON para o editor
    blocos_json = []
    for b in blocos:
        bloco = dict(b)
        if bloco["opcoes_json"]:
            try:
                bloco["opcoes"] = json.loads(bloco["opcoes_json"])
            except:
                bloco["opcoes"] = {}
        else:
            bloco["opcoes"] = {}
        blocos_json.append(bloco)

    return render_template("fluxo_editor.html", fluxo=fluxo, blocos=json.dumps(blocos_json))

@fluxo_editor_bp.route("/fluxos/<int:fluxo_id>/salvar", methods=["POST"])
@login_required
def salvar_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    data = request.get_json()
    blocos = data.get("blocos", [])

    conn = get_connection()
    # Verificar fluxo
    fluxo = conn.execute(
        "SELECT id FROM fluxos WHERE id = ? AND empresa_id = ?",
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        return jsonify({"erro": "Fluxo não encontrado"}), 404

    # Deletar blocos existentes
    conn.execute("DELETE FROM fluxo_blocos WHERE fluxo_id = ?", (fluxo_id,))

    # Inserir novos blocos
    for bloco in blocos:
        opcoes_json = json.dumps(bloco.get("opcoes", {}))
        conn.execute(
            """
            INSERT INTO fluxo_blocos (fluxo_id, tipo, titulo, conteudo, opcoes_json, proximo_bloco_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                fluxo_id,
                bloco["tipo"],
                bloco.get("titulo", ""),
                bloco.get("conteudo", ""),
                opcoes_json,
                bloco.get("proximo_bloco_id")
            )
        )

    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Fluxo salvo"})

# Rotas adicionais do template
@fluxo_editor_bp.route("/fluxos/<int:fluxo_id>/duplicar", methods=["POST"])
@login_required
def duplicar_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        "SELECT nome, descricao, tipo_gatilho, gatilho_valor FROM fluxos WHERE id = ? AND empresa_id = ?",
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        return redirect(url_for("fluxos.fluxos"))

    novo_nome = f"{fluxo['nome']} (Cópia)"
    cursor = conn.execute(
        "INSERT INTO fluxos (empresa_id, nome, descricao, tipo_gatilho, gatilho_valor) VALUES (?, ?, ?, ?, ?)",
        (empresa_id, novo_nome, fluxo['descricao'], fluxo['tipo_gatilho'], fluxo['gatilho_valor'])
    )
    novo_id = cursor.lastrowid

    # Copiar blocos
    blocos = conn.execute("SELECT tipo, titulo, conteudo, opcoes_json, proximo_bloco_id FROM fluxo_blocos WHERE fluxo_id = ?", (fluxo_id,)).fetchall()
    for b in blocos:
        conn.execute(
            "INSERT INTO fluxo_blocos (fluxo_id, tipo, titulo, conteudo, opcoes_json, proximo_bloco_id) VALUES (?, ?, ?, ?, ?, ?)",
            (novo_id, b['tipo'], b['titulo'], b['conteudo'], b['opcoes_json'], b['proximo_bloco_id'])
        )

    conn.commit()
    conn.close()
    flash("Fluxo duplicado!", "sucesso")
    return redirect(url_for("fluxos.fluxos"))

@fluxo_editor_bp.route("/fluxos/<int:fluxo_id>/toggle", methods=["POST"])
@login_required
def toggle_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        "SELECT ativo FROM fluxos WHERE id = ? AND empresa_id = ?",
        (fluxo_id, empresa_id)
    ).fetchone()
    if fluxo:
        novo_ativo = 0 if fluxo['ativo'] else 1
        conn.execute(
            "UPDATE fluxos SET ativo = ? WHERE id = ? AND empresa_id = ?",
            (novo_ativo, fluxo_id, empresa_id)
        )
        conn.commit()
    conn.close()
    return redirect(url_for("fluxos.fluxos"))

@fluxo_editor_bp.route("/fluxos/<int:fluxo_id>/excluir", methods=["POST"])
@login_required
def excluir_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    conn.execute(
        "DELETE FROM fluxos WHERE id = ? AND empresa_id = ?",
        (fluxo_id, empresa_id)
    )
    conn.commit()
    conn.close()
    flash("Fluxo excluído!", "sucesso")
    return redirect(url_for("fluxos.fluxos"))
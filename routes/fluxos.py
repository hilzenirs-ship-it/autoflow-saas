from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.db import get_connection
from utils.auth import login_required, obter_empresa_id_logada
import json

fluxos_bp = Blueprint('fluxos', __name__)

@fluxos_bp.route("/fluxos")
@login_required
def fluxos():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxos_db = conn.execute(
        """
        SELECT id, nome, descricao, ativo, tipo_gatilho, gatilho_valor, criado_em
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY criado_em DESC
        """,
        (empresa_id,)
    ).fetchall()
    conn.close()
    return render_template("fluxos.html", fluxos=fluxos_db)

@fluxos_bp.route("/fluxos/novo", methods=["GET", "POST"])
@login_required
def novo_fluxo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        tipo_gatilho = (request.form.get("tipo_gatilho") or "").strip()
        gatilho_valor = (request.form.get("gatilho_valor") or "").strip()
        ativo = 1 if request.form.get("ativo") else 0

        if nome:
            empresa_id = obter_empresa_id_logada()
            conn = get_connection()
            conn.execute(
                """
                INSERT INTO fluxos (empresa_id, nome, descricao, ativo, tipo_gatilho, gatilho_valor)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (empresa_id, nome, descricao, ativo, tipo_gatilho, gatilho_valor)
            )
            conn.commit()
            conn.close()
            flash("Fluxo criado com sucesso!", "sucesso")
            return redirect(url_for("fluxos.fluxos"))
        else:
            flash("Nome é obrigatório.", "erro")

    return render_template("novo_fluxo.html")

@fluxos_bp.route("/fluxos/<int:fluxo_id>/editar", methods=["GET", "POST"])
@login_required
def editar_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT id, nome, descricao, ativo, tipo_gatilho, gatilho_valor
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        flash("Fluxo não encontrado.", "erro")
        return redirect(url_for("fluxos.fluxos"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        tipo_gatilho = (request.form.get("tipo_gatilho") or "").strip()
        gatilho_valor = (request.form.get("gatilho_valor") or "").strip()
        ativo = 1 if request.form.get("ativo") else 0

        if nome:
            conn.execute(
                """
                UPDATE fluxos
                SET nome = ?, descricao = ?, ativo = ?, tipo_gatilho = ?, gatilho_valor = ?
                WHERE id = ? AND empresa_id = ?
                """,
                (nome, descricao, ativo, tipo_gatilho, gatilho_valor, fluxo_id, empresa_id)
            )
            conn.commit()
            flash("Fluxo atualizado!", "sucesso")
            return redirect(url_for("fluxos.fluxos"))
        else:
            flash("Nome é obrigatório.", "erro")

    conn.close()
    return render_template("editar_fluxo.html", fluxo=fluxo)

@fluxos_bp.route("/fluxos/<int:fluxo_id>/blocos", methods=["GET"])
@login_required
def blocos_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT id, nome
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
    return render_template("fluxo_blocos.html", fluxo=fluxo, blocos=blocos)

@fluxos_bp.route("/fluxos/<int:fluxo_id>/blocos/novo", methods=["POST"])
@login_required
def novo_bloco(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT id
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        return jsonify({"erro": "Fluxo não encontrado"}), 404

    tipo = (request.form.get("tipo") or "").strip()
    titulo = (request.form.get("titulo") or "").strip()
    conteudo = (request.form.get("conteudo") or "").strip()
    opcoes = request.form.get("opcoes")
    proximo_bloco_id = request.form.get("proximo_bloco_id")

    opcoes_json = json.dumps(opcoes) if opcoes else None
    proximo_id = int(proximo_bloco_id) if proximo_bloco_id and proximo_bloco_id.isdigit() else None

    conn.execute(
        """
        INSERT INTO fluxo_blocos (fluxo_id, tipo, titulo, conteudo, opcoes_json, proximo_bloco_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (fluxo_id, tipo, titulo, conteudo, opcoes_json, proximo_id)
    )
    conn.commit()
    bloco_id = conn.lastrowid
    conn.close()
    return jsonify({"id": bloco_id, "mensagem": "Bloco criado"})

# API para executar fluxo
@fluxos_bp.route("/api/fluxos/<int:fluxo_id>/executar", methods=["POST"])
@login_required
def executar_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    data = request.get_json()
    conversa_id = data.get("conversa_id")
    resposta_cliente = data.get("resposta_cliente")

    if not conversa_id:
        return jsonify({"erro": "conversa_id obrigatório"}), 400

    conn = get_connection()
    # Verificar se fluxo pertence à empresa
    fluxo = conn.execute(
        """
        SELECT id, nome
        FROM fluxos
        WHERE id = ? AND empresa_id = ? AND ativo = 1
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    if not fluxo:
        conn.close()
        return jsonify({"erro": "Fluxo não encontrado ou inativo"}), 404

    # Verificar conversa
    conversa = conn.execute(
        """
        SELECT id, bloco_atual_id, contexto_json
        FROM conversas
        WHERE id = ? AND empresa_id = ?
        """,
        (conversa_id, empresa_id)
    ).fetchone()
    if not conversa:
        conn.close()
        return jsonify({"erro": "Conversa não encontrada"}), 404

    bloco_id = conversa["bloco_atual_id"]
    contexto = {}
    if conversa["contexto_json"]:
        try:
            contexto = json.loads(conversa["contexto_json"])
        except:
            contexto = {}

    # Se há resposta do cliente, decidir próximo bloco
    if resposta_cliente and bloco_id:
        bloco_atual = conn.execute(
            """
            SELECT tipo, opcoes_json, proximo_bloco_id
            FROM fluxo_blocos
            WHERE id = ?
            """,
            (bloco_id,)
        ).fetchone()
        if bloco_atual and bloco_atual["tipo"] == "pergunta":
            opcoes = bloco_atual["opcoes_json"]
            if opcoes:
                try:
                    opcoes_dict = json.loads(opcoes)
                    # Simples: se resposta matches uma opção, ir para bloco específico
                    for opcao, bloco_destino in opcoes_dict.items():
                        if opcao.lower() in resposta_cliente.lower():
                            bloco_id = bloco_destino
                            break
                    else:
                        bloco_id = bloco_atual["proximo_bloco_id"]  # default
                except:
                    bloco_id = bloco_atual["proximo_bloco_id"]
            else:
                bloco_id = bloco_atual["proximo_bloco_id"]
        else:
            bloco_id = bloco_atual["proximo_bloco_id"] if bloco_atual else None

    # Se não há bloco atual, iniciar
    if not bloco_id:
        primeiro_bloco = conn.execute(
            """
            SELECT id
            FROM fluxo_blocos
            WHERE fluxo_id = ?
            ORDER BY criado_em ASC
            LIMIT 1
            """,
            (fluxo_id,)
        ).fetchone()
        if primeiro_bloco:
            bloco_id = primeiro_bloco["id"]

    if bloco_id:
        bloco = conn.execute(
            """
            SELECT tipo, titulo, conteudo, opcoes_json, proximo_bloco_id
            FROM fluxo_blocos
            WHERE id = ?
            """,
            (bloco_id,)
        ).fetchone()
        if bloco:
            # Atualizar conversa
            conn.execute(
                """
                UPDATE conversas
                SET fluxo_id_ativo = ?, bloco_atual_id = ?, bot_ativo = 1, contexto_json = ?, atualizada_em = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (fluxo_id, bloco_id, json.dumps(contexto), conversa_id)
            )
            conn.commit()

            resposta = bloco["conteudo"]
            tipo = bloco["tipo"]
            opcoes = None
            if bloco["opcoes_json"]:
                try:
                    opcoes = json.loads(bloco["opcoes_json"])
                except:
                    opcoes = None

            conn.close()
            return jsonify({
                "resposta": resposta,
                "tipo": tipo,
                "opcoes": opcoes,
                "titulo": bloco["titulo"]
            })

    conn.close()
    return jsonify({"resposta": "Fluxo concluído"})
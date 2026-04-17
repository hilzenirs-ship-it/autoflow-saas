# =========================================================
# ⚠️ ARQUIVO LEGADO - NÃO UTILIZAR
# =========================================================
# Este módulo usa schema antigo (etapa_atual, created_at)
# e NÃO é compatível com o sistema atual.
# NÃO registrar este blueprint no app principal.
# =========================================================

from flask import Blueprint, jsonify, request
from utils.db import get_connection
from utils.auth import login_required, obter_empresa_id_logada
from services.regras_service import buscar_resposta_por_regras
import json

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.before_request
def bloquear_api_legada():
    return {"erro": "API legada desativada"}, 410

@api_bp.route('/v1/conversas', methods=['GET'])
@login_required
def get_conversas():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    conversas = conn.execute(
        """
        SELECT id, contato_id, status, etapa_atual, created_at
        FROM conversas
        WHERE empresa_id = ?
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (empresa_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(c) for c in conversas])

@api_bp.route('/v1/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    results = conn.execute(
        """
        SELECT 'conversa' as type, c.id, c.etapa_atual as title, m.conteudo as content
        FROM conversas c
        JOIN mensagens m ON m.conversa_id = c.id
        WHERE c.empresa_id = ? AND m.conteudo LIKE ?
        UNION
        SELECT 'contato' as type, id, nome as title, telefone as content
        FROM contatos
        WHERE empresa_id = ? AND (nome LIKE ? OR telefone LIKE ?)
        LIMIT 20
        """,
        (empresa_id, f'%{query}%', empresa_id, f'%{query}%', f'%{query}%')
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in results])

@api_bp.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    from twilio.twiml.messaging_response import MessagingResponse
    from utils.whatsapp import processar_mensagem_whatsapp

    # Verificar se é Twilio
    if request.form.get('From'):
        # Mensagem Twilio
        from_number = request.form.get('From')
        body = request.form.get('Body')
        if from_number and body:
            processar_mensagem_whatsapp(from_number, body)

        resp = MessagingResponse()
        return str(resp)

    # Fallback para simulação
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data'}), 400

    telefone = data.get('from')
    mensagem = data.get('body')

    if not telefone or not mensagem:
        return jsonify({'status': 'error', 'message': 'Missing fields'}), 400

    resposta = processar_mensagem_whatsapp(f'whatsapp:{telefone}', mensagem)

    return jsonify({'status': 'ok', 'response': resposta}), 200

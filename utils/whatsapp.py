from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from config import Config
import requests
from utils.db import get_connection
from services.regras_service import buscar_resposta_por_regras
from routes.fluxos import executar_fluxo_api  # Assumindo que criaremos

client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

def enviar_mensagem_whatsapp(to, body):
    """Envia mensagem via Twilio WhatsApp"""
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_PHONE_NUMBER:
        print(f"Simulando envio para {to}: {body}")
        return True

    try:
        message = client.messages.create(
            from_=f'whatsapp:{Config.TWILIO_PHONE_NUMBER}',
            body=body,
            to=f'whatsapp:{to}'
        )
        return message.sid
    except Exception as e:
        print(f"Erro ao enviar WhatsApp: {e}")
        return False

def processar_mensagem_whatsapp(from_number, body):
    """Processa mensagem recebida do WhatsApp"""
    # Limpar número
    telefone = from_number.replace('whatsapp:', '').replace('+', '')

    conn = get_connection()

    # Buscar ou criar contato
    contato = conn.execute(
        "SELECT id, empresa_id FROM contatos WHERE telefone = ?",
        (telefone,)
    ).fetchone()

    if not contato:
        # Assumir empresa padrão ou primeira, mas como multiempresa, talvez não criar sem empresa
        # Para demo, criar com empresa_id = 1 se existir
        empresa = conn.execute("SELECT id FROM empresas LIMIT 1").fetchone()
        if empresa:
            conn.execute(
                "INSERT INTO contatos (empresa_id, telefone, origem) VALUES (?, ?, 'whatsapp')",
                (empresa["id"], telefone)
            )
            contato_id = conn.lastrowid
            empresa_id = empresa["id"]
        else:
            conn.close()
            return "Sistema não configurado."
    else:
        contato_id = contato["id"]
        empresa_id = contato["empresa_id"]

    # Buscar ou criar conversa
    conversa = conn.execute(
        "SELECT id FROM conversas WHERE contato_id = ? AND empresa_id = ?",
        (contato_id, empresa_id)
    ).fetchone()

    if not conversa:
        conn.execute(
            "INSERT INTO conversas (empresa_id, contato_id) VALUES (?, ?)",
            (empresa_id, contato_id)
        )
        conversa_id = conn.lastrowid
    else:
        conversa_id = conversa["id"]

    conn.commit()
    conn.close()

    # Processar com regras ou fluxo
    resposta = processar_mensagem_bot(conversa_id, body)

    # Enviar resposta
    if resposta:
        enviar_mensagem_whatsapp(telefone, resposta)

    return resposta

def processar_mensagem_bot(conversa_id, mensagem):
    """Processa mensagem com bot (regras ou fluxo)"""
    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT c.*, f.tipo_gatilho, f.gatilho_valor
        FROM conversas c
        LEFT JOIN fluxos f ON f.id = c.fluxo_id_ativo
        WHERE c.id = ?
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if not conversa:
        return "Erro interno."

    # Se há fluxo ativo, executar fluxo
    if conversa["fluxo_id_ativo"] and conversa["bot_ativo"]:
        # Chamar execução de fluxo
        # Como é API, simular
        from routes.fluxos import executar_fluxo_api
        # Mas como é interno, criar função
        resposta = executar_fluxo_interno(conversa["fluxo_id_ativo"], conversa_id, mensagem)
        if resposta:
            return resposta

    # Senão, usar regras
    resposta, regra_id = buscar_resposta_por_regras(mensagem, conversa_id=conversa_id)
    if resposta:
        return resposta

    # Fallback IA
    return gerar_resposta_ia(mensagem, conversa_id)

def executar_fluxo_interno(fluxo_id, conversa_id, resposta_cliente=None):
    """Executa fluxo internamente"""
    # Similar ao API, mas sem request
    # Implementar lógica aqui ou chamar a função
    # Por simplicidade, placeholder
    return "Fluxo executado."

def gerar_resposta_ia(mensagem, conversa_id):
    """Gera resposta com IA"""
    # Usar OpenAI como antes
    # Placeholder
    return "Resposta da IA."
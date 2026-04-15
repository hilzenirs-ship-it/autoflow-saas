import json
import unicodedata
from typing import List, Dict, Tuple, Optional, Any
from utils.db import get_connection
from utils.auth import obter_empresa_id_logada
from utils.cache import cache

def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    return unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('ascii').lower().strip()

def extrair_palavras_chave(condicao_json):
    if not condicao_json:
        return []

    try:
        dados = json.loads(condicao_json)
    except Exception:
        return []

    palavras = dados.get("palavras_chave", [])
    if isinstance(palavras, list):
        resultado = []
        for p in palavras:
            p = str(p).strip()
            if p:
                resultado.append(p)
        return resultado

    return []

def extrair_resposta_acao(acao_json):
    if not acao_json:
        return None

    try:
        dados = json.loads(acao_json)
    except Exception:
        return None

    resposta = dados.get("resposta")
    if resposta:
        return str(resposta).strip()

    return None

def extrair_acoes_regra(acao_json):
    if not acao_json:
        return {}
    try:
        dados = json.loads(acao_json)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}

def extrair_condicoes_regra(condicao_json):
    if not condicao_json:
        return {}
    try:
        dados = json.loads(condicao_json)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}

def buscar_etapa_conversa(conversa_id):
    if not conversa_id:
        return ""
    conn = get_connection()
    conversa = conn.execute("SELECT etapa_atual FROM conversas WHERE id = ?", (conversa_id,)).fetchone()
    conn.close()
    return (conversa or {}).get("etapa_atual", "")

def atualizar_etapa_conversa(conversa_id, etapa):
    if not conversa_id or not etapa:
        return
    conn = get_connection()
    conn.execute("UPDATE conversas SET etapa_atual = ? WHERE id = ?", (etapa, conversa_id))
    conn.commit()
    conn.close()

def registrar_evento(tipo, referencia_id=None, valor=None):
    empresa_id = obter_empresa_id_logada()
    if not empresa_id:
        return
    conn = get_connection()
    conn.execute(
        "INSERT INTO metricas_eventos (empresa_id, tipo, referencia_id, valor) VALUES (?, ?, ?, ?)",
        (empresa_id, tipo, referencia_id, valor)
    )
    conn.commit()
    conn.close()

def regra_atende_contexto(regra, conversa_id=None):
    if not conversa_id:
        return True
    condicoes = extrair_condicoes_regra(regra["condicao_json"])
    etapa_cond = condicoes.get("etapa")
    etapas_necessarias = etapa_cond if isinstance(etapa_cond, list) else ([etapa_cond] if etapa_cond else [])
    etapas_necessarias = [str(e).strip() for e in etapas_necessarias if str(e).strip()]
    etapa_atual = buscar_etapa_conversa(conversa_id)
    if etapas_necessarias and etapa_atual not in etapas_necessarias:
        return False
    status_cond = condicoes.get("status_conversa")
    status_necessarios = status_cond if isinstance(status_cond, list) else ([status_cond] if status_cond else [])
    status_necessarios = [str(s).strip() for s in status_necessarios if str(s).strip()]
    if status_necessarios:
        conn = get_connection()
        conversa = conn.execute("SELECT status FROM conversas WHERE id = ?", (conversa_id,)).fetchone()
        conn.close()
        if not conversa or conversa["status"] not in status_necessarios:
            return False
    return True

def montar_regra_para_template(regra_row):
    regra = dict(regra_row)

    palavras_lista = extrair_palavras_chave(regra.get("condicao_json"))
    resposta_texto = extrair_resposta_acao(regra.get("acao_json")) or ""

    regra["palavras_chave"] = ", ".join(palavras_lista)
    regra["resposta"] = resposta_texto
    regra["ativo"] = regra.get("ativa", 0)
    acoes = extrair_acoes_regra(regra.get("acao_json"))
    regra["prioridade"] = int(acoes.get("prioridade", 0) or 0)
    regra["etapa_destino"] = (acoes.get("etapa_destino") or "").strip()
    regra["tag_id"] = acoes.get("tag_id")

    return regra

@cache.memoize(timeout=300)
def buscar_regras_ativas(empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return []

    conn = get_connection()
    regras = conn.execute(
        """
        SELECT *
        FROM regras
        WHERE empresa_id = ? AND ativa = 1
        ORDER BY id ASC
        """,
        (empresa_id,)
    ).fetchall()
    conn.close()
    return regras

def pontuar_palavra_chave(palavra):
    palavra_normalizada = normalizar_texto(palavra)
    tamanho = len(palavra_normalizada)

    bonus_espaco = 2 if " " in palavra_normalizada else 0
    bonus_especificidade = 1 if tamanho >= 8 else 0

    return tamanho + bonus_espaco + bonus_especificidade

def pontuacao_final_regra(regra, palavra):
    acoes = extrair_acoes_regra(regra["acao_json"])
    prioridade = int(acoes.get("prioridade", 0) or 0)
    return pontuar_palavra_chave(palavra) + (prioridade * 100)

def buscar_melhor_regra(mensagem_cliente: str, empresa_id: Optional[int] = None, conversa_id: Optional[int] = None) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
    empresa_id = empresa_id or obter_empresa_id_logada()
    texto_original = (mensagem_cliente or "").strip()
    texto = normalizar_texto(texto_original)

    if not texto or not empresa_id:
        return None

    regras = buscar_regras_ativas(empresa_id)

    melhor_pontuacao = -1
    melhor_regra = None

    for regra in regras:
        if regra["tipo_regra"] != "palavra_chave":
            continue
        if not regra_atende_contexto(regra, conversa_id=conversa_id):
            continue

        condicoes = extrair_condicoes_regra(regra["condicao_json"])
        palavras = extrair_palavras_chave(regra["condicao_json"])
        operador_palavras = (condicoes.get("operador_palavras") or "any").strip().lower()
        excluir_palavras = condicoes.get("excluir_palavras", [])
        if not isinstance(excluir_palavras, list):
            excluir_palavras = []
        if not palavras:
            continue

        bloqueada = False
        for bloqueio in excluir_palavras:
            palavra_bloqueio = normalizar_texto(str(bloqueio).strip())
            if palavra_bloqueio and palavra_bloqueio in texto:
                bloqueada = True
                break
        if bloqueada:
            continue

        matches = []

        for palavra in palavras:
            palavra_limpa = palavra.strip()
            palavra_normalizada = normalizar_texto(palavra_limpa)

            if not palavra_normalizada:
                continue

            if palavra_normalizada in texto:
                matches.append(palavra_limpa)

        if operador_palavras == "all" and len(matches) < len([p for p in palavras if str(p).strip()]):
            continue
        if operador_palavras != "all" and not matches:
            continue

        palavra_referencia = max(matches, key=lambda p: pontuar_palavra_chave(p))
        pontuacao = pontuacao_final_regra(regra, palavra_referencia)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_regra = regra
        elif pontuacao == melhor_pontuacao and melhor_regra is not None and regra["id"] < melhor_regra["id"]:
            melhor_regra = regra

    return melhor_regra

def aplicar_acoes_regra(conversa_id, regra):
    if not conversa_id or not regra:
        return
    acoes = extrair_acoes_regra(regra["acao_json"])
    etapa_destino = (acoes.get("etapa_destino") or "").strip()
    if etapa_destino:
        atualizar_etapa_conversa(conversa_id, etapa_destino)
    tag_id = acoes.get("tag_id")
    if tag_id:
        conn = get_connection()
        contato = conn.execute("SELECT contato_id FROM conversas WHERE id = ?", (conversa_id,)).fetchone()
        if contato:
            ja = conn.execute(
                "SELECT id FROM contato_tags WHERE contato_id = ? AND tag_id = ?",
                (contato["contato_id"], tag_id)
            ).fetchone()
            if not ja:
                conn.execute(
                    "INSERT INTO contato_tags (contato_id, tag_id) VALUES (?, ?)",
                    (contato["contato_id"], tag_id)
                )
                conn.commit()
        conn.close()

def buscar_resposta_por_regras(mensagem_cliente, empresa_id=None, conversa_id=None):
    melhor_regra = buscar_melhor_regra(mensagem_cliente, empresa_id=empresa_id, conversa_id=conversa_id)
    if not melhor_regra:
        return None, None
    resposta = extrair_resposta_acao(melhor_regra["acao_json"])
    if conversa_id:
        aplicar_acoes_regra(conversa_id, melhor_regra)
        registrar_evento("regra_acionada", referencia_id=melhor_regra["id"], valor=melhor_regra["nome"])
    return resposta, melhor_regra["id"]

def buscar_fluxo_por_regra(mensagem_cliente, empresa_id=None, conversa_id=None):
    melhor_regra = buscar_melhor_regra(mensagem_cliente, empresa_id=empresa_id, conversa_id=conversa_id)
    if not melhor_regra or not melhor_regra["fluxo_id"]:
        return None, None
    if conversa_id:
        aplicar_acoes_regra(conversa_id, melhor_regra)
        registrar_evento("regra_fluxo_acionada", referencia_id=melhor_regra["id"], valor=melhor_regra["nome"])
    return melhor_regra["fluxo_id"], melhor_regra["id"]
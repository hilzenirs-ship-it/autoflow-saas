"""
Funções de normalização de dados para produção.
"""
import re


NOMES_CONTATO_INVALIDOS = {
    "none",
    "null",
    "undefined",
    "nan",
    "-",
    "--",
}

NOMES_CONTATO_GENERICOS = {
    "contato sem nome",
    "sem nome",
    "cliente",
    "cliente whatsapp",
    "cliente instagram",
}


def normalizar_telefone(telefone):
    """
    Normaliza telefone para formato E.164 (RFC 3966).
    
    Aceita:
    - +55 11 99999-9999
    - +5511999999999
    - 11 99999-9999
    - 11999999999
    - (11) 99999-9999
    
    Retorna:
    - +5511999999999 (se válido)
    - None (se inválido)
    
    Regras:
    - Telefones brasileiros: +55 + 2 dígitos de área + 8-9 dígitos de número
    - Remove espaços, hífens, parênteses
    - Aceita + no início
    - Valida length corretamente
    """
    if not telefone:
        return None
    
    # Converter para string e remover whitespace leading/trailing
    telefone = str(telefone).strip()
    
    if not telefone:
        return None
    
    # Remover caracteres comuns de formatação
    telefone_limpo = re.sub(r'[\s\-\(\)\.]+', '', telefone)
    
    # Se vazio após limpeza, rejeitar
    if not telefone_limpo:
        return None
    
    # Se começa com +, validar como já formatado internacionalmente
    if telefone_limpo.startswith('+'):
        numero_limpo = telefone_limpo[1:]
    else:
        numero_limpo = telefone_limpo
    
    # Validar que contém apenas dígitos
    if not numero_limpo.isdigit():
        return None
    
    # Heurística brasileira: assumir +55 se tem 10-11 dígitos
    # (padrão 11999999999 ou 8532999999)
    if len(numero_limpo) in [10, 11] and not telefone_limpo.startswith('+'):
        # Pode ser brasileiro sem +55
        if len(numero_limpo) < 10:
            return None
        # Adicionar +55
        numero_limpo = '55' + numero_limpo
    
    # Validar: deve ter entre 10 e 15 dígitos (padrão E.164)
    if len(numero_limpo) < 10 or len(numero_limpo) > 15:
        return None
    
    # Validar: se começar com 55 (Brasil), deve ter 12-13 dígitos total
    if numero_limpo.startswith('55'):
        if len(numero_limpo) not in [12, 13]:
            return None
    
    # Retornar em formato E.164
    return f"+{numero_limpo}"


def validar_telefone(telefone):
    """
    Valida se telefone é válido após normalização.
    Retorna True/False.
    """
    return normalizar_telefone(telefone) is not None


def limpar_nome_contato(nome):
    """
    Limpa nome do contato para armazenamento seguro.
    - Remove whitespace excessivo
    - Rejeita strings vazias
    - Limita a 255 caracteres
    """
    if nome is None:
        return None
    
    nome = str(nome).strip()
    
    if not nome or len(nome) == 0:
        return None
    
    # Remover espaços múltiplos
    nome = re.sub(r'\s+', ' ', nome)
    if nome.lower() in NOMES_CONTATO_INVALIDOS:
        return None
    
    # Limitar tamanho
    nome = nome[:255]
    
    return nome if nome else None


def nome_contato_generico(nome):
    nome_limpo = limpar_nome_contato(nome)
    if not nome_limpo:
        return True

    nome_base = nome_limpo.lower()
    if nome_base in NOMES_CONTATO_GENERICOS:
        return True

    if normalizar_telefone(nome_limpo):
        return True

    somente_digitos = re.sub(r'\D+', '', nome_limpo)
    return bool(somente_digitos and somente_digitos == nome_limpo and len(somente_digitos) >= 8)


def nome_contato_melhor(novo_nome, nome_atual=None):
    novo_limpo = limpar_nome_contato(novo_nome)
    if not novo_limpo or nome_contato_generico(novo_limpo):
        return None

    atual_limpo = limpar_nome_contato(nome_atual)
    if not atual_limpo or nome_contato_generico(atual_limpo):
        return novo_limpo

    return None


def fallback_nome_contato(canal=None, telefone=None):
    canal = (canal or "").strip().lower()
    telefone_limpo = normalizar_telefone(telefone) if telefone else None

    if canal == "whatsapp":
        return "Cliente WhatsApp"
    if canal == "instagram":
        return "Cliente Instagram"
    if telefone_limpo:
        return telefone_limpo
    return "Cliente"

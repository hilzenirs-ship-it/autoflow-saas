from flask import flash, has_request_context

from utils.db import get_connection


RECURSOS_LIMITADOS = {
    "contatos": ("limite_contatos", "contatos"),
    "mensagens": ("limite_mensagens", "mensagens"),
    "atendentes": ("limite_atendentes", "atendentes"),
    "integracoes": ("limite_integracoes", "integracoes"),
}

# Estados possíveis do ciclo de vida SaaS
ESTADOS_SAAS = {
    "trial": {"label": "Trial", "ativo": True, "pago": False},
    "ativo": {"label": "Ativo", "ativo": True, "pago": True},
    "pendente": {"label": "Pagamento Pendente", "ativo": True, "pago": False},
    "expirado": {"label": "Expirado", "ativo": False, "pago": False},
    "rejeitado": {"label": "Pagamento Rejeitado", "ativo": True, "pago": False},
    "cancelado": {"label": "Cancelado", "ativo": False, "pago": False},
    "reembolsado": {"label": "Reembolsado", "ativo": True, "pago": False},
    "chargeback": {"label": "Chargeback", "ativo": False, "pago": False},
    "bloqueado": {"label": "Bloqueado", "ativo": False, "pago": False},
}


def _valor_limite(row, coluna, fallback=None):
    try:
        valor = row[coluna]
    except (KeyError, IndexError):
        valor = fallback
    return valor


def buscar_limites_empresa(empresa_id, conn=None):
    if not empresa_id:
        return {}

    deve_fechar = conn is None
    conn = conn or get_connection()
    garantir_limites_empresa(empresa_id, conn=conn)
    limites = conn.execute(
        """
        SELECT el.*, ps.nome AS plano_nome, ps.descricao AS plano_descricao
        FROM empresa_limites el
        LEFT JOIN planos_saas ps ON ps.id = el.plano_id
        WHERE el.empresa_id = ?
        LIMIT 1
        """,
        (empresa_id,)
    ).fetchone()
    if deve_fechar:
        conn.commit()
        conn.close()
    return dict(limites) if limites else {}


def garantir_limites_empresa(empresa_id, conn=None):
    if not empresa_id:
        return None

    deve_fechar = conn is None
    conn = conn or get_connection()
    existente = conn.execute(
        "SELECT id FROM empresa_limites WHERE empresa_id = ? LIMIT 1",
        (empresa_id,)
    ).fetchone()
    if existente:
        if deve_fechar:
            conn.close()
        return existente["id"]

    plano_starter = conn.execute(
        """
        SELECT id, limite_contatos, limite_conversas, limite_mensagens,
               limite_atendentes, limite_integracoes
        FROM planos_saas
        WHERE nome = 'Starter'
        LIMIT 1
        """
    ).fetchone()
    cursor = conn.execute(
        """
        INSERT INTO empresa_limites (
            empresa_id, plano_id, limite_contatos, limite_conversas,
            limite_mensagens, limite_atendentes, limite_integracoes, status_ciclo_vida
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'trial')
        """,
        (
            empresa_id,
            plano_starter["id"] if plano_starter else None,
            plano_starter["limite_contatos"] if plano_starter else 500,
            plano_starter["limite_conversas"] if plano_starter else 500,
            plano_starter["limite_mensagens"] if plano_starter else 5000,
            plano_starter["limite_atendentes"] if plano_starter else 3,
            plano_starter["limite_integracoes"] if plano_starter else 1,
        )
    )
    if deve_fechar:
        conn.commit()
        conn.close()
    return cursor.lastrowid


def contar_uso_empresa(empresa_id, conn=None):
    if not empresa_id:
        return {"contatos": 0, "mensagens": 0, "atendentes": 0, "integracoes": 0}

    deve_fechar = conn is None
    conn = conn or get_connection()
    uso = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM contatos WHERE empresa_id = ?) AS contatos,
            (
                SELECT COUNT(*)
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.empresa_id = ?
            ) AS mensagens,
            (
                SELECT COUNT(*)
                FROM empresa_membros
                WHERE empresa_id = ? AND ativo = 1
            ) AS atendentes,
            (
                SELECT COUNT(*)
                FROM canal_integracoes
                WHERE empresa_id = ? AND status != 'pausado'
            ) AS integracoes
        """,
        (empresa_id, empresa_id, empresa_id, empresa_id)
    ).fetchone()
    if deve_fechar:
        conn.close()

    return {
        "contatos": uso["contatos"] or 0,
        "mensagens": uso["mensagens"] or 0,
        "atendentes": uso["atendentes"] or 0,
        "integracoes": uso["integracoes"] or 0,
    }


def montar_status_limites(empresa_id, conn=None):
    deve_fechar = conn is None
    conn = conn or get_connection()
    limites = buscar_limites_empresa(empresa_id, conn=conn)
    uso = contar_uso_empresa(empresa_id, conn=conn)
    if deve_fechar:
        conn.close()

    status = {
        "plano_nome": limites.get("plano_nome") or "Starter",
        "status": limites.get("status") or "ativo",
        "recursos": {},
        "avisos": [],
    }

    for recurso, (coluna_limite, label) in RECURSOS_LIMITADOS.items():
        limite = _valor_limite(limites, coluna_limite)
        usado = uso.get(recurso, 0)
        percentual = None
        perto_limite = False
        excedido = False
        if limite is not None:
            try:
                limite_int = int(limite)
            except (TypeError, ValueError):
                limite_int = None
            limite = limite_int
            if limite_int is not None and limite_int > 0:
                percentual = round((usado / limite_int) * 100)
                perto_limite = percentual >= 80 and usado < limite_int
                excedido = usado >= limite_int

        item = {
            "label": label,
            "usado": usado,
            "limite": limite,
            "percentual": percentual,
            "perto_limite": perto_limite,
            "excedido": excedido,
        }
        status["recursos"][recurso] = item
        if excedido:
            status["avisos"].append(f"Limite de {label} atingido.")
        elif perto_limite:
            status["avisos"].append(f"Uso de {label} acima de 80%.")

    return status


def verificar_limite_recurso(empresa_id, recurso, incremento=1, conn=None):
    if recurso not in RECURSOS_LIMITADOS:
        return True, None

    deve_fechar = conn is None
    conn = conn or get_connection()
    limites = buscar_limites_empresa(empresa_id, conn=conn)
    uso = contar_uso_empresa(empresa_id, conn=conn)
    if deve_fechar:
        conn.close()

    coluna_limite, label = RECURSOS_LIMITADOS[recurso]
    limite = _valor_limite(limites, coluna_limite)
    if limite is None:
        return True, None

    try:
        limite = int(limite)
    except (TypeError, ValueError):
        return True, None

    if limite <= 0:
        return True, None

    usado = uso.get(recurso, 0)
    if usado + max(1, int(incremento or 1)) > limite:
        return False, f"Limite de {label} atingido para o plano atual."

    return True, None


def flash_limite_bloqueado(mensagem):
    if mensagem and has_request_context():
        flash(mensagem, "erro")


def obter_estado_saas(empresa_id, conn=None):
    """
    Retorna o estado atual do SaaS para a empresa.
    """
    if not empresa_id:
        return {"status_ciclo_vida": "trial", "status_pagamento": "trial", "ativo": True, "pago": False}
    
    deve_fechar = conn is None
    conn = conn or get_connection()
    
    limites = conn.execute(
        "SELECT status_ciclo_vida, status_pagamento FROM empresa_limites WHERE empresa_id = ? LIMIT 1",
        (empresa_id,)
    ).fetchone()
    
    if deve_fechar:
        conn.close()
    
    if not limites:
        return {"status_ciclo_vida": "trial", "status_pagamento": "trial", "ativo": True, "pago": False}
    
    status_ciclo = limites["status_ciclo_vida"] or "trial"
    status_pagamento = limites["status_pagamento"] or "trial"
    
    estado_info = ESTADOS_SAAS.get(status_ciclo, {"label": "Desconhecido", "ativo": False, "pago": False})
    
    return {
        "status_ciclo_vida": status_ciclo,
        "status_pagamento": status_pagamento,
        "ativo": estado_info["ativo"],
        "pago": estado_info["pago"],
        "label": estado_info["label"]
    }


def verificar_acesso_saas(empresa_id, conn=None):
    """
    Verifica se a empresa tem acesso ativo ao SaaS.
    Retorna True se ativo, False se bloqueado/expirado.
    """
    estado = obter_estado_saas(empresa_id, conn=conn)
    return estado["ativo"]


def transicionar_estado_saas(empresa_id, novo_estado, motivo=None, conn=None):
    """
    Transiciona o estado SaaS da empresa.
    Registra audit trail.
    """
    if novo_estado not in ESTADOS_SAAS:
        return False
    
    deve_fechar = conn is None
    conn = conn or get_connection()
    
    # Buscar estado atual
    estado_atual = obter_estado_saas(empresa_id, conn=conn)
    
    # Atualizar estado
    conn.execute(
        """
        UPDATE empresa_limites 
        SET status_ciclo_vida = ?, status_pagamento = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE empresa_id = ?
        """,
        (novo_estado, novo_estado, empresa_id)
    )
    
    # Registrar transição
    from app import registrar_evento
    registrar_evento(
        "saas_estado_transicao",
        referencia_id=empresa_id,
        valor={
            "estado_anterior": estado_atual["status_ciclo_vida"],
            "estado_novo": novo_estado,
            "motivo": motivo,
            "timestamp": datetime.now().isoformat()
        },
        empresa_id=empresa_id
    )
    
    if deve_fechar:
        conn.commit()
        conn.close()
    
    return True


def verificar_e_aplicar_degradacao_automatica():
    """
    Verifica pagamentos expirados e aplica degradação automática.
    Deve ser chamado periodicamente (ex: daily job).
    """
    conn = get_connection()
    
    # Encontrar empresas com pagamentos expirados
    expirados = conn.execute(
        """
        SELECT empresa_id, payment_id_externo, data_proximo_retry
        FROM empresa_limites 
        WHERE status_ciclo_vida = 'pendente' 
          AND data_proximo_retry IS NOT NULL 
          AND data_proximo_retry < CURRENT_TIMESTAMP
        """
    ).fetchall()
    
    for empresa in expirados:
        # Transicionar para expirado
        transicionar_estado_saas(
            empresa["empresa_id"], 
            "expirado", 
            f"Pagamento {empresa['payment_id_externo']} expirado após retry",
            conn=conn
        )
    
    conn.commit()
    conn.close()

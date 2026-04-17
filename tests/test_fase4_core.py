import json
from datetime import datetime, timedelta

from tests.conftest import login_session


def criar_fluxo_multipla_escolha(app_module, empresa_id):
    conn = app_module.get_connection()
    cursor = conn.execute(
        "INSERT INTO fluxos (empresa_id, nome, descricao, ativo) VALUES (?, ?, ?, 1)",
        (empresa_id, "Fluxo teste", "Fluxo com menu"),
    )
    fluxo_id = cursor.lastrowid
    cursor = conn.execute(
        """
        INSERT INTO fluxo_blocos (fluxo_id, tipo_bloco, titulo, conteudo, ordem, config_json)
        VALUES (?, 'multipla_escolha', 'Menu', 'Escolha: 1 - Comprar', 1, ?)
        """,
        (fluxo_id, json.dumps({})),
    )
    bloco_menu_id = cursor.lastrowid
    cursor = conn.execute(
        """
        INSERT INTO fluxo_blocos (fluxo_id, tipo_bloco, titulo, conteudo, ordem, config_json)
        VALUES (?, 'mensagem', 'Compra', 'Vamos comprar.', 2, ?)
        """,
        (fluxo_id, json.dumps({})),
    )
    bloco_compra_id = cursor.lastrowid
    conn.execute(
        "UPDATE fluxo_blocos SET config_json = ? WHERE id = ?",
        (
            json.dumps({"opcoes": [{"gatilho": "1", "proximo_bloco_id": bloco_compra_id}]}),
            bloco_menu_id,
        ),
    )
    conn.commit()
    conn.close()
    return fluxo_id, bloco_menu_id, bloco_compra_id


def test_buscar_melhor_regra_respeita_empresa_da_conversa(app_module, seed_base):
    empresa_a = seed_base("regra_a")
    empresa_b = seed_base("regra_b")
    conn = app_module.get_connection()
    conn.execute(
        """
        INSERT INTO regras (empresa_id, nome, tipo_regra, condicao_json, acao_json, ativa)
        VALUES (?, 'Regra A', 'palavra_chave', ?, ?, 1)
        """,
        (
            empresa_a["empresa_id"],
            json.dumps({"palavras_chave": ["preco"]}),
            json.dumps({"resposta": "Resposta A", "prioridade": 1}),
        ),
    )
    conn.execute(
        """
        INSERT INTO regras (empresa_id, nome, tipo_regra, condicao_json, acao_json, ativa)
        VALUES (?, 'Regra B', 'palavra_chave', ?, ?, 1)
        """,
        (
            empresa_b["empresa_id"],
            json.dumps({"palavras_chave": ["preco"]}),
            json.dumps({"resposta": "Resposta B", "prioridade": 99}),
        ),
    )
    conn.commit()
    conn.close()

    regra = app_module.buscar_melhor_regra("qual o preco?", conversa_id=empresa_a["conversa_id"])

    assert regra is not None
    assert regra["nome"] == "Regra A"
    assert regra["empresa_id"] == empresa_a["empresa_id"]


def test_fluxo_multipla_escolha_avanca_para_bloco_correto(app_module, seed_base):
    base = seed_base("fluxo_multi")
    fluxo_id, bloco_menu_id, _ = criar_fluxo_multipla_escolha(app_module, base["empresa_id"])
    conn = app_module.get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET fluxo_id_ativo = ?, bloco_atual_id = ?, etapa = 'fluxo'
        WHERE id = ?
        """,
        (fluxo_id, bloco_menu_id, base["conversa_id"]),
    )
    conn.commit()
    conn.close()

    resposta = app_module.processar_fluxo_conversa(base["conversa_id"], "1")

    assert resposta == "Vamos comprar."


def test_duplicar_fluxo_remapeia_proximos_blocos(client, app_module, seed_base):
    base = seed_base("dup_fluxo")
    fluxo_id, _, bloco_compra_id = criar_fluxo_multipla_escolha(app_module, base["empresa_id"])
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    resposta = client.post(f"/fluxos/{fluxo_id}/duplicar")

    assert resposta.status_code == 302
    conn = app_module.get_connection()
    novo_fluxo = conn.execute(
        "SELECT id FROM fluxos WHERE empresa_id = ? AND id != ? ORDER BY id DESC LIMIT 1",
        (base["empresa_id"], fluxo_id),
    ).fetchone()
    blocos = conn.execute(
        "SELECT id, config_json, proximo_bloco_id FROM fluxo_blocos WHERE fluxo_id = ? ORDER BY ordem ASC",
        (novo_fluxo["id"],),
    ).fetchall()
    conn.close()

    assert novo_fluxo is not None
    assert len(blocos) == 2
    config_menu = json.loads(blocos[0]["config_json"])
    novo_proximo = config_menu["opcoes"][0]["proximo_bloco_id"]
    assert novo_proximo != bloco_compra_id
    assert novo_proximo == blocos[1]["id"]


def test_agendamento_bloqueia_conflito(app_module, seed_base):
    base = seed_base("agenda_conflito")
    data = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    sucesso, erro = app_module.salvar_agendamento(base["conversa_id"], data, "14:00", "Servico")
    assert sucesso is True
    assert erro["data"] == data
    assert erro["horario"] == "14:00"

    sucesso_2, erro_2 = app_module.salvar_agendamento(base["conversa_id"], data, "14h", "Servico")
    assert sucesso_2 is False
    assert "existe agendamento" in erro_2


def test_agendamento_tem_indice_unico_parcial(app_module):
    conn = app_module.get_connection()
    indice = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'index'
          AND name = 'idx_agendamentos_slot_ativo'
        """
    ).fetchone()
    conn.close()

    assert indice is not None
    assert "CREATE UNIQUE INDEX" in indice["sql"].upper()
    assert "WHERE status != 'cancelado'" in indice["sql"]


def test_agendamento_cancelado_libera_slot(app_module, seed_base):
    base = seed_base("agenda_cancelado")
    data = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
    conn = app_module.get_connection()
    conn.execute(
        """
        INSERT INTO agendamentos (
            empresa_id, contato_id, conversa_id, servico, data, horario, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            base["empresa_id"],
            base["contato_id"],
            base["conversa_id"],
            "Servico cancelado",
            data,
            "15:00",
            "cancelado",
        ),
    )
    conn.commit()
    conn.close()

    sucesso, resultado = app_module.salvar_agendamento(base["conversa_id"], data, "15:00", "Servico")

    assert sucesso is True
    assert resultado["data"] == data
    assert resultado["horario"] == "15:00"


def test_remarcar_agendamento_bloqueia_horario_ocupado(client, app_module, seed_base):
    base = seed_base("agenda_remarcar")
    data = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    conn = app_module.get_connection()
    cursor = conn.execute(
        """
        INSERT INTO agendamentos (
            empresa_id, contato_id, conversa_id, servico, data, horario, status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'confirmado')
        """,
        (base["empresa_id"], base["contato_id"], base["conversa_id"], "Servico A", data, "10:00"),
    )
    agendamento_a = cursor.lastrowid
    conn.execute(
        """
        INSERT INTO agendamentos (
            empresa_id, contato_id, conversa_id, servico, data, horario, status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'confirmado')
        """,
        (base["empresa_id"], base["contato_id"], base["conversa_id"], "Servico B", data, "11:00"),
    )
    conn.commit()
    conn.close()
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    resposta = client.post(
        f"/agendamentos/{agendamento_a}/remarcar",
        data={"data": data, "horario": "11:00", "servico": "Servico A remarcado"},
    )

    conn = app_module.get_connection()
    agendamento = conn.execute(
        "SELECT data, horario, servico FROM agendamentos WHERE id = ?",
        (agendamento_a,),
    ).fetchone()
    conn.close()

    assert resposta.status_code == 302
    assert agendamento["data"] == data
    assert agendamento["horario"] == "10:00"
    assert agendamento["servico"] == "Servico A"


def test_isolamento_bloqueia_conversa_de_outra_empresa(client, seed_base):
    empresa_a = seed_base("iso_a")
    empresa_b = seed_base("iso_b")
    login_session(client, empresa_a["user_id"], empresa_a["empresa_id"], email=empresa_a["email"])

    resposta = client.get(f"/conversas/{empresa_b['conversa_id']}")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/conversas")


def test_login_e_rota_protegida(client, seed_base):
    base = seed_base("login_rota")

    resposta_protegida = client.get("/dashboard")
    assert resposta_protegida.status_code == 302
    assert resposta_protegida.headers["Location"].endswith("/")

    resposta_login = client.post("/", data={"email": base["email"], "senha": "senha123"})
    assert resposta_login.status_code == 302
    assert resposta_login.headers["Location"].endswith("/dashboard")


def test_healthcheck_publico_valida_banco(client):
    resposta = client.get("/healthz")

    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok", "database": "ok"}


def test_webhook_whatsapp_simulado_deduplica_external_id(client, app_module, seed_base):
    base = seed_base("webhook")
    conn = app_module.get_connection()
    conn.execute(
        """
        INSERT INTO canal_integracoes (
            empresa_id, canal, nome, status, webhook_token, phone_number_id, access_token, config_json
        )
        VALUES (?, 'whatsapp', 'WhatsApp', 'ativo', 'token-webhook', 'phone-id', '', '{}')
        """,
        (base["empresa_id"],),
    )
    conn.commit()
    conn.close()
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.TESTE1",
                                    "from": "5511999999999",
                                    "text": {"body": "oi"},
                                }
                            ],
                            "contacts": [{"profile": {"name": "Cliente Webhook"}}],
                        }
                    }
                ]
            }
        ]
    }

    primeira = client.post("/webhooks/whatsapp/token-webhook", json=payload)
    segunda = client.post("/webhooks/whatsapp/token-webhook", json=payload)

    assert primeira.status_code == 200


def test_webhook_whatsapp_merges_contato_por_telefone(client, app_module, seed_base):
    base = seed_base("merge_contato")
    # Garantir que limites sejam criados
    app_module.garantir_limites_empresa(base["empresa_id"])
    conn = app_module.get_connection()
    conn.execute(
        "UPDATE contatos SET nome = ? WHERE id = ?",
        ("Contato sem nome", base["contato_id"])
    )
    conn.execute(
        "INSERT INTO canal_integracoes (empresa_id, canal, nome, status, webhook_token, phone_number_id, access_token, config_json) VALUES (?, 'whatsapp', 'WhatsApp', 'ativo', 'merge-token', 'phone-id', '', '{}')",
        (base["empresa_id"],)
    )
    conn.commit()
    conn.close()

    telefone = f"551190000{base['empresa_id']:04d}"
    from utils.normalizer import normalizar_telefone
    telefone_normalizado = normalizar_telefone(telefone)
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.MERGE1",
                                    "from": telefone,
                                    "text": {"body": "oi"},
                                }
                            ],
                            "contacts": [{"profile": {"name": "Cliente Novo"}}],
                        }
                    }
                ]
            }
        ]
    }

    response = client.post("/webhooks/whatsapp/merge-token", json=payload)
    assert response.status_code == 200

    conn = app_module.get_connection()
    contato = conn.execute(
        "SELECT id, telefone, nome FROM contatos WHERE empresa_id = ? AND telefone = ?",
        (base["empresa_id"], telefone_normalizado)
    ).fetchone()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ? AND telefone = ?",
        (base["empresa_id"], telefone_normalizado)
    ).fetchone()["total"]
    conn.close()

    assert contato is not None
    assert contato["nome"] == "Cliente Novo"
    assert total == 1


def test_contato_manual_rejeita_nome_none(client, app_module, seed_base):
    base = seed_base("contato_nome_none")
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    response = client.post(
        "/contatos/novo",
        data={"nome": "None", "telefone": "11988887777"},
    )

    conn = app_module.get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ? AND telefone = ?",
        (base["empresa_id"], "+5511988887777"),
    ).fetchone()["total"]
    conn.close()

    assert response.status_code == 200
    assert total == 0


def test_webhook_sem_nome_usa_fallback_seguro(client, app_module, seed_base):
    base = seed_base("webhook_nome_fallback")
    app_module.garantir_limites_empresa(base["empresa_id"])
    conn = app_module.get_connection()
    conn.execute(
        "INSERT INTO canal_integracoes (empresa_id, canal, nome, status, webhook_token, phone_number_id, access_token, config_json) VALUES (?, 'whatsapp', 'WhatsApp', 'ativo', 'fallback-token', 'phone-id', '', '{}')",
        (base["empresa_id"],)
    )
    conn.commit()
    conn.close()

    telefone = "5511900001234"
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.FALLBACK1",
                                    "from": telefone,
                                    "text": {"body": "oi"},
                                }
                            ],
                            "contacts": [{"profile": {"name": None}}],
                        }
                    }
                ]
            }
        ]
    }

    response = client.post("/webhooks/whatsapp/fallback-token", json=payload)

    conn = app_module.get_connection()
    contato = conn.execute(
        "SELECT nome FROM contatos WHERE empresa_id = ? AND telefone = ?",
        (base["empresa_id"], "+5511900001234"),
    ).fetchone()
    conn.close()

    assert response.status_code == 200
    assert contato is not None
    assert contato["nome"] == "Cliente WhatsApp"


def test_webhook_nao_mescla_apenas_por_nome(client, app_module, seed_base):
    base = seed_base("merge_nome")
    app_module.garantir_limites_empresa(base["empresa_id"])
    conn = app_module.get_connection()
    conn.execute(
        "UPDATE contatos SET nome = ?, telefone = ? WHERE id = ?",
        ("Cliente Igual", "+5511900001111", base["contato_id"]),
    )
    conn.execute(
        "INSERT INTO canal_integracoes (empresa_id, canal, nome, status, webhook_token, phone_number_id, access_token, config_json) VALUES (?, 'whatsapp', 'WhatsApp', 'ativo', 'nome-token', 'phone-id', '', '{}')",
        (base["empresa_id"],)
    )
    conn.commit()
    conn.close()

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.NOME1",
                                    "from": "5511900002222",
                                    "text": {"body": "oi"},
                                }
                            ],
                            "contacts": [{"profile": {"name": "Cliente Igual"}}],
                        }
                    }
                ]
            }
        ]
    }

    response = client.post("/webhooks/whatsapp/nome-token", json=payload)

    conn = app_module.get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ? AND nome = ?",
        (base["empresa_id"], "Cliente Igual"),
    ).fetchone()["total"]
    conn.close()

    assert response.status_code == 200
    assert total == 2


def test_login_registra_log(client, app_module, seed_base):
    base = seed_base("login_log")
    # Fazer login
    response = client.post(
        "/",
        data={"email": base["email"], "senha": "senha123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Verificar se log foi inserido
    conn = app_module.get_connection()
    log = conn.execute(
        "SELECT user_id, empresa_id, email_tentado, ip, user_agent, status, motivo FROM login_logs WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (base["user_id"],)
    ).fetchone()
    conn.close()
    assert log is not None
    assert log["user_id"] == base["user_id"]
    assert log["empresa_id"] == base["empresa_id"]
    assert log["email_tentado"] == base["email"]
    assert log["status"] == "sucesso"
    assert log["motivo"] is None
    assert log["ip"] == "127.0.0.1"  # IP do test client
    assert "werkzeug" in log["user_agent"].lower()  # User agent do test client


def test_login_senha_errada_registra_falha_sem_senha(client, app_module, seed_base):
    base = seed_base("login_falha_senha")

    response = client.post(
        "/",
        data={"email": base["email"], "senha": "senha-errada"},
        follow_redirects=True,
    )

    conn = app_module.get_connection()
    log = conn.execute(
        """
        SELECT user_id, empresa_id, email_tentado, status, motivo
        FROM login_logs
        WHERE email_tentado = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (base["email"],)
    ).fetchone()
    logs_com_senha = conn.execute(
        "SELECT COUNT(*) AS total FROM login_logs WHERE motivo LIKE ? OR email_tentado LIKE ?",
        ("%senha-errada%", "%senha-errada%")
    ).fetchone()["total"]
    conn.close()

    assert response.status_code == 200
    assert log is not None
    assert log["user_id"] == base["user_id"]
    assert log["empresa_id"] == base["empresa_id"]
    assert log["status"] == "falha"
    assert log["motivo"] == "credenciais_invalidas"
    assert logs_com_senha == 0


def test_login_usuario_inexistente_registra_falha(client, app_module):
    email = "naoexiste@teste.com"

    response = client.post(
        "/",
        data={"email": email, "senha": "qualquer-senha"},
        follow_redirects=True,
    )

    conn = app_module.get_connection()
    log = conn.execute(
        """
        SELECT user_id, empresa_id, email_tentado, status, motivo
        FROM login_logs
        WHERE email_tentado = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email,)
    ).fetchone()
    logs_com_senha = conn.execute(
        "SELECT COUNT(*) AS total FROM login_logs WHERE motivo LIKE ? OR email_tentado LIKE ?",
        ("%qualquer-senha%", "%qualquer-senha%")
    ).fetchone()["total"]
    conn.close()

    assert response.status_code == 200
    assert log is not None
    assert log["user_id"] is None
    assert log["empresa_id"] is None
    assert log["status"] == "falha"
    assert log["motivo"] == "credenciais_invalidas"
    assert logs_com_senha == 0


def assinatura_mercado_pago_teste(secret, data_id, request_id="request-test", ts=None):
    import hashlib
    import hmac
    import time

    ts = str(ts or int(time.time() * 1000))
    data_id = str(data_id).lower()
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    assinatura = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {
        "x-signature": f"ts={ts},v1={assinatura}",
        "x-request-id": request_id,
    }


def test_webhook_mercadopago_valida_assinatura(client, app_module, seed_base):
    payload_str = '{"test":"data"}'
    # Sem secret configurado
    response = client.post("/webhooks/mercadopago", data=payload_str, content_type="application/json")
    assert response.status_code == 500

    # Configurar secret para teste
    app_module.Config.MERCADO_PAGO_WEBHOOK_SECRET = "test_secret"
    app_module.Config.MERCADO_PAGO_API_KEY = "test_api_key"
    response = client.post("/webhooks/mercadopago", data=payload_str, content_type="application/json")
    assert response.status_code == 400

    # Assinatura inválida
    response = client.post(
        "/webhooks/mercadopago?data.id=mp-missing",
        data=payload_str,
        content_type="application/json",
        headers={"x-signature": "ts=1234567890,v1=invalid", "x-request-id": "request-invalid"}
    )
    assert response.status_code == 400

    # Timestamp expirado
    headers_expirados = assinatura_mercado_pago_teste("test_secret", "mp-missing", ts="1234567890")
    response = client.post(
        "/webhooks/mercadopago?data.id=mp-missing",
        data=payload_str,
        content_type="application/json",
        headers=headers_expirados
    )
    assert response.status_code == 400

    # Assinatura válida no formato oficial
    headers_validos = assinatura_mercado_pago_teste("test_secret", "mp-missing")
    response = client.post(
        "/webhooks/mercadopago?data.id=mp-missing",
        data=payload_str,
        content_type="application/json",
        headers=headers_validos
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Missing required fields"

    # Approved payment updates payment status on empresa_limites
    base = seed_base("mercado_pago")
    app_module.garantir_limites_empresa(base["empresa_id"])
    approved_payload = '{"status":"approved","external_reference":"1","id":"1234567890"}'  # Sempre usar 1 para consistência
    approved_headers = assinatura_mercado_pago_teste("test_secret", "1234567890")

    response = client.post(
        "/webhooks/mercadopago?data.id=1234567890",
        data=approved_payload,
        content_type="application/json",
        headers=approved_headers
    )
    assert response.status_code == 200
    approved_data = response.get_json()
    assert approved_data["status"] == "ok"

    conn = app_module.get_connection()
    limite = conn.execute(
        "SELECT status_pagamento FROM empresa_limites WHERE empresa_id = ?",
        (base["empresa_id"],)
    ).fetchone()
    conn.close()
    assert limite is not None
    assert limite["status_pagamento"] == "pago"

    # Non-approved payment should be ignored and not update payment status
    base2 = seed_base("mercado_pago_pending")
    app_module.garantir_limites_empresa(base2["empresa_id"])
    pending_payment_id = str(base2["empresa_id"]) + "999999999"
    pending_payload = '{"status":"pending","external_reference":"%s","id":"%s"}' % (base2["empresa_id"], pending_payment_id)
    pending_headers = assinatura_mercado_pago_teste("test_secret", pending_payment_id)

    response = client.post(
        f"/webhooks/mercadopago?data.id={pending_payment_id}",
        data=pending_payload,
        content_type="application/json",
        headers=pending_headers
    )
    assert response.status_code == 200
    pending_data = response.get_json()
    assert pending_data["status"] == "ignored"
    assert pending_data["reason"] == "not_approved"

    conn = app_module.get_connection()
    pending_limite = conn.execute(
        "SELECT status_pagamento FROM empresa_limites WHERE empresa_id = ?",
        (base2["empresa_id"],)
    ).fetchone()
    conn.close()
    assert pending_limite is not None
    assert pending_limite["status_pagamento"] != "pago"


def test_mercadopago_registra_origem_e_ignora_plano_do_payload(client, app_module, seed_base):
    base = seed_base("mercado_pago_origem")
    app_module.garantir_limites_empresa(base["empresa_id"])
    app_module.Config.MERCADO_PAGO_WEBHOOK_SECRET = "test_secret"
    app_module.Config.MERCADO_PAGO_API_KEY = ""

    conn = app_module.get_connection()
    limite_antes = conn.execute(
        "SELECT plano_id FROM empresa_limites WHERE empresa_id = ?",
        (base["empresa_id"],)
    ).fetchone()
    plano_payload = conn.execute(
        "SELECT id FROM planos_saas WHERE id != ? ORDER BY id DESC LIMIT 1",
        (limite_antes["plano_id"],)
    ).fetchone()
    conn.close()

    payload = (
        '{"status":"approved","external_reference":"%s","id":"mp-origem-1","plan_id":"%s"}'
        % (base["empresa_id"], plano_payload["id"])
    )
    headers = assinatura_mercado_pago_teste("test_secret", "mp-origem-1")

    response = client.post(
        "/webhooks/mercadopago?data.id=mp-origem-1",
        data=payload,
        content_type="application/json",
        headers=headers
    )

    conn = app_module.get_connection()
    limite_depois = conn.execute(
        """
        SELECT plano_id, status_pagamento, pagamento_origem_atualizacao, pagamento_status_externo
        FROM empresa_limites
        WHERE empresa_id = ?
        """,
        (base["empresa_id"],)
    ).fetchone()
    conn.close()

    assert response.status_code == 200
    assert limite_depois["status_pagamento"] == "pago"
    assert limite_depois["plano_id"] == limite_antes["plano_id"]
    assert limite_depois["pagamento_origem_atualizacao"] == "mercadopago_webhook"
    assert limite_depois["pagamento_status_externo"] == "approved"


def test_mercadopago_api_configurada_indisponivel_nao_atualiza_plano(client, app_module, seed_base):
    base = seed_base("mercado_pago_api_falha")
    app_module.garantir_limites_empresa(base["empresa_id"])
    app_module.Config.MERCADO_PAGO_WEBHOOK_SECRET = "test_secret"
    app_module.Config.MERCADO_PAGO_API_KEY = "token_configurado"
    app_module.consultar_pagamento_mercado_pago = lambda payment_id: None

    payload = '{"status":"approved","external_reference":"%s","id":"mp-api-falha-1"}' % base["empresa_id"]
    headers = assinatura_mercado_pago_teste("test_secret", "mp-api-falha-1")

    response = client.post(
        "/webhooks/mercadopago?data.id=mp-api-falha-1",
        data=payload,
        content_type="application/json",
        headers=headers
    )

    conn = app_module.get_connection()
    limite = conn.execute(
        "SELECT status_pagamento, payment_id_externo FROM empresa_limites WHERE empresa_id = ?",
        (base["empresa_id"],)
    ).fetchone()
    conn.close()

    assert response.status_code == 503
    assert limite["status_pagamento"] != "pago"
    assert limite["payment_id_externo"] is None


def test_transicao_pagamento_exige_origem_confiavel(app_module, seed_base):
    base = seed_base("mercado_pago_origem_direta")
    app_module.garantir_limites_empresa(base["empresa_id"])
    conn = app_module.get_connection()

    try:
        app_module.processar_transicao_status_pagamento(
            conn,
            base["empresa_id"],
            "approved",
            payment_id_externo="mp-falso",
            origem="payload_manual"
        )
    except ValueError as erro:
        assert "Origem" in str(erro)
    else:
        raise AssertionError("Transicao sem origem confiavel deveria falhar")
    finally:
        conn.rollback()
        limite = conn.execute(
            "SELECT status_pagamento, payment_id_externo FROM empresa_limites WHERE empresa_id = ?",
            (base["empresa_id"],)
        ).fetchone()
        conn.close()

    assert limite["status_pagamento"] != "pago"
    assert limite["payment_id_externo"] is None

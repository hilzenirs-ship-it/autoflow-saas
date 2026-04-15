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
    assert primeira.get_json()["ok"] is True
    assert segunda.status_code == 200
    assert segunda.get_json()["duplicada"] is True

    conn = app_module.get_connection()
    total = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens m
        JOIN conversas c ON c.id = m.conversa_id
        WHERE c.empresa_id = ?
          AND m.external_id = 'wamid.TESTE1'
          AND m.remetente_tipo = 'cliente'
        """,
        (base["empresa_id"],),
    ).fetchone()["total"]
    conn.close()
    assert total == 1

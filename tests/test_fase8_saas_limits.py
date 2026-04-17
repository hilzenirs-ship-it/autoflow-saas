from tests.conftest import login_session


def atualizar_limites(app_module, empresa_id, **limites):
    app_module.garantir_limites_empresa(empresa_id)
    campos = ", ".join([f"{campo} = ?" for campo in limites])
    valores = list(limites.values()) + [empresa_id]
    conn = app_module.get_connection()
    conn.execute(
        f"UPDATE empresa_limites SET {campos} WHERE empresa_id = ?",
        tuple(valores),
    )
    conn.commit()
    conn.close()


def test_limite_contatos_bloqueia_novo_contato(client, app_module, seed_base):
    base = seed_base("limite_contatos")
    atualizar_limites(app_module, base["empresa_id"], limite_contatos=1)
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    resposta = client.post("/contatos/novo", data={"nome": "Extra", "telefone": "5511999999999"})

    assert resposta.status_code == 302
    conn = app_module.get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ?",
        (base["empresa_id"],),
    ).fetchone()["total"]
    conn.close()
    assert total == 1


def test_limite_mensagens_bloqueia_criacao(app_module, seed_base):
    base = seed_base("limite_mensagens")
    atualizar_limites(app_module, base["empresa_id"], limite_mensagens=1)

    primeira = app_module.criar_mensagem(base["conversa_id"], "cliente", "primeira", "recebida")
    segunda = app_module.criar_mensagem(base["conversa_id"], "cliente", "segunda", "recebida")

    assert primeira is not None
    assert segunda is None


def test_limite_atendentes_bloqueia_novo_membro(client, app_module, seed_base):
    base = seed_base("limite_atendentes")
    atualizar_limites(app_module, base["empresa_id"], limite_atendentes=1)
    conn = app_module.get_connection()
    conn.execute(
        "INSERT INTO users (nome, email, senha_hash) VALUES (?, ?, ?)",
        ("Outro Usuario", "outro-limite@teste.com", app_module.gerar_hash_senha("senha123")),
    )
    conn.commit()
    conn.close()
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    resposta = client.post(
        "/configuracoes/membros/adicionar",
        data={"email": "outro-limite@teste.com", "papel": "membro"},
    )

    assert resposta.status_code == 302
    conn = app_module.get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM empresa_membros WHERE empresa_id = ? AND ativo = 1",
        (base["empresa_id"],),
    ).fetchone()["total"]
    conn.close()
    assert total == 1


def test_limite_integracoes_bloqueia_segunda_integracao(client, app_module, seed_base):
    base = seed_base("limite_integracoes")
    atualizar_limites(app_module, base["empresa_id"], limite_integracoes=1)
    login_session(client, base["user_id"], base["empresa_id"], email=base["email"])

    primeira = client.post(
        "/configuracoes/integracoes/salvar",
        data={"canal": "whatsapp", "nome": "WhatsApp", "status": "ativo"},
    )
    segunda = client.post(
        "/configuracoes/integracoes/salvar",
        data={"canal": "instagram", "nome": "Instagram", "status": "ativo"},
    )

    assert primeira.status_code == 302
    assert segunda.status_code == 302
    conn = app_module.get_connection()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM canal_integracoes WHERE empresa_id = ?",
        (base["empresa_id"],),
    ).fetchone()["total"]
    conn.close()
    assert total == 1

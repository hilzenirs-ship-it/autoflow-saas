from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, has_request_context
from utils.db import get_connection
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from config import Config
from flask_wtf.csrf import CSRFProtect
from utils.limiter import limiter
import json
import unicodedata
import os
import requests
import csv
import io
import secrets
import hmac
import hashlib
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

csrf = CSRFProtect(app)
from flask_caching import Cache

from utils.cache import cache

cache.init_app(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': Config.REDIS_URL or 'redis://localhost:6379/0'})


def _coluna_existe(conn, tabela, coluna):
    try:
        cols = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    except Exception:
        return False
    for col in cols:
        if col["name"] == coluna:
            return True
    return False


def _garantir_coluna(conn, tabela, coluna, definicao):
    if not _coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def garantir_schema_compativel():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            cor TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contato_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contato_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metricas_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo_evento TEXT NOT NULL,
            referencia_id INTEGER,
            valor TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS empresa_membros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            papel TEXT DEFAULT 'membro',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agenda_disponibilidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fluxo_execucoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            fluxo_id INTEGER,
            bloco_id INTEGER,
            evento TEXT NOT NULL,
            detalhe TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fluxo_versoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fluxo_id INTEGER NOT NULL,
            versao INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversa_atendentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            nome_atendente TEXT,
            papel TEXT DEFAULT 'atendente',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(conversa_id, user_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cliente_memorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            contato_id INTEGER NOT NULL,
            resumo TEXT,
            preferencias_json TEXT,
            contexto_json TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, contato_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS canal_integracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            canal TEXT NOT NULL,
            nome TEXT,
            status TEXT DEFAULT 'rascunho',
            access_token TEXT,
            webhook_token TEXT,
            phone_number_id TEXT,
            business_account_id TEXT,
            instagram_account_id TEXT,
            config_json TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS planos_saas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            preco_mensal REAL DEFAULT 0,
            limite_conversas INTEGER,
            limite_mensagens INTEGER,
            limite_atendentes INTEGER,
            limite_integracoes INTEGER,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS empresa_limites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL UNIQUE,
            plano_id INTEGER,
            limite_conversas INTEGER,
            limite_mensagens INTEGER,
            limite_atendentes INTEGER,
            limite_integracoes INTEGER,
            status TEXT DEFAULT 'ativo',
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contatos_empresa_telefone
        ON contatos (empresa_id, telefone)
        """
    )
    _garantir_coluna(conn, "conversas", "bot_ativo", "INTEGER DEFAULT 1")
    _garantir_coluna(conn, "conversas", "atendente_nome", "TEXT")
    _garantir_coluna(conn, "conversas", "etapa", "TEXT")
    _garantir_coluna(conn, "conversas", "contexto_json", "TEXT")
    _garantir_coluna(conn, "conversas", "fluxo_id_ativo", "INTEGER")
    _garantir_coluna(conn, "conversas", "bloco_atual_id", "INTEGER")
    _garantir_coluna(conn, "contatos", "origem", "TEXT")

    _garantir_coluna(conn, "regras", "tipo_regra", "TEXT")
    _garantir_coluna(conn, "regras", "condicao_json", "TEXT")
    _garantir_coluna(conn, "regras", "acao_json", "TEXT")
    _garantir_coluna(conn, "regras", "fluxo_id", "INTEGER")
    _garantir_coluna(conn, "regras", "ativa", "INTEGER DEFAULT 1")

    _garantir_coluna(conn, "fluxos", "tipo_gatilho", "TEXT")
    _garantir_coluna(conn, "fluxos", "gatilho_valor", "TEXT")

    _garantir_coluna(conn, "agendamentos", "servico", "TEXT")
    _garantir_coluna(conn, "agendamentos", "data", "TEXT")
    _garantir_coluna(conn, "agendamentos", "horario", "TEXT")
    _garantir_coluna(conn, "agendamentos", "status", "TEXT DEFAULT 'confirmado'")

    _garantir_coluna(conn, "mensagens", "user_id", "INTEGER")
    _garantir_coluna(conn, "mensagens", "canal", "TEXT DEFAULT 'interno'")
    _garantir_coluna(conn, "mensagens", "external_id", "TEXT")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mensagens_external_id_canal
        ON mensagens (external_id, canal, remetente_tipo, direcao)
        """
    )

    _garantir_coluna(conn, "canal_integracoes", "access_token", "TEXT")
    _garantir_coluna(conn, "canal_integracoes", "webhook_token", "TEXT")
    _garantir_coluna(conn, "canal_integracoes", "phone_number_id", "TEXT")
    _garantir_coluna(conn, "canal_integracoes", "business_account_id", "TEXT")
    _garantir_coluna(conn, "canal_integracoes", "instagram_account_id", "TEXT")
    _garantir_coluna(conn, "canal_integracoes", "config_json", "TEXT")

    planos_padrao = [
        ("Starter", "Base SaaS inicial para operar atendimento e automacao.", 0, 500, 5000, 3, 1),
        ("Pro", "Operacao profissional com mais atendentes, canais e volume.", 149, 3000, 30000, 10, 3),
        ("Scale", "Estrutura preparada para crescimento e multiplas equipes.", 399, None, None, None, None),
    ]
    for plano in planos_padrao:
        conn.execute(
            """
            INSERT OR IGNORE INTO planos_saas (
                nome, descricao, preco_mensal, limite_conversas,
                limite_mensagens, limite_atendentes, limite_integracoes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            plano
        )

    empresas = conn.execute("SELECT id, user_id FROM empresas").fetchall()
    for empresa in empresas:
        existe = conn.execute(
            """
            SELECT id
            FROM empresa_membros
            WHERE empresa_id = ? AND user_id = ?
            LIMIT 1
            """,
            (empresa["id"], empresa["user_id"])
        ).fetchone()
        if not existe:
            conn.execute(
                """
                INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo)
                VALUES (?, ?, 'owner', 1)
                """,
                (empresa["id"], empresa["user_id"])
            )
        limite_existe = conn.execute(
            """
            SELECT id
            FROM empresa_limites
            WHERE empresa_id = ?
            LIMIT 1
            """,
            (empresa["id"],)
        ).fetchone()
        if not limite_existe:
            plano_starter = conn.execute(
                "SELECT id, limite_conversas, limite_mensagens, limite_atendentes, limite_integracoes FROM planos_saas WHERE nome = 'Starter' LIMIT 1"
            ).fetchone()
            conn.execute(
                """
                INSERT INTO empresa_limites (
                    empresa_id, plano_id, limite_conversas, limite_mensagens,
                    limite_atendentes, limite_integracoes, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'ativo')
                """,
                (
                    empresa["id"],
                    plano_starter["id"] if plano_starter else None,
                    plano_starter["limite_conversas"] if plano_starter else 500,
                    plano_starter["limite_mensagens"] if plano_starter else 5000,
                    plano_starter["limite_atendentes"] if plano_starter else 3,
                    plano_starter["limite_integracoes"] if plano_starter else 1,
                )
            )
    conn.commit()
    conn.close()


garantir_schema_compativel()


# =========================================================
# HELPERS GERAIS
# =========================================================
def normalizar_texto(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def senha_confere(senha_digitada, senha_salva):
    senha_digitada = (senha_digitada or "").strip()
    senha_salva = (senha_salva or "").strip()

    if not senha_digitada or not senha_salva:
        return False

    try:
        if senha_salva.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            return check_password_hash(senha_salva, senha_digitada)
    except Exception:
        pass

    return senha_digitada == senha_salva


def gerar_hash_senha(senha):
    senha = (senha or "").strip()
    if not senha:
        return ""
    return generate_password_hash(senha)


def buscar_usuario_por_email(email):
    email = (email or "").strip().lower()
    if not email:
        return None

    conn = get_connection()
    usuario = conn.execute(
        """
        SELECT *
        FROM users
        WHERE lower(email) = ?
        LIMIT 1
        """,
        (email,)
    ).fetchone()
    conn.close()
    return usuario


def buscar_empresa_do_usuario(user_id):
    conn = get_connection()
    empresa = conn.execute(
        """
        SELECT e.*
        FROM empresas e
        JOIN empresa_membros em ON em.empresa_id = e.id
        WHERE em.user_id = ? AND em.ativo = 1
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, e.id ASC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return empresa


def buscar_empresas_do_usuario(user_id):
    conn = get_connection()
    empresas = conn.execute(
        """
        SELECT
            e.*,
            em.papel
        FROM empresas e
        JOIN empresa_membros em ON em.empresa_id = e.id
        WHERE em.user_id = ? AND em.ativo = 1
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, e.nome_empresa ASC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return empresas


def usuario_logado():
    if not has_request_context():
        return False
    return "user_id" in session and "empresa_id" in session


def obter_user_id_logado():
    if not has_request_context():
        return None
    return session.get("user_id")


def obter_empresa_id_logada():
    if not has_request_context():
        return None
    return session.get("empresa_id")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not usuario_logado():
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def conversa_pertence_empresa(conversa_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return False

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT id
        FROM conversas
        WHERE id = ? AND empresa_id = ?
        """,
        (conversa_id, empresa_id)
    ).fetchone()
    conn.close()

    return conversa is not None


def obter_empresa_id_da_conversa(conversa_id):
    if not conversa_id:
        return None

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT empresa_id
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if not conversa:
        return None

    return conversa["empresa_id"]


def conversa_acessivel_na_sessao(conversa_id):
    empresa_id = obter_empresa_id_logada()
    if not empresa_id:
        return True
    return conversa_pertence_empresa(conversa_id, empresa_id)


def contato_pertence_empresa(contato_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return False

    conn = get_connection()
    contato = conn.execute(
        """
        SELECT id
        FROM contatos
        WHERE id = ? AND empresa_id = ?
        """,
        (contato_id, empresa_id)
    ).fetchone()
    conn.close()

    return contato is not None


def fluxo_pertence_empresa(fluxo_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return False

    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT id
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    conn.close()

    return fluxo is not None


def tag_pertence_empresa(tag_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id or not tag_id:
        return False

    conn = get_connection()
    tag = conn.execute(
        """
        SELECT id
        FROM tags
        WHERE id = ? AND empresa_id = ?
        """,
        (tag_id, empresa_id)
    ).fetchone()
    conn.close()

    return tag is not None


def filtrar_tags_da_empresa(tag_ids, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    tag_ids_limpos = []
    for tag_id in tag_ids or []:
        try:
            tag_id_int = int(tag_id)
        except (TypeError, ValueError):
            continue
        if tag_id_int not in tag_ids_limpos:
            tag_ids_limpos.append(tag_id_int)

    if not empresa_id or not tag_ids_limpos:
        return []

    placeholders = ", ".join(["?"] * len(tag_ids_limpos))
    conn = get_connection()
    tags = conn.execute(
        f"""
        SELECT id
        FROM tags
        WHERE empresa_id = ? AND id IN ({placeholders})
        """,
        tuple([empresa_id] + tag_ids_limpos)
    ).fetchall()
    conn.close()

    tags_validas = {row["id"] for row in tags}
    return [tag_id for tag_id in tag_ids_limpos if tag_id in tags_validas]


def bloco_pertence_fluxo(bloco_id, fluxo_id):
    if not bloco_id or not fluxo_id:
        return False

    conn = get_connection()
    bloco = conn.execute(
        """
        SELECT id
        FROM fluxo_blocos
        WHERE id = ? AND fluxo_id = ?
        """,
        (bloco_id, fluxo_id)
    ).fetchone()
    conn.close()

    return bloco is not None


def fluxo_id_do_bloco(bloco_id):
    if not bloco_id:
        return None

    conn = get_connection()
    bloco = conn.execute(
        """
        SELECT fluxo_id
        FROM fluxo_blocos
        WHERE id = ?
        """,
        (bloco_id,)
    ).fetchone()
    conn.close()

    if not bloco:
        return None

    return bloco["fluxo_id"]


def normalizar_proximo_bloco_id(proximo_bloco_id, fluxo_id):
    if proximo_bloco_id in [None, ""]:
        return None

    try:
        proximo_bloco_id_int = int(proximo_bloco_id)
    except (TypeError, ValueError):
        return None

    if bloco_pertence_fluxo(proximo_bloco_id_int, fluxo_id):
        return proximo_bloco_id_int

    return None


def normalizar_config_bloco_fluxo(config, fluxo_id):
    config = config if isinstance(config, dict) else {}
    opcoes = config.get("opcoes")
    if isinstance(opcoes, list):
        for opcao in opcoes:
            if not isinstance(opcao, dict):
                continue
            opcao["proximo_bloco_id"] = normalizar_proximo_bloco_id(
                opcao.get("proximo_bloco_id"),
                fluxo_id
            )
    return config


def buscar_nome_empresa(empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return "Empresa"

    conn = get_connection()
    empresa = conn.execute(
        """
        SELECT nome_exibicao, nome_empresa
        FROM empresas
        WHERE id = ?
        """,
        (empresa_id,)
    ).fetchone()
    conn.close()

    if not empresa:
        return "Empresa"

    return empresa["nome_exibicao"] or empresa["nome_empresa"] or "Empresa"


def buscar_ou_criar_conversa(contato_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return None

    conn = get_connection()

    contato = conn.execute(
        """
        SELECT id
        FROM contatos
        WHERE id = ? AND empresa_id = ?
        """,
        (contato_id, empresa_id)
    ).fetchone()

    if not contato:
        conn.close()
        return None

    conversa = conn.execute(
        """
        SELECT *
        FROM conversas
        WHERE contato_id = ? AND empresa_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (contato_id, empresa_id)
    ).fetchone()

    if conversa:
        conn.close()
        return conversa["id"]

    cursor = conn.execute(
        """
        INSERT INTO conversas (
            empresa_id,
            contato_id,
            status,
            bot_ativo,
            atendente_nome,
            etapa,
            contexto_json,
            fluxo_id_ativo,
            bloco_atual_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (empresa_id, contato_id, "aberta", 1, None, None, None, None, None)
    )
    conversa_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return conversa_id


def atualizar_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (conversa_id,)
    )
    conn.commit()
    conn.close()


def buscar_ultima_mensagem(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return "Sem mensagens ainda"

    conn = get_connection()
    mensagem = conn.execute(
        """
        SELECT conteudo
        FROM mensagens
        WHERE conversa_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if mensagem:
        return mensagem["conteudo"]

    return "Sem mensagens ainda"


def buscar_ultima_mensagem_completa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    conn = get_connection()
    mensagem = conn.execute(
        """
        SELECT *
        FROM mensagens
        WHERE conversa_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()
    return mensagem


def criar_mensagem(conversa_id, remetente_tipo, conteudo, direcao=None, regra_id=None, user_id=None, canal="interno", external_id=None):
    conteudo = (conteudo or "").strip()
    if not conteudo:
        return None
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    if direcao is None:
        direcao = "recebida" if remetente_tipo == "cliente" else "enviada"

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT id, empresa_id
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()

    if not conversa:
        conn.close()
        return None

    cursor = conn.execute(
        """
        INSERT INTO mensagens (
            conversa_id,
            direcao,
            remetente_tipo,
            conteudo,
            regra_id,
            user_id,
            canal,
            external_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (conversa_id, direcao, remetente_tipo, conteudo, regra_id, user_id, canal, external_id)
    )
    mensagem_id = cursor.lastrowid
    conn.commit()
    conn.close()

    atualizar_conversa(conversa_id)
    registrar_evento(
        "mensagem_criada",
        referencia_id=conversa_id,
        valor=json.dumps(
            {
                "remetente_tipo": remetente_tipo,
                "direcao": direcao,
                "regra_id": regra_id,
                "user_id": user_id,
                "canal": canal or "interno",
            },
            ensure_ascii=False
        ),
        empresa_id=conversa["empresa_id"]
    )
    return mensagem_id


def vincular_atendente_conversa(conversa_id, user_id=None, nome_atendente=None, papel="atendente"):
    user_id = user_id or obter_user_id_logado()
    nome_atendente = (nome_atendente or session.get("user_nome") or "Atendente").strip()
    if not conversa_id or not user_id:
        return
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO conversa_atendentes (conversa_id, user_id, nome_atendente, papel, ativo)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(conversa_id, user_id) DO UPDATE SET
            nome_atendente = excluded.nome_atendente,
            papel = excluded.papel,
            ativo = 1,
            atualizado_em = CURRENT_TIMESTAMP
        """,
        (conversa_id, user_id, nome_atendente, papel)
    )
    conn.commit()
    conn.close()


def listar_atendentes_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return []

    conn = get_connection()
    atendentes = conn.execute(
        """
        SELECT ca.user_id, ca.nome_atendente, ca.papel, ca.ativo, ca.criado_em, u.email
        FROM conversa_atendentes ca
        LEFT JOIN users u ON u.id = ca.user_id
        WHERE ca.conversa_id = ? AND ca.ativo = 1
        ORDER BY ca.atualizado_em DESC, ca.id DESC
        """,
        (conversa_id,)
    ).fetchall()
    conn.close()
    return atendentes


# =========================================================
# HELPERS DE ETAPA / CONTEXTO / FLUXO EM CONVERSA
# =========================================================
def buscar_etapa_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT etapa
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if conversa:
        return conversa["etapa"]

    return None


def atualizar_etapa_conversa(conversa_id, etapa):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET etapa = ?, atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (etapa, conversa_id)
    )
    conn.commit()
    conn.close()


def buscar_contexto_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return {}

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT contexto_json
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if not conversa or not conversa["contexto_json"]:
        return {}

    try:
        return json.loads(conversa["contexto_json"])
    except Exception:
        return {}


def atualizar_contexto_conversa(conversa_id, contexto):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET contexto_json = ?, atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(contexto or {}, ensure_ascii=False), conversa_id)
    )
    conn.commit()
    conn.close()


def limpar_fluxo_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET etapa = NULL,
            contexto_json = NULL,
            fluxo_id_ativo = NULL,
            bloco_atual_id = NULL,
            atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (conversa_id,)
    )
    conn.commit()
    conn.close()


def atualizar_contexto_parcial(conversa_id, novos_dados):
    contexto = buscar_contexto_conversa(conversa_id)
    contexto.update(novos_dados or {})
    atualizar_contexto_conversa(conversa_id, contexto)


def registrar_evento(tipo_evento, referencia_id=None, valor=None, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id or not tipo_evento:
        return

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO metricas_eventos (
            empresa_id,
            tipo_evento,
            referencia_id,
            valor
        )
        VALUES (?, ?, ?, ?)
        """,
        (empresa_id, str(tipo_evento).strip(), referencia_id, valor)
    )
    conn.commit()
    conn.close()


def obter_status_atendimento(conversa_row):
    if not conversa_row:
        return "bot"
    conversa_data = dict(conversa_row)
    contexto = {}
    if conversa_data.get("contexto_json"):
        try:
            contexto = json.loads(conversa_data["contexto_json"])
        except Exception:
            contexto = {}
    status = (contexto.get("atendimento_status") or "").strip()
    if status in ["bot", "em_atendimento", "aguardando_cliente"]:
        return status
    return "bot" if int(conversa_data.get("bot_ativo") or 0) == 1 else "em_atendimento"


def registrar_execucao_fluxo(conversa_id, fluxo_id, bloco_id, evento, detalhe=None):
    empresa_id = obter_empresa_id_da_conversa(conversa_id)
    if not empresa_id:
        return
    if fluxo_id and not fluxo_pertence_empresa(fluxo_id, empresa_id):
        return
    if bloco_id and fluxo_id and not bloco_pertence_fluxo(bloco_id, fluxo_id):
        return

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO fluxo_execucoes (
            conversa_id,
            fluxo_id,
            bloco_id,
            evento,
            detalhe
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (conversa_id, fluxo_id, bloco_id, evento, detalhe)
    )
    conn.commit()
    conn.close()


def snapshot_fluxo_versao(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    if empresa_id and not fluxo_pertence_empresa(fluxo_id, empresa_id):
        return

    conn = get_connection()
    fluxo = conn.execute(
        "SELECT * FROM fluxos WHERE id = ?" + (" AND empresa_id = ?" if empresa_id else ""),
        (fluxo_id, empresa_id) if empresa_id else (fluxo_id,)
    ).fetchone()
    if not fluxo:
        conn.close()
        return
    blocos = conn.execute(
        """
        SELECT *
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        ORDER BY ordem ASC, id ASC
        """,
        (fluxo_id,)
    ).fetchall()
    ultima = conn.execute(
        "SELECT MAX(versao) AS v FROM fluxo_versoes WHERE fluxo_id = ?",
        (fluxo_id,)
    ).fetchone()
    versao = int((ultima["v"] if ultima and ultima["v"] else 0) or 0) + 1
    payload = {
        "fluxo": dict(fluxo) if fluxo else {},
        "blocos": [dict(b) for b in blocos],
    }
    conn.execute(
        """
        INSERT INTO fluxo_versoes (fluxo_id, versao, payload_json)
        VALUES (?, ?, ?)
        """,
        (fluxo_id, versao, json.dumps(payload, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


def salvar_status_atendimento(conversa_id, status, atendente_nome=None):
    if status not in ["bot", "em_atendimento", "aguardando_cliente"]:
        return
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    contexto = buscar_contexto_conversa(conversa_id)
    contexto["atendimento_status"] = status
    historico = contexto.get("atendimento_historico", [])
    if not isinstance(historico, list):
        historico = []
    historico.append(
        {
            "acao": status,
            "atendente": atendente_nome,
            "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    contexto["atendimento_historico"] = historico[-30:]
    atualizar_contexto_conversa(conversa_id, contexto)


def buscar_fluxo_ativo_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT fluxo_id_ativo, bloco_atual_id
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()
    return conversa


def atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id=None, bloco_atual_id=None):
    if not conversa_acessivel_na_sessao(conversa_id):
        return
    if fluxo_id and fluxo_id != fluxo_id_ativo_da_conversa(conversa_id):
        empresa_id = obter_empresa_id_da_conversa(conversa_id)
        if not fluxo_pertence_empresa(fluxo_id, empresa_id):
            return
    if bloco_atual_id and not fluxo_id:
        return
    if bloco_atual_id and fluxo_id and not bloco_pertence_fluxo(bloco_atual_id, fluxo_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET fluxo_id_ativo = ?,
            bloco_atual_id = ?,
            atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (fluxo_id, bloco_atual_id, conversa_id)
    )
    conn.commit()
    conn.close()


def normalizar_data_agendamento(data_texto, base=None):
    texto = normalizar_texto(data_texto)
    hoje = (base or datetime.now()).date()
    if not texto:
        return None, "Informe uma data para o agendamento."

    aliases = {
        "hoje": hoje,
        "amanha": hoje + timedelta(days=1),
        "amanhã": hoje + timedelta(days=1),
    }
    if texto in aliases:
        return aliases[texto].strftime("%Y-%m-%d"), None

    dias_semana = {
        "segunda": 0,
        "segunda feira": 0,
        "terca": 1,
        "terca feira": 1,
        "terça": 1,
        "terça feira": 1,
        "quarta": 2,
        "quarta feira": 2,
        "quinta": 3,
        "quinta feira": 3,
        "sexta": 4,
        "sexta feira": 4,
        "sabado": 5,
        "sábado": 5,
        "domingo": 6,
    }
    if texto in dias_semana:
        dias_ate = (dias_semana[texto] - hoje.weekday()) % 7
        data_obj = hoje + timedelta(days=dias_ate)
        return data_obj.strftime("%Y-%m-%d"), None

    formatos = [
        ("%Y-%m-%d", r"^\d{4}-\d{1,2}-\d{1,2}$"),
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
    ]
    for formato, padrao in formatos:
        if re.match(padrao, texto):
            try:
                data_obj = datetime.strptime(texto, formato).date()
                return data_obj.strftime("%Y-%m-%d"), None
            except ValueError:
                return None, "Data inválida."

    match_sem_ano = re.match(r"^(\d{1,2})[/-](\d{1,2})$", texto)
    if match_sem_ano:
        dia = int(match_sem_ano.group(1))
        mes = int(match_sem_ano.group(2))
        try:
            data_obj = datetime(hoje.year, mes, dia).date()
            if data_obj < hoje:
                data_obj = datetime(hoje.year + 1, mes, dia).date()
            return data_obj.strftime("%Y-%m-%d"), None
        except ValueError:
            return None, "Data inválida."

    return None, "Use uma data válida, por exemplo 2026-04-25 ou 25/04/2026."


def normalizar_horario_agendamento(horario_texto):
    texto = normalizar_texto(horario_texto)
    if not texto:
        return None, "Informe um horário para o agendamento."

    texto = texto.replace(" horas", "h").replace(" hora", "h")
    match = re.match(r"^(\d{1,2})(?::|h)?(\d{2})?$", texto)
    if not match:
        return None, "Use um horário válido, por exemplo 14:30."

    hora = int(match.group(1))
    minuto = int(match.group(2) or 0)
    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
        return None, "Horário inválido."

    return f"{hora:02d}:{minuto:02d}", None


def disponibilidade_agendamento_ok(conn, empresa_id, data_ag, horario_ag):
    data_obj = datetime.strptime(data_ag, "%Y-%m-%d")
    dia_semana = data_obj.weekday()
    faixas = conn.execute(
        """
        SELECT hora_inicio, hora_fim
        FROM agenda_disponibilidade
        WHERE empresa_id = ? AND dia_semana = ? AND ativo = 1
        ORDER BY hora_inicio ASC
        """,
        (empresa_id, dia_semana)
    ).fetchall()
    if not faixas:
        return True

    for faixa in faixas:
        inicio, erro_inicio = normalizar_horario_agendamento(faixa["hora_inicio"])
        fim, erro_fim = normalizar_horario_agendamento(faixa["hora_fim"])
        if erro_inicio or erro_fim:
            continue
        if inicio <= horario_ag <= fim:
            return True
    return False


def validar_dados_agendamento(conn, empresa_id, data_texto, horario_texto, excluir_agendamento_id=None):
    data_norm, erro_data = normalizar_data_agendamento(data_texto)
    if erro_data:
        return None, None, erro_data

    horario_norm, erro_horario = normalizar_horario_agendamento(horario_texto)
    if erro_horario:
        return None, None, erro_horario

    try:
        inicio_agendamento = datetime.strptime(f"{data_norm} {horario_norm}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None, None, "Data ou horário inválido."

    agora = datetime.now().replace(second=0, microsecond=0)
    if inicio_agendamento < agora:
        return None, None, "Não é possível agendar em data ou horário passado."

    if not disponibilidade_agendamento_ok(conn, empresa_id, data_norm, horario_norm):
        return None, None, "Horário fora da disponibilidade configurada."

    query = """
        SELECT id
        FROM agendamentos
        WHERE empresa_id = ?
          AND data = ?
          AND horario = ?
          AND status != 'cancelado'
    """
    params = [empresa_id, data_norm, horario_norm]
    if excluir_agendamento_id:
        query += " AND id != ?"
        params.append(excluir_agendamento_id)
    query += " LIMIT 1"

    conflito = conn.execute(query, tuple(params)).fetchone()
    if conflito:
        return None, None, "Já existe agendamento nesse horário."

    return data_norm, horario_norm, None


def salvar_agendamento(conversa_id, data_texto, horario_texto, servico=None):
    if not conversa_acessivel_na_sessao(conversa_id):
        return False, "Conversa não encontrada."

    conn = get_connection()

    conversa = conn.execute(
        """
        SELECT empresa_id, contato_id
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()

    if not conversa:
        conn.close()
        return False, "Conversa não encontrada."

    data_normalizada, horario_normalizado, erro_validacao = validar_dados_agendamento(
        conn,
        conversa["empresa_id"],
        data_texto,
        horario_texto
    )
    if erro_validacao:
        conn.close()
        return False, erro_validacao

    cursor = conn.execute(
        """
        INSERT INTO agendamentos (
            empresa_id,
            contato_id,
            conversa_id,
            servico,
            data,
            horario,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conversa["empresa_id"],
            conversa["contato_id"],
            conversa_id,
            servico,
            data_normalizada,
            horario_normalizado,
            "confirmado"
        )
    )
    conn.commit()
    conn.close()
    registrar_evento(
        "agendamento_criado",
        referencia_id=cursor.lastrowid,
        valor=json.dumps(
            {"conversa_id": conversa_id, "servico": servico, "data": data_normalizada, "horario": horario_normalizado},
            ensure_ascii=False
        ),
        empresa_id=conversa["empresa_id"]
    )
    return True, {"data": data_normalizada, "horario": horario_normalizado}


# =========================================================
# HELPERS DE REGRAS
# =========================================================
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


def regra_atende_contexto(regra, conversa_id=None):
    if not conversa_id:
        return True
    if not conversa_acessivel_na_sessao(conversa_id):
        return False

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


def buscar_melhor_regra(mensagem_cliente, empresa_id=None, conversa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada() or obter_empresa_id_da_conversa(conversa_id)
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
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    acoes = extrair_acoes_regra(regra["acao_json"])
    etapa_destino = (acoes.get("etapa_destino") or "").strip()
    if etapa_destino:
        atualizar_etapa_conversa(conversa_id, etapa_destino)
    tag_id = acoes.get("tag_id")
    if tag_id:
        conn = get_connection()
        contato = conn.execute("SELECT empresa_id, contato_id FROM conversas WHERE id = ?", (conversa_id,)).fetchone()
        if contato and tag_pertence_empresa(tag_id, contato["empresa_id"]):
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
        registrar_evento(
            "regra_acionada",
            referencia_id=melhor_regra["id"],
            valor=melhor_regra["nome"],
            empresa_id=empresa_id or obter_empresa_id_da_conversa(conversa_id)
        )
    return resposta, melhor_regra["id"]


def buscar_fluxo_por_regra(mensagem_cliente, empresa_id=None, conversa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada() or obter_empresa_id_da_conversa(conversa_id)
    melhor_regra = buscar_melhor_regra(mensagem_cliente, empresa_id=empresa_id, conversa_id=conversa_id)
    if not melhor_regra or not melhor_regra["fluxo_id"]:
        return None, None
    if not fluxo_pertence_empresa(melhor_regra["fluxo_id"], empresa_id):
        return None, None
    if conversa_id:
        aplicar_acoes_regra(conversa_id, melhor_regra)
        registrar_evento(
            "regra_fluxo_acionada",
            referencia_id=melhor_regra["id"],
            valor=melhor_regra["nome"],
            empresa_id=empresa_id or obter_empresa_id_da_conversa(conversa_id)
        )
    return melhor_regra["fluxo_id"], melhor_regra["id"]


# =========================================================
# HELPERS DE FLUXOS
# =========================================================
def buscar_fluxos_empresa(empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return []

    conn = get_connection()
    fluxos = conn.execute(
        """
        SELECT *
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY atualizado_em DESC, id DESC
        """,
        (empresa_id,)
    ).fetchall()
    conn.close()
    return fluxos


def buscar_fluxo(fluxo_id, empresa_id=None):
    empresa_id = empresa_id or obter_empresa_id_logada()
    if not empresa_id:
        return None

    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT *
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, empresa_id)
    ).fetchone()
    conn.close()
    return fluxo


def buscar_blocos_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    if empresa_id and not fluxo_pertence_empresa(fluxo_id, empresa_id):
        return []

    conn = get_connection()
    blocos = conn.execute(
        """
        SELECT *
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        ORDER BY ordem ASC, id ASC
        """,
        (fluxo_id,)
    ).fetchall()
    conn.close()
    return blocos


def buscar_primeiro_bloco_fluxo(fluxo_id):
    empresa_id = obter_empresa_id_logada()
    if empresa_id and not fluxo_pertence_empresa(fluxo_id, empresa_id):
        return None

    conn = get_connection()
    bloco = conn.execute(
        """
        SELECT *
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        ORDER BY ordem ASC, id ASC
        LIMIT 1
        """,
        (fluxo_id,)
    ).fetchone()
    conn.close()
    return bloco


def buscar_bloco_por_id(bloco_id):
    if not bloco_id:
        return None

    fluxo_id = fluxo_id_do_bloco(bloco_id)
    empresa_id = obter_empresa_id_logada()
    if empresa_id and fluxo_id and not fluxo_pertence_empresa(fluxo_id, empresa_id):
        return None

    conn = get_connection()
    bloco = conn.execute(
        """
        SELECT *
        FROM fluxo_blocos
        WHERE id = ?
        """,
        (bloco_id,)
    ).fetchone()
    conn.close()
    return bloco


def parse_config_json(config_json):
    if not config_json:
        return {}
    try:
        return json.loads(config_json)
    except Exception:
        return {}


def iniciar_fluxo_conversa(conversa_id, fluxo_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    empresa_id = obter_empresa_id_da_conversa(conversa_id) or obter_empresa_id_logada()
    fluxo = buscar_fluxo(fluxo_id, empresa_id)
    if not fluxo or int(fluxo["ativo"] or 0) != 1:
        return None

    primeiro_bloco = buscar_primeiro_bloco_fluxo(fluxo_id)
    if not primeiro_bloco:
        return None

    atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id=fluxo_id, bloco_atual_id=primeiro_bloco["id"])
    atualizar_etapa_conversa(conversa_id, "fluxo")
    atualizar_contexto_parcial(conversa_id, {"fluxo_nome": fluxo["nome"]})
    registrar_evento("fluxo_iniciado", referencia_id=fluxo_id, valor=f"conversa:{conversa_id}", empresa_id=empresa_id)
    registrar_execucao_fluxo(conversa_id, fluxo_id, primeiro_bloco["id"], "inicio", "Fluxo iniciado")

    return primeiro_bloco


def buscar_proximo_bloco(bloco_atual, resposta_cliente=None):
    if not bloco_atual:
        return None

    config = parse_config_json(bloco_atual["config_json"])
    tipo_bloco = (bloco_atual["tipo_bloco"] or "").strip().lower()

    if tipo_bloco == "multipla_escolha":
        opcoes = config.get("opcoes", [])
        resposta_norm = normalizar_texto(resposta_cliente or "")

        for opcao in opcoes:
            gatilho = normalizar_texto(opcao.get("gatilho", ""))
            if gatilho and gatilho == resposta_norm:
                proximo_id = opcao.get("proximo_bloco_id")
                if proximo_id and bloco_pertence_fluxo(proximo_id, bloco_atual["fluxo_id"]):
                    return buscar_bloco_por_id(proximo_id)

    proximo_id = bloco_atual["proximo_bloco_id"]
    if proximo_id and bloco_pertence_fluxo(proximo_id, bloco_atual["fluxo_id"]):
        return buscar_bloco_por_id(proximo_id)

    return None


def finalizar_fluxo_conversa(conversa_id):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    fluxo_atual = fluxo_id_ativo_da_conversa(conversa_id)
    empresa_id = obter_empresa_id_da_conversa(conversa_id)
    atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id=None, bloco_atual_id=None)
    atualizar_etapa_conversa(conversa_id, None)

    contexto = buscar_contexto_conversa(conversa_id)
    contexto.pop("fluxo_nome", None)
    atualizar_contexto_conversa(conversa_id, contexto)
    registrar_evento("fluxo_finalizado", referencia_id=conversa_id, empresa_id=empresa_id)
    registrar_execucao_fluxo(conversa_id, fluxo_atual, None, "fim", "Fluxo finalizado")


def executar_bloco_fluxo(conversa_id, bloco, mensagem_cliente=None):
    if not conversa_acessivel_na_sessao(conversa_id):
        return None

    if not bloco:
        finalizar_fluxo_conversa(conversa_id)
        return None

    tipo_bloco = (bloco["tipo_bloco"] or "").strip().lower()
    conteudo = (bloco["conteudo"] or "").strip()
    config = parse_config_json(bloco["config_json"])
    registrar_execucao_fluxo(
        conversa_id,
        fluxo_id_ativo_da_conversa(conversa_id),
        bloco["id"],
        "bloco_executado",
        json.dumps({"tipo_bloco": tipo_bloco}, ensure_ascii=False)
    )

    if tipo_bloco == "mensagem":
        proximo = buscar_proximo_bloco(bloco)
        if proximo:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
        else:
            finalizar_fluxo_conversa(conversa_id)
        return conteudo or "Mensagem do fluxo."

    if tipo_bloco == "pergunta":
        atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), bloco["id"])
        return conteudo or "Me responda para continuar."

    if tipo_bloco == "multipla_escolha":
        if mensagem_cliente is None:
            return conteudo or "Escolha uma opção."

        proximo = buscar_proximo_bloco(bloco, resposta_cliente=mensagem_cliente)
        if proximo:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
            return executar_bloco_fluxo(conversa_id, proximo)
        return "Não entendi sua escolha. Me responda usando uma das opções do menu."

    if tipo_bloco == "coletar_nome":
        if mensagem_cliente is None:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), bloco["id"])
            return conteudo or "Qual é o seu nome?"

        salvar_nome_contato_conversa(conversa_id, mensagem_cliente)
        proximo = buscar_proximo_bloco(bloco)
        if proximo:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
            return executar_bloco_fluxo(conversa_id, proximo)
        finalizar_fluxo_conversa(conversa_id)
        return "Perfeito 💖 Nome salvo."

    if tipo_bloco == "coletar_telefone":
        if mensagem_cliente is None:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), bloco["id"])
            return conteudo or "Qual é o seu telefone?"

        salvar_telefone_contato_conversa(conversa_id, mensagem_cliente)
        proximo = buscar_proximo_bloco(bloco)
        if proximo:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
            return executar_bloco_fluxo(conversa_id, proximo)
        finalizar_fluxo_conversa(conversa_id)
        return "Perfeito 💖 Telefone salvo."

    if tipo_bloco == "transferir_humano":
        conn = get_connection()
        conn.execute(
            """
            UPDATE conversas
            SET bot_ativo = 0,
                atualizada_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (conversa_id,)
        )
        conn.commit()
        conn.close()
        salvar_status_atendimento(conversa_id, "em_atendimento", atendente_nome=session.get("user_nome"))
        registrar_evento("fluxo_transferencia_humano", referencia_id=conversa_id)
        finalizar_fluxo_conversa(conversa_id)
        return conteudo or "Perfeito 🤍 Vou encaminhar você para um atendente."

    if tipo_bloco == "encerrar":
        finalizar_fluxo_conversa(conversa_id)
        return conteudo or "Atendimento encerrado 💖"

    if tipo_bloco == "acao":
        acao = (config.get("acao") or "").strip().lower()

        if acao == "salvar_agendamento":
            contexto = buscar_contexto_conversa(conversa_id)
            sucesso_agendamento, resultado_agendamento = salvar_agendamento(
                conversa_id,
                contexto.get("data"),
                contexto.get("horario"),
                contexto.get("servico")
            )
            if not sucesso_agendamento and resultado_agendamento:
                return f"Não consegui salvar o agendamento: {resultado_agendamento}"

        proximo = buscar_proximo_bloco(bloco)
        if proximo:
            atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
            return executar_bloco_fluxo(conversa_id, proximo)
        finalizar_fluxo_conversa(conversa_id)
        return conteudo or "Ação executada."

    proximo = buscar_proximo_bloco(bloco)
    if proximo:
        atualizar_fluxo_ativo_conversa(conversa_id, fluxo_id_ativo_da_conversa(conversa_id), proximo["id"])
    else:
        finalizar_fluxo_conversa(conversa_id)

    return conteudo or "Fluxo executado."


def fluxo_id_ativo_da_conversa(conversa_id):
    dados = buscar_fluxo_ativo_conversa(conversa_id)
    if dados:
        return dados["fluxo_id_ativo"]
    return None


def processar_fluxo_conversa(conversa_id, mensagem_cliente=None):
    estado = buscar_fluxo_ativo_conversa(conversa_id)
    if not estado or not estado["fluxo_id_ativo"] or not estado["bloco_atual_id"]:
        registrar_execucao_fluxo(conversa_id, None, None, "fallback_sem_estado", "Sem estado de fluxo ativo")
        return None

    bloco_atual = buscar_bloco_por_id(estado["bloco_atual_id"])
    if not bloco_atual or not bloco_pertence_fluxo(estado["bloco_atual_id"], estado["fluxo_id_ativo"]):
        registrar_execucao_fluxo(conversa_id, estado["fluxo_id_ativo"], estado["bloco_atual_id"], "fallback_bloco_invalido", "Bloco atual não encontrado")
        finalizar_fluxo_conversa(conversa_id)
        return None

    tipo_bloco = (bloco_atual["tipo_bloco"] or "").strip().lower()

    if tipo_bloco in ["pergunta", "coletar_nome", "coletar_telefone"]:
        if mensagem_cliente is None:
            return executar_bloco_fluxo(conversa_id, bloco_atual)
        proximo = buscar_proximo_bloco(bloco_atual, resposta_cliente=mensagem_cliente)
        if tipo_bloco == "pergunta":
            if mensagem_cliente:
                atualizar_contexto_parcial(conversa_id, {f"resposta_bloco_{bloco_atual['id']}": mensagem_cliente.strip()})
            if proximo:
                atualizar_fluxo_ativo_conversa(conversa_id, estado["fluxo_id_ativo"], proximo["id"])
                return executar_bloco_fluxo(conversa_id, proximo)
            finalizar_fluxo_conversa(conversa_id)
            return "Perfeito 💖"

        return executar_bloco_fluxo(conversa_id, bloco_atual, mensagem_cliente=mensagem_cliente)

    if tipo_bloco == "multipla_escolha":
        if mensagem_cliente is None:
            return executar_bloco_fluxo(conversa_id, bloco_atual)
        return executar_bloco_fluxo(conversa_id, bloco_atual, mensagem_cliente=mensagem_cliente)

    return executar_bloco_fluxo(conversa_id, bloco_atual, mensagem_cliente=mensagem_cliente)


def salvar_nome_contato_conversa(conversa_id, nome):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE contatos
        SET nome = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = (
            SELECT contato_id FROM conversas WHERE id = ?
        )
          AND empresa_id = (
              SELECT empresa_id FROM conversas WHERE id = ?
          )
        """,
        ((nome or "").strip(), conversa_id, conversa_id)
    )
    conn.commit()
    conn.close()


def salvar_telefone_contato_conversa(conversa_id, telefone):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conn.execute(
        """
        UPDATE contatos
        SET telefone = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE id = (
            SELECT contato_id FROM conversas WHERE id = ?
        )
          AND empresa_id = (
              SELECT empresa_id FROM conversas WHERE id = ?
          )
        """,
        ((telefone or "").strip(), conversa_id, conversa_id)
    )
    conn.commit()
    conn.close()


def serializar_bloco(bloco_row):
    bloco = dict(bloco_row)
    bloco["config"] = parse_config_json(bloco.get("config_json"))
    return bloco


def remapear_config_bloco_fluxo(config_json, mapa_ids):
    config = parse_config_json(config_json)
    if not config:
        return json.dumps(config, ensure_ascii=False)

    opcoes = config.get("opcoes")
    if isinstance(opcoes, list):
        for opcao in opcoes:
            if not isinstance(opcao, dict):
                continue

            proximo_id = opcao.get("proximo_bloco_id")
            try:
                proximo_id_int = int(proximo_id) if proximo_id is not None else None
            except (TypeError, ValueError):
                proximo_id_int = None

            if proximo_id_int in mapa_ids:
                opcao["proximo_bloco_id"] = mapa_ids[proximo_id_int]

    return json.dumps(config, ensure_ascii=False)


# =========================================================
# MENU AUTOMÁTICO
# =========================================================
def montar_menu_principal():
    return (
        "Olá 💖 Seja muito bem-vindo(a)!\n\n"
        "Digite uma opção para continuar:\n"
        "1 - Valores\n"
        "2 - Agendamento\n"
        "3 - Localização\n"
        "4 - Formas de pagamento\n\n"
        "Se preferir, também pode escrever sua dúvida normalmente."
    )


def resposta_menu_por_opcao(texto_normalizado):
    mapa = {
        "1": "Claro 💖 Vou te ajudar com os valores. Me diz qual serviço você quer consultar que eu te explico certinho.",
        "2": "Perfeito ✨ Vou te ajudar com o agendamento. Me fala qual dia ou horário você prefere.",
        "3": "Claro 📍 Vou te passar a localização certinho. Você prefere vir até o espaço ou atendimento a domicílio?",
        "4": "Sem problema 💳 Hoje trabalhamos com Pix, cartão e dinheiro. Se quiser, também já posso te orientar sobre agendamento."
    }

    return mapa.get(texto_normalizado)


def eh_pedido_de_menu(texto_normalizado):
    gatilhos = [
        "menu",
        "oi",
        "ola",
        "bom dia",
        "boa tarde",
        "boa noite",
        "inicio",
        "comecar",
        "voltar",
        "iniciar"
    ]
    return texto_normalizado in gatilhos


# =========================================================
# IA / MEMÓRIA
# =========================================================
def ia_habilitada():
    return bool(Config.OPENAI_API_KEY and Config.OPENAI_MODEL)


def classificar_intencao(texto_normalizado):
    if texto_normalizado in ["1"]:
        return "valores"
    if texto_normalizado in ["2"]:
        return "agendamento"
    if texto_normalizado in ["3"]:
        return "localizacao"
    if texto_normalizado in ["4"]:
        return "pagamento"

    if any(p in texto_normalizado for p in ["preco", "valor", "quanto custa", "orcamento", "investimento"]):
        return "valores"

    if any(p in texto_normalizado for p in ["agendar", "agenda", "horario", "horário", "marcar", "disponibilidade"]):
        return "agendamento"

    if any(p in texto_normalizado for p in ["endereco", "endereço", "onde fica", "localizacao", "localização", "local"]):
        return "localizacao"

    if any(p in texto_normalizado for p in ["pagamento", "forma de pagamento", "pix", "cartao", "cartão", "dinheiro"]):
        return "pagamento"

    if any(p in texto_normalizado for p in ["atendente", "humano", "pessoa", "falar com alguem", "falar com alguém"]):
        return "humano"

    return None


def buscar_historico_conversa_ia(conversa_id, limite=12):
    if not conversa_acessivel_na_sessao(conversa_id):
        return []

    conn = get_connection()
    mensagens = conn.execute(
        """
        SELECT remetente_tipo, conteudo, criado_em
        FROM mensagens
        WHERE conversa_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (conversa_id, limite)
    ).fetchall()
    conn.close()

    historico = []
    for mensagem in reversed(mensagens):
        role = "assistant" if mensagem["remetente_tipo"] == "bot" else "user"
        historico.append({
            "role": role,
            "content": (mensagem["conteudo"] or "").strip()
        })

    return historico


def buscar_memoria_cliente(conversa_id):
    if not conversa_id:
        return {}
    if not conversa_acessivel_na_sessao(conversa_id):
        return {}

    conn = get_connection()
    memoria = conn.execute(
        """
        SELECT cm.*
        FROM cliente_memorias cm
        JOIN conversas c ON c.contato_id = cm.contato_id AND c.empresa_id = cm.empresa_id
        WHERE c.id = ?
        LIMIT 1
        """,
        (conversa_id,)
    ).fetchone()
    conn.close()

    if not memoria:
        return {}

    dados = dict(memoria)
    for campo in ["preferencias_json", "contexto_json"]:
        try:
            dados[campo] = json.loads(dados.get(campo) or "{}")
        except Exception:
            dados[campo] = {}
    return dados


def montar_prompt_sistema_ia(conversa_id=None):
    empresa_prompt_id = None
    if conversa_id and conversa_acessivel_na_sessao(conversa_id):
        empresa_prompt_id = obter_empresa_id_da_conversa(conversa_id)
    nome_empresa = buscar_nome_empresa(empresa_prompt_id)

    base = (
        f"Você é a atendente virtual da empresa {nome_empresa}. "
        "Você responde como uma atendente profissional de WhatsApp, em português do Brasil. "
        "Seu estilo deve ser humano, simpático, direto, elegante e útil. "
        "Nunca diga que é uma IA, a menos que perguntem diretamente. "
        "Priorize conversão, atendimento claro e continuidade natural da conversa. "
        "Se o cliente quiser preço, explique. "
        "Se quiser marcar horário, conduza com objetividade. "
        "Se não souber uma informação específica do negócio, não invente; diga de forma natural que pode confirmar."
    )

    if conversa_id:
        contexto = buscar_contexto_conversa(conversa_id)
        etapa = buscar_etapa_conversa(conversa_id)
        memoria_cliente = buscar_memoria_cliente(conversa_id)

        if contexto or etapa:
            base += f" Contexto atual da conversa: etapa={etapa}, contexto={json.dumps(contexto, ensure_ascii=False)}."
        if memoria_cliente:
            memoria_prompt = {
                "resumo": memoria_cliente.get("resumo"),
                "preferencias": memoria_cliente.get("preferencias_json") or {},
                "contexto": memoria_cliente.get("contexto_json") or {},
            }
            base += f" Memoria salva do cliente: {json.dumps(memoria_prompt, ensure_ascii=False)}."

    return base


def gerar_resposta_ia(mensagem_cliente, conversa_id=None):
    if not ia_habilitada():
        return (
            "Entendi 💖 Recebi sua mensagem.\n\n"
            "Você também pode usar o menu:\n"
            "1 - Valores\n"
            "2 - Agendamento\n"
            "3 - Localização\n"
            "4 - Formas de pagamento"
        )

    mensagens = [
        {"role": "system", "content": montar_prompt_sistema_ia(conversa_id)}
    ]

    if conversa_id:
        mensagens.extend(buscar_historico_conversa_ia(conversa_id, limite=10))

    mensagens.append({"role": "user", "content": mensagem_cliente})

    try:
        resposta = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": Config.OPENAI_MODEL,
                "messages": mensagens,
                "temperature": 0.7
            },
            timeout=30
        )
        resposta.raise_for_status()
        data = resposta.json()

        conteudo = data["choices"][0]["message"]["content"].strip()
        return conteudo or (
            "Entendi 💖 Me fala um pouco mais para eu te responder melhor."
        )
    except Exception:
        return (
            "Tive uma instabilidade aqui 💖\n\n"
            "Pode repetir sua mensagem ou usar o menu:\n"
            "1 - Valores\n"
            "2 - Agendamento\n"
            "3 - Localização\n"
            "4 - Formas de pagamento"
        )


def atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_bot=None):
    if not conversa_id:
        return

    contexto = buscar_contexto_conversa(conversa_id)
    texto = normalizar_texto(mensagem_cliente)

    intencao = classificar_intencao(texto)
    if intencao:
        contexto["ultima_intencao"] = intencao

    contexto["ultima_mensagem_cliente"] = mensagem_cliente.strip()

    if resposta_bot:
        contexto["ultima_resposta_bot"] = resposta_bot.strip()

    atualizar_contexto_conversa(conversa_id, contexto)
    atualizar_memoria_cliente(conversa_id, contexto, mensagem_cliente, resposta_bot)


def atualizar_memoria_cliente(conversa_id, contexto_conversa=None, mensagem_cliente=None, resposta_bot=None):
    if not conversa_acessivel_na_sessao(conversa_id):
        return

    conn = get_connection()
    conversa = conn.execute(
        """
        SELECT empresa_id, contato_id
        FROM conversas
        WHERE id = ?
        """,
        (conversa_id,)
    ).fetchone()
    if not conversa:
        conn.close()
        return

    memoria_atual = conn.execute(
        """
        SELECT resumo, preferencias_json, contexto_json
        FROM cliente_memorias
        WHERE empresa_id = ? AND contato_id = ?
        LIMIT 1
        """,
        (conversa["empresa_id"], conversa["contato_id"])
    ).fetchone()

    preferencias = {}
    contexto_memoria = {}
    resumo = ""
    if memoria_atual:
        resumo = memoria_atual["resumo"] or ""
        try:
            preferencias = json.loads(memoria_atual["preferencias_json"] or "{}")
        except Exception:
            preferencias = {}
        try:
            contexto_memoria = json.loads(memoria_atual["contexto_json"] or "{}")
        except Exception:
            contexto_memoria = {}

    contexto_conversa = contexto_conversa or buscar_contexto_conversa(conversa_id)
    for chave in ["servico", "data", "ultima_intencao"]:
        if contexto_conversa.get(chave):
            contexto_memoria[chave] = contexto_conversa.get(chave)

    texto = normalizar_texto(mensagem_cliente or "")
    if "prefiro" in texto or "preferencia" in texto or "preferência" in texto:
        preferencias["observacao"] = (mensagem_cliente or "").strip()[:280]

    partes_resumo = []
    if contexto_memoria.get("ultima_intencao"):
        partes_resumo.append(f"Intencao recente: {contexto_memoria['ultima_intencao']}")
    if contexto_memoria.get("servico"):
        partes_resumo.append(f"Servico de interesse: {contexto_memoria['servico']}")
    if contexto_memoria.get("data"):
        partes_resumo.append(f"Data mencionada: {contexto_memoria['data']}")
    if mensagem_cliente:
        partes_resumo.append(f"Ultima fala do cliente: {(mensagem_cliente or '').strip()[:180]}")
    if resposta_bot:
        partes_resumo.append(f"Ultima resposta enviada: {(resposta_bot or '').strip()[:180]}")
    novo_resumo = " | ".join(partes_resumo)[:900] or resumo

    conn.execute(
        """
        INSERT INTO cliente_memorias (
            empresa_id, contato_id, resumo, preferencias_json, contexto_json, atualizado_em
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(empresa_id, contato_id) DO UPDATE SET
            resumo = excluded.resumo,
            preferencias_json = excluded.preferencias_json,
            contexto_json = excluded.contexto_json,
            atualizado_em = CURRENT_TIMESTAMP
        """,
        (
            conversa["empresa_id"],
            conversa["contato_id"],
            novo_resumo,
            json.dumps(preferencias, ensure_ascii=False),
            json.dumps(contexto_memoria, ensure_ascii=False),
        )
    )
    conn.commit()
    conn.close()


# =========================================================
# BOT INTELIGENTE
# =========================================================
def gerar_resposta_bot(mensagem_cliente, conversa_id=None):
    if not mensagem_cliente:
        if conversa_id:
            estado = buscar_fluxo_ativo_conversa(conversa_id)
            if estado and estado["fluxo_id_ativo"]:
                resposta_fluxo = processar_fluxo_conversa(conversa_id)
                if resposta_fluxo:
                    return resposta_fluxo, None

            atualizar_etapa_conversa(conversa_id, "menu")
            atualizar_contexto_conversa(conversa_id, {})
        return montar_menu_principal(), None

    texto = normalizar_texto(mensagem_cliente)
    etapa = buscar_etapa_conversa(conversa_id) if conversa_id else None
    contexto = buscar_contexto_conversa(conversa_id) if conversa_id else {}

    if conversa_id:
        estado_fluxo = buscar_fluxo_ativo_conversa(conversa_id)
        if estado_fluxo and estado_fluxo["fluxo_id_ativo"]:
            resposta_fluxo = processar_fluxo_conversa(conversa_id, mensagem_cliente=mensagem_cliente)
            if resposta_fluxo:
                atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_fluxo)
                return resposta_fluxo, None

    fluxo_id_regra, regra_fluxo_id = buscar_fluxo_por_regra(mensagem_cliente, conversa_id=conversa_id)
    if conversa_id and fluxo_id_regra:
        primeiro_bloco = iniciar_fluxo_conversa(conversa_id, fluxo_id_regra)
        if primeiro_bloco:
            resposta_fluxo = executar_bloco_fluxo(conversa_id, primeiro_bloco)
            atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_fluxo)
            return resposta_fluxo, regra_fluxo_id

    intencao_atual = classificar_intencao(texto)

    if etapa in ["agendamento_dia", "agendamento_horario"] and intencao_atual in ["valores", "localizacao", "pagamento", "humano"]:
        limpar_fluxo_conversa(conversa_id)
        etapa = None
        contexto = {}

    if etapa == "valores" and intencao_atual in ["agendamento", "localizacao", "pagamento", "humano"]:
        limpar_fluxo_conversa(conversa_id)
        etapa = None
        contexto = {}

    if eh_pedido_de_menu(texto):
        if conversa_id:
            atualizar_etapa_conversa(conversa_id, "menu")
            atualizar_contexto_conversa(conversa_id, {})
        resposta = montar_menu_principal()
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if texto == "1":
        if conversa_id:
            atualizar_etapa_conversa(conversa_id, "valores")
            atualizar_contexto_conversa(conversa_id, {})
        resposta = "Claro 💖 Me diga qual serviço você quer saber o valor."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if texto == "2":
        if conversa_id:
            atualizar_etapa_conversa(conversa_id, "agendamento_dia")
            atualizar_contexto_conversa(conversa_id, {})
        resposta = "Perfeito ✨ Me fala o DIA que você quer agendar."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if texto == "3":
        if conversa_id:
            limpar_fluxo_conversa(conversa_id)
        resposta = resposta_menu_por_opcao(texto)
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if texto == "4":
        if conversa_id:
            limpar_fluxo_conversa(conversa_id)
        resposta = resposta_menu_por_opcao(texto)
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if etapa == "valores":
        if conversa_id:
            atualizar_contexto_parcial(conversa_id, {"servico": mensagem_cliente.strip()})

        resposta_regra, regra_id = buscar_resposta_por_regras(mensagem_cliente, conversa_id=conversa_id)
        if resposta_regra:
            atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_regra)
            return resposta_regra, regra_id

        resposta = (
            f"Perfeito 💖 Sobre '{mensagem_cliente}', posso te passar mais detalhes ou já te ajudar a agendar.\n\n"
            "Se quiser agendar, digite 2."
        )
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if etapa == "agendamento_dia":
        data_normalizada, erro_data = normalizar_data_agendamento(mensagem_cliente)
        if erro_data:
            resposta_erro = f"Não consegui entender a data: {erro_data}"
            atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_erro)
            return resposta_erro, None
        if datetime.strptime(data_normalizada, "%Y-%m-%d").date() < datetime.now().date():
            resposta_erro = "Não é possível agendar em uma data passada."
            atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_erro)
            return resposta_erro, None

        novo_contexto = dict(contexto)
        novo_contexto["data"] = data_normalizada

        if conversa_id:
            atualizar_contexto_conversa(conversa_id, novo_contexto)
            atualizar_etapa_conversa(conversa_id, "agendamento_horario")

        resposta = (
            f"Perfeito 💖 Agendamento para {data_normalizada}.\n\n"
            "Agora me fala o HORÁRIO que você prefere 😊"
        )
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if etapa == "agendamento_horario":
        data_agendamento = contexto.get("data", "Data não informada")
        horario_agendamento = mensagem_cliente.strip()
        servico_agendamento = contexto.get("servico")
        agendamento_confirmado = {"data": data_agendamento, "horario": horario_agendamento}

        if conversa_id:
            sucesso_agendamento, resultado_agendamento = salvar_agendamento(
                conversa_id,
                data_agendamento,
                horario_agendamento,
                servico_agendamento
            )
            if not sucesso_agendamento and resultado_agendamento:
                resposta_erro = f"Não consegui confirmar: {resultado_agendamento}"
                atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_erro)
                return resposta_erro, None
            if isinstance(resultado_agendamento, dict):
                agendamento_confirmado = resultado_agendamento
            limpar_fluxo_conversa(conversa_id)

        resposta = (
            "Perfeito ✨ Agendamento confirmado!\n\n"
            f"📅 {agendamento_confirmado['data']}\n"
            f"⏰ {agendamento_confirmado['horario']}\n\n"
            "Se precisar de mais alguma coisa, estou por aqui 💖"
        )
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    resposta_regra, regra_id = buscar_resposta_por_regras(mensagem_cliente, conversa_id=conversa_id)
    if resposta_regra:
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_regra)
        return resposta_regra, regra_id

    if intencao_atual == "valores":
        if conversa_id:
            atualizar_etapa_conversa(conversa_id, "valores")
            atualizar_contexto_conversa(conversa_id, {})
        resposta = "Claro 💖 Vou te ajudar com os valores sim. Me diz qual serviço você quer que eu te explico certinho."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if intencao_atual == "agendamento":
        if conversa_id:
            atualizar_etapa_conversa(conversa_id, "agendamento_dia")
            atualizar_contexto_conversa(conversa_id, {})
        resposta = "Perfeito ✨ Vou te ajudar com o agendamento. Me fala qual dia ou horário você prefere."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if intencao_atual == "localizacao":
        if conversa_id:
            limpar_fluxo_conversa(conversa_id)
        resposta = "Claro 📍 Vou te passar a localização certinho. Você prefere vir até o espaço ou atendimento a domicílio?"
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if intencao_atual == "pagamento":
        if conversa_id:
            limpar_fluxo_conversa(conversa_id)
        resposta = "Sem problema 💳 Posso te informar as formas de pagamento sim. Hoje trabalhamos com Pix, cartão e dinheiro. Se quiser, também já posso te orientar sobre agendamento."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    if intencao_atual == "humano":
        if conversa_id:
            limpar_fluxo_conversa(conversa_id)
        resposta = "Sem problemas 🤍 Vou direcionar seu atendimento para o time responsável."
        atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta)
        return resposta, None

    resposta_ia = gerar_resposta_ia(mensagem_cliente, conversa_id)
    atualizar_memoria_basica(conversa_id, mensagem_cliente, resposta_ia)
    return resposta_ia, None


# =========================================================
# CONTEXTO GLOBAL DOS TEMPLATES
# =========================================================
@app.context_processor
def inject_user_context():
    empresas_usuario = buscar_empresas_do_usuario(obter_user_id_logado()) if usuario_logado() else []
    return {
        "usuario_logado": usuario_logado(),
        "nome_empresa_logada": buscar_nome_empresa() if usuario_logado() else None,
        "user_email_logado": session.get("user_email"),
        "user_nome_logado": session.get("user_nome"),
        "empresas_usuario": empresas_usuario,
    }


# =========================================================
# LOGIN / CADASTRO / LOGOUT
# =========================================================
@app.route("/", methods=["GET", "POST"])
def login():
    if usuario_logado():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = (request.form.get("senha") or "").strip()

        if not email or not senha:
            flash("Preencha e-mail e senha.", "erro")
            return render_template("login.html", email=email)

        usuario = buscar_usuario_por_email(email)

        if not usuario:
            flash("Usuário não encontrado.", "erro")
            return render_template("login.html", email=email)

        if not senha_confere(senha, usuario["senha_hash"]):
            flash("Senha inválida.", "erro")
            return render_template("login.html", email=email)

        empresa = buscar_empresa_do_usuario(usuario["id"])

        if not empresa:
            flash("Usuário sem empresa vinculada.", "erro")
            return render_template("login.html", email=email)

        session["user_id"] = usuario["id"]
        session["user_nome"] = usuario["nome"]
        session["user_email"] = usuario["email"]
        session["empresa_id"] = empresa["id"]
        session["empresa_nome"] = empresa["nome_exibicao"] or empresa["nome_empresa"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if usuario_logado():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        empresa_nome = (request.form.get("empresa") or "").strip()
        senha = (request.form.get("senha") or "").strip()

        if not nome or not email or not empresa_nome or not senha:
            flash("Preencha todos os campos.", "erro")
            return render_template(
                "cadastro.html",
                nome=nome,
                email=email,
                empresa=empresa_nome
            )

        conn = get_connection()

        usuario_existente = conn.execute(
            """
            SELECT id
            FROM users
            WHERE lower(email) = ?
            LIMIT 1
            """,
            (email,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            flash("Esse e-mail já está cadastrado.", "erro")
            return render_template(
                "cadastro.html",
                nome=nome,
                email=email,
                empresa=empresa_nome
            )

        senha_hash = gerar_hash_senha(senha)

        cursor = conn.execute(
            """
            INSERT INTO users (nome, email, senha_hash)
            VALUES (?, ?, ?)
            """,
            (nome, email, senha_hash)
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """
            INSERT INTO empresas (user_id, nome_empresa, nome_exibicao, email)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, empresa_nome, empresa_nome, email)
        )
        empresa_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo)
            VALUES (?, ?, 'owner', 1)
            """,
            (empresa_id, user_id)
        )

        conn.commit()
        conn.close()

        session["user_id"] = user_id
        session["user_nome"] = nome
        session["user_email"] = email
        session["empresa_id"] = empresa_id
        session["empresa_nome"] = empresa_nome

        return redirect(url_for("dashboard"))

    return render_template("cadastro.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================
@app.route("/dashboard")
@login_required
def dashboard():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()

    total_contatos = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    total_conversas = conn.execute(
        "SELECT COUNT(*) AS total FROM conversas WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    conversas_abertas = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM conversas
        WHERE empresa_id = ? AND status = 'aberta'
        """,
        (empresa_id,)
    ).fetchone()["total"]

    conversas_fechadas = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM conversas
        WHERE empresa_id = ? AND status = 'fechada'
        """,
        (empresa_id,)
    ).fetchone()["total"]

    total_mensagens = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens
        WHERE conversa_id IN (
            SELECT id FROM conversas WHERE empresa_id = ?
        )
        """,
        (empresa_id,)
    ).fetchone()["total"]

    agendamentos_criados = conn.execute(
        "SELECT COUNT(*) AS total FROM agendamentos WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    mensagens_humano = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens
        WHERE remetente_tipo = 'humano'
          AND conversa_id IN (SELECT id FROM conversas WHERE empresa_id = ?)
        """,
        (empresa_id,)
    ).fetchone()["total"]

    integracoes_ativas = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM canal_integracoes
        WHERE empresa_id = ? AND status = 'ativo'
        """,
        (empresa_id,)
    ).fetchone()["total"]

    regras_acionadas = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM metricas_eventos
        WHERE empresa_id = ? AND tipo_evento IN ('regra_acionada', 'regra_fluxo_acionada')
        """,
        (empresa_id,)
    ).fetchone()["total"]

    fluxos_iniciados = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM metricas_eventos
        WHERE empresa_id = ? AND tipo_evento = 'fluxo_iniciado'
        """,
        (empresa_id,)
    ).fetchone()["total"]

    atividade_recente = conn.execute(
        """
        SELECT tipo_evento, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
        ORDER BY id DESC
        LIMIT 6
        """,
        (empresa_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_contatos=total_contatos,
        total_conversas=total_conversas,
        conversas_abertas=conversas_abertas,
        conversas_fechadas=conversas_fechadas,
        total_mensagens=total_mensagens,
        agendamentos_criados=agendamentos_criados,
        mensagens_humano=mensagens_humano,
        integracoes_ativas=integracoes_ativas,
        regras_acionadas=regras_acionadas,
        fluxos_iniciados=fluxos_iniciados,
        atividade_recente=atividade_recente,
    )


# =========================================================
# CONVERSAS
# =========================================================
@app.route("/conversas")
@login_required
def conversas():
    empresa_id = obter_empresa_id_logada()
    busca = (request.args.get("busca") or "").strip()
    status = (request.args.get("status") or "").strip()
    bot = (request.args.get("bot") or "").strip()
    atendimento = (request.args.get("atendimento") or "").strip()
    tag_id = (request.args.get("tag_id") or "").strip()
    somente_humano = (request.args.get("somente_humano") or "").strip() == "1"
    if tag_id.isdigit() and not tag_pertence_empresa(int(tag_id), empresa_id):
        tag_id = ""

    conn = get_connection()

    query = """
        SELECT
            c.id,
            c.status,
            c.bot_ativo,
            c.atendente_nome,
            c.etapa,
            c.fluxo_id_ativo,
            c.bloco_atual_id,
            c.iniciada_em,
            c.atualizada_em,
            c.contexto_json,
            f.nome AS fluxo_nome,
            ct.id AS contato_id,
            ct.nome AS contato_nome,
            ct.telefone AS contato_telefone
        FROM conversas c
        LEFT JOIN contatos ct ON ct.id = c.contato_id AND ct.empresa_id = c.empresa_id
        LEFT JOIN fluxos f ON f.id = c.fluxo_id_ativo AND f.empresa_id = c.empresa_id
        WHERE c.empresa_id = ?
    """
    params = [empresa_id]
    if busca:
        query += " AND (lower(coalesce(ct.nome, '')) LIKE ? OR replace(coalesce(ct.telefone, ''), ' ', '') LIKE ?)"
        busca_like = f"%{busca.lower()}%"
        busca_tel = f"%{busca.replace(' ', '')}%"
        params.extend([busca_like, busca_tel])
    if status in ["aberta", "fechada"]:
        query += " AND c.status = ?"
        params.append(status)
    if bot == "ativo":
        query += " AND c.bot_ativo = 1"
    elif bot == "pausado":
        query += " AND c.bot_ativo = 0"
    tag_id_valida = int(tag_id) if tag_id.isdigit() and tag_pertence_empresa(int(tag_id), empresa_id) else None
    if tag_id_valida:
        query += " AND ct.id IN (SELECT contato_id FROM contato_tags WHERE tag_id = ?)"
        params.append(tag_id_valida)
    query += " ORDER BY c.atualizada_em DESC, c.id DESC"

    conversas_db = conn.execute(query, tuple(params)).fetchall()

    contatos = conn.execute(
        """
        SELECT *
        FROM contatos
        WHERE empresa_id = ?
        ORDER BY id DESC
        """,
        (empresa_id,)
    ).fetchall()
    tags = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (empresa_id,)
    ).fetchall()

    conn.close()

    conversas_lista = []
    resumo_fila = {"total": 0, "em_atendimento": 0, "aguardando_cliente": 0, "no_bot": 0}
    for conversa in conversas_db:
        conversa_dict = dict(conversa)
        atendimento_status = obter_status_atendimento(conversa)
        conversa_dict["atendimento_status"] = atendimento_status
        conversa_dict["atendimento_status_label"] = {
            "bot": "No bot",
            "em_atendimento": "Em atendimento humano",
            "aguardando_cliente": "Aguardando cliente",
        }.get(atendimento_status, "No bot")
        conversa_dict["proxima_acao_label"] = {
            "bot": "Automação ativa para próxima mensagem",
            "em_atendimento": "Aguardando ação do atendente",
            "aguardando_cliente": "Aguardando retorno do cliente",
        }.get(atendimento_status, "Automação ativa")
        conversa_dict["ultima_mensagem"] = buscar_ultima_mensagem(conversa["id"])
        if atendimento_status == "em_atendimento":
            resumo_fila["em_atendimento"] += 1
        elif atendimento_status == "aguardando_cliente":
            resumo_fila["aguardando_cliente"] += 1
        else:
            resumo_fila["no_bot"] += 1

        if atendimento and atendimento_status != atendimento:
            continue
        if somente_humano and not conversa_dict.get("atendente_nome"):
            continue

        conversas_lista.append(conversa_dict)
    resumo_fila["total"] = len(conversas_lista)

    return render_template(
        "conversas.html",
        conversas=conversas_lista,
        contatos=contatos,
        tags=tags,
        resumo_fila=resumo_fila,
        filtros_conversa={
            "busca": busca,
            "status": status,
            "bot": bot,
            "atendimento": atendimento,
            "tag_id": tag_id_valida,
            "somente_humano": somente_humano,
        },
    )


@app.route("/conversas/exportar")
@login_required
def exportar_conversas():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()

    conversas_db = conn.execute(
        """
        SELECT
            c.id,
            c.status,
            c.bot_ativo,
            c.atendente_nome,
            c.etapa,
            c.iniciada_em,
            c.atualizada_em,
            f.nome AS fluxo_nome,
            ct.id AS contato_id,
            ct.nome AS contato_nome,
            ct.telefone AS contato_telefone
        FROM conversas c
        LEFT JOIN contatos ct ON ct.id = c.contato_id AND ct.empresa_id = c.empresa_id
        LEFT JOIN fluxos f ON f.id = c.fluxo_id_ativo AND f.empresa_id = c.empresa_id
        WHERE c.empresa_id = ?
        ORDER BY c.atualizada_em DESC, c.id DESC
        """,
        (empresa_id,)
    ).fetchall()

    conn.close()

    conversas_lista = []
    for conversa in conversas_db:
        conversa_dict = dict(conversa)
        conversa_dict["ultima_mensagem"] = buscar_ultima_mensagem(conversa["id"])
        conversas_lista.append(conversa_dict)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Status', 'Bot Ativo', 'Atendente Nome', 'Etapa', 'Iniciada em', 'Atualizada em', 'Fluxo Nome', 'Contato Nome', 'Contato Telefone', 'Última Mensagem'])

    for conversa in conversas_lista:
        writer.writerow([
            conversa['id'],
            conversa['status'] or '',
            'Sim' if conversa['bot_ativo'] else 'Não',
            conversa['atendente_nome'] or '',
            conversa['etapa'] or '',
            conversa['iniciada_em'] or '',
            conversa['atualizada_em'] or '',
            conversa['fluxo_nome'] or '',
            conversa['contato_nome'] or '',
            conversa['contato_telefone'] or '',
            conversa['ultima_mensagem'] or ''
        ])

    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=conversas.csv'
    }


@app.route("/conversas/contato/<int:contato_id>")
@login_required
def abrir_conversa_por_contato(contato_id):
    if not contato_pertence_empresa(contato_id):
        return redirect(url_for("conversas"))

    conversa_id = buscar_ou_criar_conversa(contato_id)
    if not conversa_id:
        return redirect(url_for("conversas"))

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>")
@login_required
def ver_conversa(conversa_id):
    empresa_id = obter_empresa_id_logada()
    busca = (request.args.get("busca") or "").strip()
    status = (request.args.get("status") or "").strip()
    bot = (request.args.get("bot") or "").strip()
    atendimento = (request.args.get("atendimento") or "").strip()
    tag_id = (request.args.get("tag_id") or "").strip()
    somente_humano = (request.args.get("somente_humano") or "").strip() == "1"
    if tag_id.isdigit() and not tag_pertence_empresa(int(tag_id), empresa_id):
        tag_id = ""

    conn = get_connection()

    conversa = conn.execute(
        """
        SELECT
            c.*,
            f.nome AS fluxo_nome,
            ct.nome AS contato_nome,
            ct.telefone AS contato_telefone
        FROM conversas c
        LEFT JOIN contatos ct ON ct.id = c.contato_id AND ct.empresa_id = c.empresa_id
        LEFT JOIN fluxos f ON f.id = c.fluxo_id_ativo AND f.empresa_id = c.empresa_id
        WHERE c.id = ? AND c.empresa_id = ?
        """,
        (conversa_id, empresa_id)
    ).fetchone()

    if not conversa:
        conn.close()
        return redirect(url_for("conversas"))

    mensagens = conn.execute(
        """
        SELECT
            m.*,
            r.nome AS regra_nome,
            u.nome AS user_nome
        FROM mensagens m
        LEFT JOIN regras r ON r.id = m.regra_id AND r.empresa_id = ?
        LEFT JOIN users u ON u.id = m.user_id
        WHERE m.conversa_id = ?
        ORDER BY m.id ASC
        """,
        (empresa_id, conversa_id)
    ).fetchall()

    conversas_db = conn.execute(
        """
        SELECT
            c.id,
            c.status,
            c.bot_ativo,
            c.atendente_nome,
            c.etapa,
            c.fluxo_id_ativo,
            c.bloco_atual_id,
            c.contexto_json,
            c.atualizada_em,
            f.nome AS fluxo_nome,
            ct.nome AS contato_nome,
            ct.telefone AS contato_telefone
        FROM conversas c
        LEFT JOIN contatos ct ON ct.id = c.contato_id AND ct.empresa_id = c.empresa_id
        LEFT JOIN fluxos f ON f.id = c.fluxo_id_ativo AND f.empresa_id = c.empresa_id
        WHERE c.empresa_id = ?
        ORDER BY c.atualizada_em DESC, c.id DESC
        """,
        (empresa_id,)
    ).fetchall()

    contatos = conn.execute(
        """
        SELECT *
        FROM contatos
        WHERE empresa_id = ?
        ORDER BY id DESC
        """,
        (empresa_id,)
    ).fetchall()
    tags = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (empresa_id,)
    ).fetchall()

    resumo_conversa = {
        "total_mensagens": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE conversa_id = ?
            """,
            (conversa_id,)
        ).fetchone()["total"],

        "mensagens_bot": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE conversa_id = ? AND remetente_tipo = 'bot'
            """,
            (conversa_id,)
        ).fetchone()["total"],

        "mensagens_com_regra": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE conversa_id = ? AND regra_id IS NOT NULL
            """,
            (conversa_id,)
        ).fetchone()["total"],

        "ultima_regra_nome": None,
        "etapa_atual": conversa["etapa"] if conversa else None,
        "fluxo_nome": conversa["fluxo_nome"] if conversa else None,
        "atendimento_status_label": None,
    }

    ultima_regra = conn.execute(
        """
        SELECT r.nome
        FROM mensagens m
        JOIN regras r ON r.id = m.regra_id AND r.empresa_id = ?
        WHERE m.conversa_id = ? AND m.regra_id IS NOT NULL
        ORDER BY m.id DESC
        LIMIT 1
        """,
        (empresa_id, conversa_id)
    ).fetchone()

    if ultima_regra:
        resumo_conversa["ultima_regra_nome"] = ultima_regra["nome"]

    atendimento_status = obter_status_atendimento(conversa)
    atendimento_status_label = {
        "bot": "No bot",
        "em_atendimento": "Em atendimento humano",
        "aguardando_cliente": "Aguardando cliente",
    }.get(atendimento_status, "No bot")
    resumo_conversa["atendimento_status_label"] = atendimento_status_label

    conn.close()

    contexto_conversa = buscar_contexto_conversa(conversa_id)
    conversa_dict = dict(conversa)
    conversa_dict["atendimento_status"] = atendimento_status
    conversa_dict["atendimento_status_label"] = atendimento_status_label
    conversa_dict["atendimento_historico"] = contexto_conversa.get("atendimento_historico", [])
    conversa_dict["atendentes"] = listar_atendentes_conversa(conversa_id)
    conversa_dict["memoria_cliente"] = buscar_memoria_cliente(conversa_id)

    conversas_lista = []
    resumo_fila = {"total": 0, "em_atendimento": 0, "aguardando_cliente": 0, "no_bot": 0}
    contato_ids_tag = None
    tag_id_valida = int(tag_id) if tag_id.isdigit() and tag_pertence_empresa(int(tag_id), empresa_id) else None
    if tag_id_valida:
        conn = get_connection()
        contato_ids_tag = {
            row["contato_id"]
            for row in conn.execute(
                "SELECT contato_id FROM contato_tags WHERE tag_id = ?",
                (tag_id_valida,)
            ).fetchall()
        }
        conn.close()
    for item in conversas_db:
        item_dict = dict(item)
        item_status = obter_status_atendimento(item)
        item_dict["atendimento_status"] = item_status
        item_dict["atendimento_status_label"] = {
            "bot": "No bot",
            "em_atendimento": "Em atendimento humano",
            "aguardando_cliente": "Aguardando cliente",
        }.get(item_status, "No bot")
        item_dict["proxima_acao_label"] = {
            "bot": "Automação ativa para próxima mensagem",
            "em_atendimento": "Aguardando ação do atendente",
            "aguardando_cliente": "Aguardando retorno do cliente",
        }.get(item_status, "Automação ativa")
        item_dict["ultima_mensagem"] = buscar_ultima_mensagem(item["id"])
        if item_status == "em_atendimento":
            resumo_fila["em_atendimento"] += 1
        elif item_status == "aguardando_cliente":
            resumo_fila["aguardando_cliente"] += 1
        else:
            resumo_fila["no_bot"] += 1
        if busca:
            nome = (item_dict.get("contato_nome") or "").lower()
            tel = (item_dict.get("contato_telefone") or "").replace(" ", "")
            if busca.lower() not in nome and busca.replace(" ", "") not in tel:
                continue
        if status in ["aberta", "fechada"] and item_dict["status"] != status:
            continue
        if bot == "ativo" and int(item_dict["bot_ativo"] or 0) != 1:
            continue
        if bot == "pausado" and int(item_dict["bot_ativo"] or 0) != 0:
            continue
        if contato_ids_tag is not None and item_dict.get("contato_id") not in contato_ids_tag:
            continue
        if atendimento and item_status != atendimento:
            continue
        if somente_humano and not item_dict.get("atendente_nome"):
            continue
        conversas_lista.append(item_dict)
    resumo_fila["total"] = len(conversas_lista)

    return render_template(
        "conversa_detalhe.html",
        conversa=conversa_dict,
        mensagens=mensagens,
        conversas=conversas_lista,
        contatos=contatos,
        resumo_conversa=resumo_conversa,
        tags=tags,
        resumo_fila=resumo_fila,
        filtros_conversa={
            "busca": busca,
            "status": status,
            "bot": bot,
            "atendimento": atendimento,
            "tag_id": tag_id_valida,
            "somente_humano": somente_humano,
        },
    )


@app.route("/conversas/<int:conversa_id>/mensagem", methods=["POST"])
@login_required
def enviar_mensagem(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))

    conteudo = request.form.get("conteudo", "").strip()

    if conteudo:
        vincular_atendente_conversa(conversa_id, nome_atendente=session.get("user_nome"))
        criar_mensagem(
            conversa_id,
            "humano",
            conteudo,
            "enviada",
            user_id=obter_user_id_logado(),
            canal="interno"
        )
        registrar_evento("mensagem_humana_enviada", referencia_id=conversa_id, valor=session.get("user_nome"))

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/mensagens/recentes")
@login_required
def mensagens_recentes_conversa(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return jsonify({"ok": False, "erro": "Conversa invalida"}), 403

    ultimo_id = (request.args.get("ultimo_id") or "0").strip()
    ultimo_id = int(ultimo_id) if ultimo_id.isdigit() else 0
    conn = get_connection()
    mensagens = conn.execute(
        """
        SELECT
            m.id,
            m.direcao,
            m.remetente_tipo,
            m.conteudo,
            m.criado_em,
            m.regra_id,
            m.user_id,
            m.canal,
            u.nome AS user_nome,
            r.nome AS regra_nome
        FROM mensagens m
        LEFT JOIN users u ON u.id = m.user_id
        LEFT JOIN regras r ON r.id = m.regra_id AND r.empresa_id = ?
        WHERE m.conversa_id = ?
          AND m.id > ?
        ORDER BY m.id ASC
        LIMIT 100
        """,
        (obter_empresa_id_logada(), conversa_id, ultimo_id)
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "conversa_id": conversa_id,
            "mensagens": [dict(mensagem) for mensagem in mensagens],
            "atendentes": [dict(atendente) for atendente in listar_atendentes_conversa(conversa_id)],
        }
    )


@app.route("/conversas/<int:conversa_id>/iniciar-fluxo/<int:fluxo_id>")
@login_required
def iniciar_fluxo_manual_conversa(conversa_id, fluxo_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))

    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("ver_conversa", conversa_id=conversa_id))

    primeiro_bloco = iniciar_fluxo_conversa(conversa_id, fluxo_id)
    if primeiro_bloco:
        resposta_fluxo = executar_bloco_fluxo(conversa_id, primeiro_bloco)
        if resposta_fluxo:
            criar_mensagem(conversa_id, "bot", resposta_fluxo, "enviada")

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/simular-cliente", methods=["POST"])
@login_required
def simular_mensagem_cliente(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))

    conteudo = request.form.get("conteudo_cliente", "").strip()

    if conteudo:
        criar_mensagem(conversa_id, "cliente", conteudo, "recebida")

        conn = get_connection()
        conversa = conn.execute(
            """
            SELECT bot_ativo
            FROM conversas
            WHERE id = ? AND empresa_id = ?
            """,
            (conversa_id, obter_empresa_id_logada())
        ).fetchone()
        conn.close()

        if conversa and conversa["bot_ativo"] == 1:
            resposta_bot, regra_id = gerar_resposta_bot(conteudo, conversa_id)

            ultima = buscar_ultima_mensagem_completa(conversa_id)
            if resposta_bot and not (
                ultima
                and ultima["remetente_tipo"] == "bot"
                and (ultima["conteudo"] or "").strip() == resposta_bot.strip()
            ):
                criar_mensagem(
                    conversa_id,
                    "bot",
                    resposta_bot,
                    "enviada",
                    regra_id
                )

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/status/<novo_status>", methods=["POST"])
@login_required
def alterar_status_conversa(conversa_id, novo_status):
    if novo_status not in ["aberta", "fechada"]:
        return redirect(url_for("ver_conversa", conversa_id=conversa_id))

    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET status = ?, atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (novo_status, conversa_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    registrar_evento("conversa_status_alterado", referencia_id=conversa_id, valor=novo_status)

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/bot/<int:ativo>", methods=["POST"])
@login_required
def alterar_bot_conversa(conversa_id, ativo):
    if ativo not in [0, 1]:
        return redirect(url_for("ver_conversa", conversa_id=conversa_id))

    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET bot_ativo = ?, atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (ativo, conversa_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    if ativo == 1:
        salvar_status_atendimento(conversa_id, "bot", atendente_nome=session.get("user_nome"))
        registrar_evento("bot_ativado", referencia_id=conversa_id)
    else:
        salvar_status_atendimento(conversa_id, "em_atendimento", atendente_nome=session.get("user_nome"))
        registrar_evento("bot_pausado", referencia_id=conversa_id)

    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/assumir", methods=["POST"])
@login_required
def assumir_conversa(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))
    nome_atendente = session.get("user_nome") or "Atendente"
    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET bot_ativo = 0,
            atendente_nome = ?,
            atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (nome_atendente, conversa_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    vincular_atendente_conversa(conversa_id, nome_atendente=nome_atendente)
    salvar_status_atendimento(conversa_id, "em_atendimento", atendente_nome=nome_atendente)
    registrar_evento("atendimento_assumido", referencia_id=conversa_id, valor=nome_atendente)
    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/aguardando-cliente", methods=["POST"])
@login_required
def marcar_conversa_aguardando_cliente(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))
    nome_atendente = session.get("user_nome") or "Atendente"
    salvar_status_atendimento(conversa_id, "aguardando_cliente", atendente_nome=nome_atendente)
    registrar_evento("atendimento_aguardando_cliente", referencia_id=conversa_id, valor=nome_atendente)
    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/retomar-atendimento", methods=["POST"])
@login_required
def retomar_atendimento_conversa(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))
    nome_atendente = session.get("user_nome") or "Atendente"
    salvar_status_atendimento(conversa_id, "em_atendimento", atendente_nome=nome_atendente)
    registrar_evento("atendimento_retornado", referencia_id=conversa_id, valor=nome_atendente)
    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


@app.route("/conversas/<int:conversa_id>/devolver-bot", methods=["POST"])
@login_required
def devolver_conversa_ao_bot(conversa_id):
    if not conversa_pertence_empresa(conversa_id):
        return redirect(url_for("conversas"))
    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET bot_ativo = 1,
            atendente_nome = NULL,
            atualizada_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (conversa_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    salvar_status_atendimento(conversa_id, "bot", atendente_nome=session.get("user_nome"))
    registrar_evento("atendimento_devolvido_bot", referencia_id=conversa_id)
    return redirect(url_for("ver_conversa", conversa_id=conversa_id))


# =========================================================
# CONTATOS
# =========================================================
@app.route("/contatos")
@login_required
def contatos():
    busca = (request.args.get("busca") or "").strip()
    tag_id = (request.args.get("tag_id") or "").strip()
    empresa_id = obter_empresa_id_logada()
    if tag_id.isdigit() and not tag_pertence_empresa(int(tag_id), empresa_id):
        tag_id = ""

    conn = get_connection()
    query = """
        SELECT
            c.*,
            (
                SELECT GROUP_CONCAT(t.nome, ', ')
                FROM contato_tags ct
                JOIN tags t ON t.id = ct.tag_id
                WHERE ct.contato_id = c.id AND t.empresa_id = c.empresa_id
            ) AS tags_nomes
        FROM contatos c
        WHERE c.empresa_id = ?
    """
    params = [empresa_id]
    if busca:
        query += " AND (lower(coalesce(c.nome, '')) LIKE ? OR replace(coalesce(c.telefone, ''), ' ', '') LIKE ?)"
        params.extend([f"%{busca.lower()}%", f"%{busca.replace(' ', '')}%"])
    tag_id_valida = int(tag_id) if tag_id.isdigit() and tag_pertence_empresa(int(tag_id)) else None
    if tag_id_valida:
        query += " AND c.id IN (SELECT contato_id FROM contato_tags WHERE tag_id = ?)"
        params.append(tag_id_valida)
    query += " ORDER BY c.id DESC"
    contatos_lista = conn.execute(query, tuple(params)).fetchall()
    tags = conn.execute(
        "SELECT id, nome, cor FROM tags WHERE empresa_id = ? ORDER BY nome ASC",
        (empresa_id,)
    ).fetchall()
    conn.close()
    return render_template(
        "contatos.html",
        contatos=contatos_lista,
        tags=tags,
        busca=busca,
        tag_id_selecionada=tag_id_valida,
    )


@app.route("/contatos/exportar")
@login_required
def exportar_contatos():
    conn = get_connection()
    contatos_lista = conn.execute(
        """
        SELECT id, nome, telefone, criado_em
        FROM contatos
        WHERE empresa_id = ?
        ORDER BY id DESC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nome', 'Telefone', 'Criado em'])

    for contato in contatos_lista:
        writer.writerow([
            contato['id'],
            contato['nome'] or '',
            contato['telefone'] or '',
            contato['criado_em'] or ''
        ])

    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=contatos.csv'
    }


@app.route("/contatos/novo", methods=["GET", "POST"])
@login_required
def novo_contato():
    conn = get_connection()
    tags = conn.execute(
        "SELECT id, nome, cor FROM tags WHERE empresa_id = ? ORDER BY nome ASC",
        (obter_empresa_id_logada(),)
    ).fetchall()
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        telefone = (request.form.get("telefone") or "").strip()
        tag_ids = filtrar_tags_da_empresa(request.form.getlist("tag_ids"))

        if telefone:
            cursor = conn.execute(
                """
                INSERT INTO contatos (empresa_id, nome, telefone)
                VALUES (?, ?, ?)
                """,
                (obter_empresa_id_logada(), nome, telefone)
            )
            contato_id = cursor.lastrowid
            for tag_id in tag_ids:
                conn.execute(
                    "INSERT INTO contato_tags (contato_id, tag_id) VALUES (?, ?)",
                    (contato_id, tag_id)
                )
            conn.commit()

        conn.close()
        return redirect(url_for("contatos"))

    conn.close()
    return render_template("novo_contato.html", tags=tags)


@app.route("/contatos/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_contato(id):
    conn = get_connection()
    tags = conn.execute(
        "SELECT id, nome, cor FROM tags WHERE empresa_id = ? ORDER BY nome ASC",
        (obter_empresa_id_logada(),)
    ).fetchall()

    if not contato_pertence_empresa(id):
        conn.close()
        return redirect(url_for("contatos"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        telefone = (request.form.get("telefone") or "").strip()
        tag_ids = filtrar_tags_da_empresa(request.form.getlist("tag_ids"))

        conn.execute(
            """
            UPDATE contatos
            SET nome = ?, telefone = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ?
            """,
            (nome, telefone, id, obter_empresa_id_logada())
        )
        conn.execute("DELETE FROM contato_tags WHERE contato_id = ?", (id,))
        for tag_id in tag_ids:
            conn.execute(
                "INSERT INTO contato_tags (contato_id, tag_id) VALUES (?, ?)",
                (id, tag_id)
            )
        conn.commit()
        conn.close()

        return redirect(url_for("contatos"))

    contato = conn.execute(
        """
        SELECT *
        FROM contatos
        WHERE id = ? AND empresa_id = ?
        """,
        (id, obter_empresa_id_logada())
    ).fetchone()
    conn.close()

    if not contato:
        return redirect(url_for("contatos"))

    conn = get_connection()
    tag_ids_contato = [
        row["tag_id"]
        for row in conn.execute(
            """
            SELECT ct.tag_id
            FROM contato_tags ct
            JOIN tags t ON t.id = ct.tag_id
            WHERE ct.contato_id = ? AND t.empresa_id = ?
            """,
            (id, obter_empresa_id_logada())
        ).fetchall()
    ]
    conn.close()
    return render_template(
        "editar_contatos.html",
        contato=contato,
        tags=tags,
        tag_ids_contato=tag_ids_contato,
    )


@app.route("/contatos/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_contato(id):
    if not contato_pertence_empresa(id):
        return redirect(url_for("contatos"))

    conn = get_connection()
    conn.execute("DELETE FROM contato_tags WHERE contato_id = ?", (id,))
    conn.execute(
        "DELETE FROM contatos WHERE id = ? AND empresa_id = ?",
        (id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()

    return redirect(url_for("contatos"))


@app.route("/tags/nova", methods=["POST"])
@login_required
def nova_tag():
    nome = (request.form.get("nome") or "").strip()
    cor = (request.form.get("cor") or "").strip() or "#7b5ae0"
    if nome:
        conn = get_connection()
        conn.execute(
            "INSERT INTO tags (empresa_id, nome, cor) VALUES (?, ?, ?)",
            (obter_empresa_id_logada(), nome, cor)
        )
        conn.commit()
        conn.close()
        registrar_evento("tag_criada", valor=nome)
    return redirect(url_for("contatos"))


@app.route("/tags/<int:tag_id>/excluir", methods=["POST"])
@login_required
def excluir_tag(tag_id):
    if not tag_pertence_empresa(tag_id):
        return redirect(url_for("contatos"))

    conn = get_connection()
    tag = conn.execute(
        "SELECT nome FROM tags WHERE id = ? AND empresa_id = ?",
        (tag_id, obter_empresa_id_logada())
    ).fetchone()
    conn.execute("DELETE FROM contato_tags WHERE tag_id = ?", (tag_id,))
    conn.execute(
        "DELETE FROM tags WHERE id = ? AND empresa_id = ?",
        (tag_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    if tag:
        registrar_evento("tag_excluida", referencia_id=tag_id, valor=tag["nome"])
    return redirect(url_for("contatos"))


# =========================================================
# REGRAS
# =========================================================
@app.route("/regras")
@login_required
def regras():
    conn = get_connection()
    regras_db = conn.execute(
        """
        SELECT r.*, f.nome AS fluxo_nome
        FROM regras r
        LEFT JOIN fluxos f ON f.id = r.fluxo_id AND f.empresa_id = r.empresa_id
        WHERE r.empresa_id = ?
        ORDER BY r.id DESC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    fluxos_db = conn.execute(
        """
        SELECT id, nome
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()
    tags_db = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    conn.close()

    regras_lista = [montar_regra_para_template(regra) for regra in regras_db]

    return render_template("regras.html", regras=regras_lista, fluxos=fluxos_db, tags=tags_db)


@app.route("/regras/nova", methods=["POST"])
@login_required
def nova_regra():
    nome = (request.form.get("nome") or "").strip()
    palavras = (request.form.get("palavras_chave") or "").strip()
    resposta = (request.form.get("resposta") or "").strip()
    fluxo_id = (request.form.get("fluxo_id") or "").strip()
    prioridade = (request.form.get("prioridade") or "0").strip()
    etapa_destino = (request.form.get("etapa_destino") or "").strip()
    tag_id = (request.form.get("tag_id") or "").strip()
    operador_palavras = (request.form.get("operador_palavras") or "any").strip().lower()
    excluir_palavras_texto = (request.form.get("excluir_palavras") or "").strip()
    etapa_cond = (request.form.get("etapa_condicao") or "").strip()
    status_cond = (request.form.get("status_condicao") or "").strip()
    fluxo_id_valor = int(fluxo_id) if fluxo_id.isdigit() and fluxo_pertence_empresa(int(fluxo_id)) else None
    tag_id_valor = int(tag_id) if tag_id.isdigit() and tag_pertence_empresa(int(tag_id)) else None

    if nome and palavras and (resposta or fluxo_id_valor):
        palavras_lista = []
        for p in palavras.split(","):
            p = p.strip()
            if p:
                palavras_lista.append(p)

        condicao_json = json.dumps(
            {
                "palavras_chave": palavras_lista,
                "operador_palavras": "all" if operador_palavras == "all" else "any",
                "excluir_palavras": [p.strip() for p in excluir_palavras_texto.split(",") if p.strip()],
                "etapa": etapa_cond or None,
                "status_conversa": status_cond or None,
            },
            ensure_ascii=False
        )

        acao_json = json.dumps(
            {
                "resposta": resposta,
                "prioridade": int(prioridade) if prioridade.isdigit() else 0,
                "etapa_destino": etapa_destino or None,
                "tag_id": tag_id_valor,
            },
            ensure_ascii=False
        )

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO regras (
                empresa_id,
                nome,
                tipo_regra,
                condicao_json,
                acao_json,
                fluxo_id,
                ativa
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obter_empresa_id_logada(),
                nome,
                "palavra_chave",
                condicao_json,
                acao_json,
                fluxo_id_valor,
                1
            )
        )
        conn.commit()
        conn.close()
        registrar_evento("regra_criada", valor=nome)

    return redirect(url_for("regras"))


@app.route("/regras/editar/<int:regra_id>", methods=["GET", "POST"])
@login_required
def editar_regra(regra_id):
    conn = get_connection()

    regra_row = conn.execute(
        """
        SELECT *
        FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    ).fetchone()

    fluxos_db = conn.execute(
        """
        SELECT id, nome
        FROM fluxos
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()
    tags_db = conn.execute(
        """
        SELECT id, nome, cor
        FROM tags
        WHERE empresa_id = ?
        ORDER BY nome ASC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    if not regra_row:
        conn.close()
        return redirect(url_for("regras"))

    regra = montar_regra_para_template(regra_row)

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        palavras = (request.form.get("palavras_chave") or "").strip()
        resposta = (request.form.get("resposta") or "").strip()
        fluxo_id = (request.form.get("fluxo_id") or "").strip()
        prioridade = (request.form.get("prioridade") or "0").strip()
        etapa_destino = (request.form.get("etapa_destino") or "").strip()
        tag_id = (request.form.get("tag_id") or "").strip()
        operador_palavras = (request.form.get("operador_palavras") or "any").strip().lower()
        excluir_palavras_texto = (request.form.get("excluir_palavras") or "").strip()
        etapa_cond = (request.form.get("etapa_condicao") or "").strip()
        status_cond = (request.form.get("status_condicao") or "").strip()
        ativa = 1 if request.form.get("ativo") == "on" else 0
        fluxo_id_valor = int(fluxo_id) if fluxo_id.isdigit() and fluxo_pertence_empresa(int(fluxo_id)) else None
        tag_id_valor = int(tag_id) if tag_id.isdigit() and tag_pertence_empresa(int(tag_id)) else None

        if nome and palavras and (resposta or fluxo_id_valor):
            palavras_lista = []
            for p in palavras.split(","):
                p = p.strip()
                if p:
                    palavras_lista.append(p)

            condicao_json = json.dumps(
                {
                    "palavras_chave": palavras_lista,
                    "operador_palavras": "all" if operador_palavras == "all" else "any",
                    "excluir_palavras": [p.strip() for p in excluir_palavras_texto.split(",") if p.strip()],
                    "etapa": etapa_cond or None,
                    "status_conversa": status_cond or None,
                },
                ensure_ascii=False
            )

            acao_json = json.dumps(
                {
                    "resposta": resposta,
                    "prioridade": int(prioridade) if prioridade.isdigit() else 0,
                    "etapa_destino": etapa_destino or None,
                    "tag_id": tag_id_valor,
                },
                ensure_ascii=False
            )

            conn.execute(
                """
                UPDATE regras
                SET nome = ?,
                    condicao_json = ?,
                    acao_json = ?,
                    fluxo_id = ?,
                    ativa = ?
                WHERE id = ? AND empresa_id = ?
                """,
                (
                    nome,
                    condicao_json,
                    acao_json,
                    fluxo_id_valor,
                    ativa,
                    regra_id,
                    obter_empresa_id_logada()
                )
            )
            conn.commit()
            registrar_evento("regra_editada", referencia_id=regra_id, valor=nome)

        conn.close()
        return redirect(url_for("regras"))

    conn.close()

    return render_template(
        "editar_regra.html",
        regra=regra,
        palavras_chave=regra["palavras_chave"],
        resposta=regra["resposta"],
        fluxos=fluxos_db,
        tags=tags_db
    )


@app.route("/regras/<int:regra_id>/toggle", methods=["POST"])
@login_required
def toggle_regra(regra_id):
    conn = get_connection()

    regra = conn.execute(
        """
        SELECT ativa
        FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    ).fetchone()

    if regra:
        novo_status = 0 if regra["ativa"] == 1 else 1
        conn.execute(
            """
            UPDATE regras
            SET ativa = ?
            WHERE id = ? AND empresa_id = ?
            """,
            (novo_status, regra_id, obter_empresa_id_logada())
        )
        conn.commit()
        registrar_evento("regra_toggle", referencia_id=regra_id, valor=str(novo_status))

    conn.close()
    return redirect(url_for("regras"))


@app.route("/regras/excluir/<int:regra_id>", methods=["POST"])
@login_required
def excluir_regra(regra_id):
    conn = get_connection()
    regra = conn.execute(
        "SELECT nome FROM regras WHERE id = ? AND empresa_id = ?",
        (regra_id, obter_empresa_id_logada())
    ).fetchone()
    conn.execute(
        """
        DELETE FROM regras
        WHERE id = ? AND empresa_id = ?
        """,
        (regra_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    if regra:
        registrar_evento("regra_excluida", referencia_id=regra_id, valor=regra["nome"])

    return redirect(url_for("regras"))


# =========================================================
# AGENDAMENTOS
# =========================================================
@app.route("/agendamentos")
@login_required
def agendamentos():
    conn = get_connection()

    agendamentos_lista = conn.execute(
        """
        SELECT
            a.*,
            c.nome AS contato_nome,
            c.telefone AS contato_telefone
        FROM agendamentos a
        LEFT JOIN contatos c ON c.id = a.contato_id AND c.empresa_id = a.empresa_id
        WHERE a.empresa_id = ?
        ORDER BY a.criado_em DESC, a.id DESC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    conn.close()

    return render_template("agendamentos.html", agendamentos=agendamentos_lista)


@app.route("/agendamentos/exportar")
@login_required
def exportar_agendamentos():
    conn = get_connection()

    agendamentos_lista = conn.execute(
        """
        SELECT
            a.id,
            a.servico,
            a.data,
            a.horario,
            a.status,
            a.criado_em,
            c.nome AS contato_nome,
            c.telefone AS contato_telefone
        FROM agendamentos a
        LEFT JOIN contatos c ON c.id = a.contato_id AND c.empresa_id = a.empresa_id
        WHERE a.empresa_id = ?
        ORDER BY a.criado_em DESC, a.id DESC
        """,
        (obter_empresa_id_logada(),)
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Serviço', 'Data', 'Horário', 'Status', 'Criado em', 'Contato Nome', 'Contato Telefone'])

    for agendamento in agendamentos_lista:
        writer.writerow([
            agendamento['id'],
            agendamento['servico'] or '',
            agendamento['data'] or '',
            agendamento['horario'] or '',
            agendamento['status'] or '',
            agendamento['criado_em'] or '',
            agendamento['contato_nome'] or '',
            agendamento['contato_telefone'] or ''
        ])

    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=agendamentos.csv'
    }


@app.route("/agendamentos/<int:agendamento_id>/cancelar", methods=["POST"])
@login_required
def cancelar_agendamento(agendamento_id):
    conn = get_connection()
    conn.execute(
        """
        UPDATE agendamentos
        SET status = 'cancelado'
        WHERE id = ? AND empresa_id = ?
        """,
        (agendamento_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()
    registrar_evento("agendamento_cancelado", referencia_id=agendamento_id)
    return redirect(url_for("agendamentos"))


@app.route("/agendamentos/<int:agendamento_id>/remarcar", methods=["POST"])
@login_required
def remarcar_agendamento(agendamento_id):
    data = (request.form.get("data") or "").strip()
    horario = (request.form.get("horario") or "").strip()
    servico = (request.form.get("servico") or "").strip()
    if not data or not horario:
        return redirect(url_for("agendamentos"))
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()
    agendamento = conn.execute(
        """
        SELECT id
        FROM agendamentos
        WHERE id = ? AND empresa_id = ?
        """,
        (agendamento_id, empresa_id)
    ).fetchone()
    if not agendamento:
        conn.close()
        return redirect(url_for("agendamentos"))
    data_normalizada, horario_normalizado, erro_validacao = validar_dados_agendamento(
        conn,
        empresa_id,
        data,
        horario,
        excluir_agendamento_id=agendamento_id
    )
    if erro_validacao:
        conn.close()
        flash(erro_validacao, "erro")
        return redirect(url_for("agendamentos"))
    conn.execute(
        """
        UPDATE agendamentos
        SET servico = ?,
            data = ?,
            horario = ?,
            status = 'confirmado'
        WHERE id = ? AND empresa_id = ?
        """,
        (servico, data_normalizada, horario_normalizado, agendamento_id, empresa_id)
    )
    conn.commit()
    conn.close()
    registrar_evento(
        "agendamento_remarcado",
        referencia_id=agendamento_id,
        valor=json.dumps({"data": data_normalizada, "horario": horario_normalizado}, ensure_ascii=False)
    )
    return redirect(url_for("agendamentos"))


# =========================================================
# FLUXOS - LISTAGEM / CRUD
# =========================================================
@app.route("/fluxos")
@login_required
def fluxos():
    fluxos_db = buscar_fluxos_empresa(obter_empresa_id_logada())

    fluxos_lista = []
    for fluxo in fluxos_db:
        fluxo_dict = dict(fluxo)

        conn = get_connection()
        total_blocos = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM fluxo_blocos
            WHERE fluxo_id = ?
            """,
            (fluxo["id"],)
        ).fetchone()["total"]
        conn.close()

        fluxo_dict["total_blocos"] = total_blocos
        fluxos_lista.append(fluxo_dict)

    return render_template("fluxos.html", fluxos=fluxos_lista)


@app.route("/fluxos/novo", methods=["POST"])
@login_required
def novo_fluxo():
    empresa_id = obter_empresa_id_logada()
    nome = (request.form.get("nome") or "Novo fluxo").strip()
    descricao = (request.form.get("descricao") or "").strip()
    tipo_gatilho = (request.form.get("tipo_gatilho") or "").strip()
    gatilho_valor = (request.form.get("gatilho_valor") or "").strip()

    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO fluxos (
            empresa_id,
            nome,
            descricao,
            ativo,
            tipo_gatilho,
            gatilho_valor
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (empresa_id, nome, descricao, 1, tipo_gatilho, gatilho_valor)
    )
    fluxo_id = cursor.lastrowid

    conn.execute(
        """
        INSERT INTO fluxo_blocos (
            fluxo_id,
            tipo_bloco,
            titulo,
            conteudo,
            ordem,
            proximo_bloco_id,
            config_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fluxo_id,
            "mensagem",
            "Mensagem inicial",
            "Olá 💖 Seja bem-vindo(a)! Como posso te ajudar hoje?",
            1,
            None,
            json.dumps({}, ensure_ascii=False)
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("fluxo_editor", fluxo_id=fluxo_id))


@app.route("/fluxos/<int:fluxo_id>/editar", methods=["POST"])
@login_required
def editar_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    nome = (request.form.get("nome") or "").strip()
    descricao = (request.form.get("descricao") or "").strip()
    tipo_gatilho = (request.form.get("tipo_gatilho") or "").strip()
    gatilho_valor = (request.form.get("gatilho_valor") or "").strip()
    ativo = 1 if request.form.get("ativo") == "1" else 0

    conn = get_connection()
    conn.execute(
        """
        UPDATE fluxos
        SET nome = ?,
            descricao = ?,
            tipo_gatilho = ?,
            gatilho_valor = ?,
            ativo = ?,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (
            nome,
            descricao,
            tipo_gatilho,
            gatilho_valor,
            ativo,
            fluxo_id,
            obter_empresa_id_logada()
        )
    )
    conn.commit()
    conn.close()
    snapshot_fluxo_versao(fluxo_id)
    registrar_evento("fluxo_editado", referencia_id=fluxo_id, valor=nome)

    return redirect(url_for("fluxo_editor", fluxo_id=fluxo_id))


@app.route("/fluxos/<int:fluxo_id>/toggle", methods=["POST"])
@login_required
def toggle_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    conn = get_connection()
    fluxo = conn.execute(
        """
        SELECT ativo
        FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, obter_empresa_id_logada())
    ).fetchone()

    if fluxo:
        novo_status = 0 if int(fluxo["ativo"] or 0) == 1 else 1
        conn.execute(
            """
            UPDATE fluxos
            SET ativo = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ?
            """,
            (novo_status, fluxo_id, obter_empresa_id_logada())
        )
        conn.commit()

    conn.close()
    return redirect(url_for("fluxos"))


@app.route("/fluxos/<int:fluxo_id>/duplicar", methods=["POST"])
@login_required
def duplicar_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    fluxo_original = buscar_fluxo(fluxo_id, obter_empresa_id_logada())
    blocos_originais = buscar_blocos_fluxo(fluxo_id)

    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO fluxos (
            empresa_id,
            nome,
            descricao,
            ativo,
            tipo_gatilho,
            gatilho_valor
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            fluxo_original["empresa_id"],
            f"{fluxo_original['nome']} (cópia)",
            fluxo_original["descricao"],
            0,
            fluxo_original["tipo_gatilho"],
            fluxo_original["gatilho_valor"]
        )
    )
    novo_fluxo_id = cursor.lastrowid

    mapa_ids = {}

    for bloco in blocos_originais:
        cursor = conn.execute(
            """
            INSERT INTO fluxo_blocos (
                fluxo_id,
                tipo_bloco,
                titulo,
                conteudo,
                ordem,
                proximo_bloco_id,
                config_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                novo_fluxo_id,
                bloco["tipo_bloco"],
                bloco["titulo"],
                bloco["conteudo"],
                bloco["ordem"],
                None,
                bloco["config_json"]
            )
        )
        mapa_ids[bloco["id"]] = cursor.lastrowid

    for bloco in blocos_originais:
        novo_bloco_id = mapa_ids[bloco["id"]]
        novo_proximo = mapa_ids.get(bloco["proximo_bloco_id"]) if bloco["proximo_bloco_id"] else None
        novo_config_json = remapear_config_bloco_fluxo(bloco["config_json"], mapa_ids)

        conn.execute(
            """
            UPDATE fluxo_blocos
            SET proximo_bloco_id = ?,
                config_json = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND fluxo_id = ?
            """,
            (novo_proximo, novo_config_json, novo_bloco_id, novo_fluxo_id)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("fluxo_editor", fluxo_id=novo_fluxo_id))


@app.route("/fluxos/<int:fluxo_id>/excluir", methods=["POST"])
@login_required
def excluir_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET fluxo_id_ativo = NULL,
            bloco_atual_id = NULL,
            etapa = NULL,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE empresa_id = ? AND fluxo_id_ativo = ?
        """,
        (obter_empresa_id_logada(), fluxo_id)
    )
    conn.execute(
        """
        UPDATE regras
        SET fluxo_id = NULL
        WHERE empresa_id = ? AND fluxo_id = ?
        """,
        (obter_empresa_id_logada(), fluxo_id)
    )
    conn.execute(
        """
        DELETE FROM fluxos
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, obter_empresa_id_logada())
    )
    conn.commit()
    conn.close()

    return redirect(url_for("fluxos"))


# =========================================================
# EDITOR DE FLUXO
# =========================================================
@app.route("/fluxos/editor")
@login_required
def fluxo_editor_redirect():
    fluxos_db = buscar_fluxos_empresa(obter_empresa_id_logada())
    if not fluxos_db:
        return redirect(url_for("fluxos"))
    return redirect(url_for("fluxo_editor", fluxo_id=fluxos_db[0]["id"]))


@app.route("/fluxos/editor/<int:fluxo_id>")
@login_required
def fluxo_editor(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    fluxo = buscar_fluxo(fluxo_id, obter_empresa_id_logada())
    blocos_rows = buscar_blocos_fluxo(fluxo_id)
    blocos = [serializar_bloco(b) for b in blocos_rows]

    return render_template(
        "fluxo_editor.html",
        fluxo=fluxo,
        blocos=blocos
    )


@app.route("/fluxos/<int:fluxo_id>/debug-execucoes")
@login_required
def fluxo_debug_execucoes(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))
    conn = get_connection()
    logs = conn.execute(
        """
        SELECT fe.*
        FROM fluxo_execucoes fe
        JOIN conversas c ON c.id = fe.conversa_id
        WHERE fe.fluxo_id = ? AND c.empresa_id = ?
        ORDER BY fe.id DESC
        LIMIT 200
        """,
        (fluxo_id, obter_empresa_id_logada())
    ).fetchall()
    versoes = conn.execute(
        """
        SELECT id, versao, criado_em
        FROM fluxo_versoes
        WHERE fluxo_id = ?
        ORDER BY versao DESC
        LIMIT 20
        """,
        (fluxo_id,)
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "fluxo_id": fluxo_id,
            "versoes": [dict(v) for v in versoes],
            "execucoes": [dict(l) for l in logs],
        }
    )


@app.route("/fluxos/<int:fluxo_id>/blocos/novo", methods=["POST"])
@login_required
def novo_bloco_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))

    tipo_bloco = (request.form.get("tipo_bloco") or "mensagem").strip()
    titulo = (request.form.get("titulo") or "Novo bloco").strip()
    conteudo = (request.form.get("conteudo") or "").strip()

    conn = get_connection()
    ultimo = conn.execute(
        """
        SELECT MAX(ordem) AS max_ordem
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        """,
        (fluxo_id,)
    ).fetchone()

    nova_ordem = (ultimo["max_ordem"] or 0) + 1

    conn.execute(
        """
        INSERT INTO fluxo_blocos (
            fluxo_id,
            tipo_bloco,
            titulo,
            conteudo,
            ordem,
            proximo_bloco_id,
            config_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fluxo_id,
            tipo_bloco,
            titulo,
            conteudo,
            nova_ordem,
            None,
            json.dumps({}, ensure_ascii=False)
        )
    )
    conn.commit()
    conn.close()

    return redirect(url_for("fluxo_editor", fluxo_id=fluxo_id))


@app.route("/fluxos/<int:fluxo_id>/blocos/salvar", methods=["POST"])
@login_required
def salvar_blocos_fluxo(fluxo_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return jsonify({"ok": False, "erro": "Fluxo inválido"}), 403

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"ok": False, "erro": "JSON inválido"}), 400

    blocos = payload.get("blocos", [])
    if not isinstance(blocos, list):
        return jsonify({"ok": False, "erro": "Lista de blocos inválida"}), 400

    conn = get_connection()

    ids_existentes = conn.execute(
        """
        SELECT id
        FROM fluxo_blocos
        WHERE fluxo_id = ?
        """,
        (fluxo_id,)
    ).fetchall()

    ids_existentes_set = {row["id"] for row in ids_existentes}
    ids_recebidos = set()

    for indice, bloco in enumerate(blocos, start=1):
        bloco_id_raw = bloco.get("id")
        try:
            bloco_id = int(bloco_id_raw) if bloco_id_raw else None
        except (TypeError, ValueError):
            bloco_id = None
        tipo_bloco = (bloco.get("tipo_bloco") or "mensagem").strip()
        titulo = (bloco.get("titulo") or "Bloco").strip()
        conteudo = (bloco.get("conteudo") or "").strip()
        proximo_bloco_id = normalizar_proximo_bloco_id(bloco.get("proximo_bloco_id"), fluxo_id)
        config = normalizar_config_bloco_fluxo(bloco.get("config", {}), fluxo_id)

        if bloco_id and bloco_id in ids_existentes_set:
            conn.execute(
                """
                UPDATE fluxo_blocos
                SET tipo_bloco = ?,
                    titulo = ?,
                    conteudo = ?,
                    ordem = ?,
                    proximo_bloco_id = ?,
                    config_json = ?,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ? AND fluxo_id = ?
                """,
                (
                    tipo_bloco,
                    titulo,
                    conteudo,
                    indice,
                    proximo_bloco_id,
                    json.dumps(config or {}, ensure_ascii=False),
                    bloco_id,
                    fluxo_id
                )
            )
            ids_recebidos.add(bloco_id)
        else:
            cursor = conn.execute(
                """
                INSERT INTO fluxo_blocos (
                    fluxo_id,
                    tipo_bloco,
                    titulo,
                    conteudo,
                    ordem,
                    proximo_bloco_id,
                    config_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fluxo_id,
                    tipo_bloco,
                    titulo,
                    conteudo,
                    indice,
                    proximo_bloco_id,
                    json.dumps(config or {}, ensure_ascii=False)
                )
            )
            ids_recebidos.add(cursor.lastrowid)

    ids_para_excluir = ids_existentes_set - ids_recebidos
    for bloco_id in ids_para_excluir:
        conn.execute(
            """
            DELETE FROM fluxo_blocos
            WHERE id = ? AND fluxo_id = ?
            """,
            (bloco_id, fluxo_id)
        )

    conn.execute(
        """
        UPDATE fluxos
        SET atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ? AND empresa_id = ?
        """,
        (fluxo_id, obter_empresa_id_logada())
    )

    conn.commit()
    conn.close()
    snapshot_fluxo_versao(fluxo_id)
    registrar_evento("fluxo_blocos_salvos", referencia_id=fluxo_id, valor=f"total:{len(blocos)}")

    return jsonify({"ok": True})


@app.route("/fluxos/<int:fluxo_id>/blocos/<int:bloco_id>/excluir", methods=["POST"])
@login_required
def excluir_bloco_fluxo(fluxo_id, bloco_id):
    if not fluxo_pertence_empresa(fluxo_id):
        return redirect(url_for("fluxos"))
    if not bloco_pertence_fluxo(bloco_id, fluxo_id):
        return redirect(url_for("fluxo_editor", fluxo_id=fluxo_id))

    conn = get_connection()
    conn.execute(
        """
        UPDATE conversas
        SET bloco_atual_id = NULL,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE empresa_id = ? AND bloco_atual_id = ?
        """,
        (obter_empresa_id_logada(), bloco_id)
    )
    conn.execute(
        """
        UPDATE fluxo_blocos
        SET proximo_bloco_id = NULL
        WHERE fluxo_id = ? AND proximo_bloco_id = ?
        """,
        (fluxo_id, bloco_id)
    )

    conn.execute(
        """
        DELETE FROM fluxo_blocos
        WHERE id = ? AND fluxo_id = ?
        """,
        (bloco_id, fluxo_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("fluxo_editor", fluxo_id=fluxo_id))


# =========================================================
# MÉTRICAS / OUTRAS TELAS
# =========================================================
@app.route("/metricas")
@login_required
def metricas():
    empresa_id = obter_empresa_id_logada()
    periodo_dias = (request.args.get("periodo_dias") or "30").strip()
    tipo_evento = (request.args.get("tipo_evento") or "").strip()
    if periodo_dias not in ["7", "15", "30", "90"]:
        periodo_dias = "30"
    data_inicio = (datetime.now() - timedelta(days=int(periodo_dias))).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()

    top_regras = conn.execute(
        """
        SELECT
            r.nome,
            COUNT(m.id) AS total
        FROM mensagens m
        JOIN regras r ON r.id = m.regra_id AND r.empresa_id = ?
        WHERE m.regra_id IS NOT NULL
          AND m.conversa_id IN (
              SELECT id FROM conversas WHERE empresa_id = ?
          )
        GROUP BY r.nome
        ORDER BY total DESC
        LIMIT 5
        """,
        (empresa_id, empresa_id)
    ).fetchall()

    total_agendamentos = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE empresa_id = ?
        """,
        (empresa_id,)
    ).fetchone()["total"]

    desempenho_atendentes = conn.execute(
        """
        SELECT
            COALESCE(u.nome, ca.nome_atendente, 'Atendente') AS nome,
            COUNT(m.id) AS mensagens,
            COUNT(DISTINCT ca.conversa_id) AS conversas
        FROM conversa_atendentes ca
        LEFT JOIN users u ON u.id = ca.user_id
        LEFT JOIN mensagens m ON m.conversa_id = ca.conversa_id
            AND m.user_id = ca.user_id
            AND m.remetente_tipo = 'humano'
        JOIN conversas c ON c.id = ca.conversa_id
        WHERE c.empresa_id = ?
          AND ca.ativo = 1
        GROUP BY COALESCE(u.nome, ca.nome_atendente, 'Atendente')
        ORDER BY mensagens DESC, conversas DESC
        LIMIT 8
        """,
        (empresa_id,)
    ).fetchall()

    tempo_medio_resposta = conn.execute(
        """
        SELECT AVG(
            (
                SELECT (julianday(m2.criado_em) - julianday(m1.criado_em)) * 24 * 60
                FROM mensagens m2
                WHERE m2.conversa_id = m1.conversa_id
                  AND m2.id > m1.id
                  AND m2.remetente_tipo IN ('bot', 'humano')
                ORDER BY m2.id ASC
                LIMIT 1
            )
        ) AS minutos
        FROM mensagens m1
        WHERE m1.remetente_tipo = 'cliente'
          AND m1.conversa_id IN (
              SELECT id FROM conversas WHERE empresa_id = ?
          )
        """,
        (empresa_id,)
    ).fetchone()["minutos"]

    metricas_data = {
        "total_contatos": conn.execute(
            "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ?",
            (empresa_id,)
        ).fetchone()["total"],

        "total_conversas": conn.execute(
            "SELECT COUNT(*) AS total FROM conversas WHERE empresa_id = ?",
            (empresa_id,)
        ).fetchone()["total"],

        "conversas_abertas": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversas
            WHERE empresa_id = ? AND status = 'aberta'
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "conversas_fechadas": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversas
            WHERE empresa_id = ? AND status = 'fechada'
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "total_mensagens": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE conversa_id IN (
                SELECT id FROM conversas WHERE empresa_id = ?
            )
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "mensagens_bot": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE remetente_tipo = 'bot'
              AND conversa_id IN (
                  SELECT id FROM conversas WHERE empresa_id = ?
              )
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "mensagens_cliente": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE remetente_tipo = 'cliente'
              AND conversa_id IN (
                  SELECT id FROM conversas WHERE empresa_id = ?
              )
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "mensagens_humano": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE remetente_tipo = 'humano'
              AND conversa_id IN (
                  SELECT id FROM conversas WHERE empresa_id = ?
              )
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "mensagens_com_regra": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM mensagens
            WHERE regra_id IS NOT NULL
              AND conversa_id IN (
                  SELECT id FROM conversas WHERE empresa_id = ?
              )
            """,
            (empresa_id,)
        ).fetchone()["total"],

        "total_agendamentos": total_agendamentos,
        "regras_acionadas": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM metricas_eventos
            WHERE empresa_id = ? AND tipo_evento IN ('regra_acionada', 'regra_fluxo_acionada')
            """,
            (empresa_id,)
        ).fetchone()["total"],
        "fluxos_iniciados": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM metricas_eventos
            WHERE empresa_id = ? AND tipo_evento = 'fluxo_iniciado'
            """,
            (empresa_id,)
        ).fetchone()["total"],
        "fluxos_finalizados": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM metricas_eventos
            WHERE empresa_id = ? AND tipo_evento = 'fluxo_finalizado'
            """,
            (empresa_id,)
        ).fetchone()["total"],
        "integracoes_ativas": conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM canal_integracoes
            WHERE empresa_id = ? AND status = 'ativo'
            """,
            (empresa_id,)
        ).fetchone()["total"],
        "tempo_medio_resposta_min": round(float(tempo_medio_resposta or 0), 1),
        "desempenho_atendentes": desempenho_atendentes,
        "top_regras": top_regras,
        "filtros": {"periodo_dias": periodo_dias, "tipo_evento": tipo_evento},
    }

    params_eventos = [empresa_id, data_inicio]
    filtro_tipo_sql = ""
    if tipo_evento:
        filtro_tipo_sql = " AND tipo_evento = ?"
        params_eventos.append(tipo_evento)

    metricas_data["eventos_recentes"] = conn.execute(
        f"""
        SELECT id, tipo_evento, referencia_id, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
          {filtro_tipo_sql}
        ORDER BY id DESC
        LIMIT 30
        """,
        tuple(params_eventos)
    ).fetchall()
    metricas_data["top_tipos_evento"] = conn.execute(
        f"""
        SELECT tipo_evento, COUNT(*) AS total
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
          {filtro_tipo_sql}
        GROUP BY tipo_evento
        ORDER BY total DESC
        LIMIT 8
        """,
        tuple(params_eventos)
    ).fetchall()
    metricas_data["tipos_evento_disponiveis"] = [
        row["tipo_evento"]
        for row in conn.execute(
            """
            SELECT DISTINCT tipo_evento
            FROM metricas_eventos
            WHERE empresa_id = ?
            ORDER BY tipo_evento ASC
            """,
            (empresa_id,)
        ).fetchall()
    ]
    eventos_norm = []
    for evento in metricas_data["eventos_recentes"]:
        item = dict(evento)
        resumo = ""
        if item.get("valor"):
            try:
                payload = json.loads(item["valor"])
                if isinstance(payload, dict):
                    resumo = ", ".join([f"{k}: {v}" for k, v in payload.items() if v is not None])[:140]
                else:
                    resumo = str(payload)[:140]
            except Exception:
                resumo = str(item["valor"])[:140]
        item["resumo"] = resumo
        eventos_norm.append(item)
    metricas_data["eventos_recentes"] = eventos_norm

    conn.close()

    return render_template("metricas.html", metricas=metricas_data)


@app.route("/metricas/eventos/exportar")
@login_required
def exportar_metricas_eventos():
    empresa_id = obter_empresa_id_logada()
    periodo_dias = (request.args.get("periodo_dias") or "30").strip()
    tipo_evento = (request.args.get("tipo_evento") or "").strip()
    if periodo_dias not in ["7", "15", "30", "90"]:
        periodo_dias = "30"
    data_inicio = (datetime.now() - timedelta(days=int(periodo_dias))).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    query = """
        SELECT id, tipo_evento, referencia_id, valor, criado_em
        FROM metricas_eventos
        WHERE empresa_id = ?
          AND criado_em >= ?
    """
    params = [empresa_id, data_inicio]
    if tipo_evento:
        query += " AND tipo_evento = ?"
        params.append(tipo_evento)
    query += " ORDER BY id DESC"
    eventos = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Tipo evento", "Referência", "Valor", "Criado em"])
    for evento in eventos:
        writer.writerow([
            evento["id"],
            evento["tipo_evento"] or "",
            evento["referencia_id"] or "",
            evento["valor"] or "",
            evento["criado_em"] or "",
        ])
    output.seek(0)
    return output.getvalue(), 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=metricas_eventos.csv",
    }


@app.route("/configuracoes")
@login_required
def configuracoes():
    conn = get_connection()
    empresas_usuario = buscar_empresas_do_usuario(obter_user_id_logado())
    empresa_id = obter_empresa_id_logada()
    membros_empresa = conn.execute(
        """
        SELECT
            u.nome,
            u.email,
            em.papel,
            em.ativo
        FROM empresa_membros em
        JOIN users u ON u.id = em.user_id
        WHERE em.empresa_id = ?
        ORDER BY CASE WHEN em.papel = 'owner' THEN 0 ELSE 1 END, u.nome ASC
        """,
        (empresa_id,)
    ).fetchall()
    disponibilidade = conn.execute(
        """
        SELECT id, dia_semana, hora_inicio, hora_fim, ativo
        FROM agenda_disponibilidade
        WHERE empresa_id = ?
        ORDER BY dia_semana ASC, hora_inicio ASC
        """,
        (empresa_id,)
    ).fetchall()
    integracoes = conn.execute(
        """
        SELECT id, canal, nome, status, webhook_token, phone_number_id,
               business_account_id, instagram_account_id, atualizado_em
        FROM canal_integracoes
        WHERE empresa_id = ?
        ORDER BY canal ASC, id DESC
        """,
        (empresa_id,)
    ).fetchall()
    plano_empresa = conn.execute(
        """
        SELECT el.*, ps.nome AS plano_nome, ps.descricao AS plano_descricao
        FROM empresa_limites el
        LEFT JOIN planos_saas ps ON ps.id = el.plano_id
        WHERE el.empresa_id = ?
        LIMIT 1
        """,
        (empresa_id,)
    ).fetchone()
    conn.close()
    return render_template(
        "configuracoes.html",
        empresas_usuario=empresas_usuario,
        membros_empresa=membros_empresa,
        disponibilidade=disponibilidade,
        integracoes=integracoes,
        plano_empresa=plano_empresa,
        empresa_id_logada=empresa_id,
    )


@app.route("/configuracoes/trocar-empresa", methods=["POST"])
@login_required
def trocar_empresa():
    empresa_id_nova = (request.form.get("empresa_id") or "").strip()
    if not empresa_id_nova.isdigit():
        return redirect(url_for("configuracoes"))
    conn = get_connection()
    membro = conn.execute(
        """
        SELECT e.id, e.nome_exibicao, e.nome_empresa
        FROM empresa_membros em
        JOIN empresas e ON e.id = em.empresa_id
        WHERE em.user_id = ? AND em.empresa_id = ? AND em.ativo = 1
        LIMIT 1
        """,
        (obter_user_id_logado(), int(empresa_id_nova))
    ).fetchone()
    conn.close()
    if not membro:
        flash("Você não pertence a essa empresa.", "erro")
        return redirect(url_for("configuracoes"))
    session["empresa_id"] = membro["id"]
    session["empresa_nome"] = membro["nome_exibicao"] or membro["nome_empresa"]
    registrar_evento("troca_contexto_empresa", referencia_id=membro["id"])
    return redirect(url_for("dashboard"))


@app.route("/configuracoes/membros/adicionar", methods=["POST"])
@login_required
def adicionar_membro_empresa():
    email = (request.form.get("email") or "").strip().lower()
    papel = (request.form.get("papel") or "membro").strip().lower()
    papel = papel if papel in ["owner", "admin", "membro"] else "membro"
    if not email:
        return redirect(url_for("configuracoes"))
    conn = get_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE lower(email) = ? LIMIT 1",
        (email,)
    ).fetchone()
    if not user:
        conn.close()
        flash("Usuário não encontrado para esse e-mail.", "erro")
        return redirect(url_for("configuracoes"))
    existe = conn.execute(
        """
        SELECT id
        FROM empresa_membros
        WHERE empresa_id = ? AND user_id = ?
        LIMIT 1
        """,
        (obter_empresa_id_logada(), user["id"])
    ).fetchone()
    if existe:
        conn.execute(
            """
            UPDATE empresa_membros
            SET ativo = 1, papel = ?
            WHERE id = ? AND empresa_id = ?
            """,
            (papel, existe["id"], obter_empresa_id_logada())
        )
    else:
        conn.execute(
            """
            INSERT INTO empresa_membros (empresa_id, user_id, papel, ativo)
            VALUES (?, ?, ?, 1)
            """,
            (obter_empresa_id_logada(), user["id"], papel)
        )
    conn.commit()
    conn.close()
    registrar_evento("membro_adicionado", valor=email)
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/disponibilidade/adicionar", methods=["POST"])
@login_required
def adicionar_disponibilidade():
    dia_semana = (request.form.get("dia_semana") or "").strip()
    hora_inicio = (request.form.get("hora_inicio") or "").strip()
    hora_fim = (request.form.get("hora_fim") or "").strip()
    if not dia_semana.isdigit() or not hora_inicio or not hora_fim:
        return redirect(url_for("configuracoes"))
    dia_semana_int = int(dia_semana)
    if dia_semana_int < 0 or dia_semana_int > 6:
        flash("Dia da semana inválido.", "erro")
        return redirect(url_for("configuracoes"))
    hora_inicio_norm, erro_inicio = normalizar_horario_agendamento(hora_inicio)
    hora_fim_norm, erro_fim = normalizar_horario_agendamento(hora_fim)
    if erro_inicio or erro_fim or hora_inicio_norm >= hora_fim_norm:
        flash("Informe uma faixa de horário válida.", "erro")
        return redirect(url_for("configuracoes"))

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO agenda_disponibilidade (empresa_id, dia_semana, hora_inicio, hora_fim, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        (obter_empresa_id_logada(), dia_semana_int, hora_inicio_norm, hora_fim_norm)
    )
    conn.commit()
    conn.close()
    registrar_evento("disponibilidade_adicionada", valor=f"{dia_semana}:{hora_inicio_norm}-{hora_fim_norm}")
    return redirect(url_for("configuracoes"))


@app.route("/configuracoes/integracoes/salvar", methods=["POST"])
@login_required
def salvar_integracao_canal():
    canal = (request.form.get("canal") or "").strip().lower()
    nome = (request.form.get("nome") or "").strip()
    status = (request.form.get("status") or "rascunho").strip().lower()
    access_token = (request.form.get("access_token") or "").strip()
    phone_number_id = (request.form.get("phone_number_id") or "").strip()
    business_account_id = (request.form.get("business_account_id") or "").strip()
    instagram_account_id = (request.form.get("instagram_account_id") or "").strip()
    config_json_texto = (request.form.get("config_json") or "").strip()

    if canal not in ["whatsapp", "instagram"]:
        flash("Canal invalido para integracao.", "erro")
        return redirect(url_for("configuracoes"))
    if status not in ["rascunho", "ativo", "pausado"]:
        status = "rascunho"

    try:
        config_payload = json.loads(config_json_texto) if config_json_texto else {}
        if not isinstance(config_payload, dict):
            config_payload = {}
    except Exception:
        flash("Config JSON invalido. Mantive a integracao sem salvar.", "erro")
        return redirect(url_for("configuracoes"))

    webhook_token = (request.form.get("webhook_token") or "").strip() or secrets.token_urlsafe(24)
    conn = get_connection()
    existente = conn.execute(
        """
            SELECT id, access_token
            FROM canal_integracoes
            WHERE empresa_id = ? AND canal = ?
            ORDER BY id DESC
        LIMIT 1
        """,
        (obter_empresa_id_logada(), canal)
    ).fetchone()
    if existente:
        conn.execute(
            """
            UPDATE canal_integracoes
            SET nome = ?, status = ?, access_token = ?, webhook_token = ?, phone_number_id = ?,
                business_account_id = ?, instagram_account_id = ?, config_json = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ?
            """,
            (
                nome or canal.title(),
                status,
                access_token or existente["access_token"],
                webhook_token,
                phone_number_id,
                business_account_id,
                instagram_account_id,
                json.dumps(config_payload, ensure_ascii=False),
                existente["id"],
                obter_empresa_id_logada(),
            )
        )
        integracao_id = existente["id"]
    else:
        cursor = conn.execute(
            """
            INSERT INTO canal_integracoes (
                empresa_id, canal, nome, status, access_token, webhook_token, phone_number_id,
                business_account_id, instagram_account_id, config_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obter_empresa_id_logada(),
                canal,
                nome or canal.title(),
                status,
                access_token,
                webhook_token,
                phone_number_id,
                business_account_id,
                instagram_account_id,
                json.dumps(config_payload, ensure_ascii=False),
            )
        )
        integracao_id = cursor.lastrowid
    conn.commit()
    conn.close()
    registrar_evento("integracao_salva", referencia_id=integracao_id, valor=canal)
    return redirect(url_for("configuracoes"))


def buscar_integracao_por_token(canal, token):
    canal = (canal or "").strip().lower()
    token = (token or "").strip()
    if canal not in ["whatsapp", "instagram"] or not token:
        return None
    conn = get_connection()
    integracao = conn.execute(
        """
        SELECT *
        FROM canal_integracoes
        WHERE canal = ? AND webhook_token = ? AND status = 'ativo'
        ORDER BY id DESC
        LIMIT 1
        """,
        (canal, token)
    ).fetchone()
    conn.close()
    return integracao


def parse_config_integracao(integracao):
    if not integracao:
        return {}
    try:
        config = json.loads(integracao["config_json"] or "{}")
        return config if isinstance(config, dict) else {}
    except Exception:
        return {}


def validar_get_webhook_meta(canal, token):
    integracao = buscar_integracao_por_token(canal, token)
    challenge = request.args.get("hub.challenge")
    verify_token_recebido = (request.args.get("hub.verify_token") or "").strip()

    if not integracao:
        return "Integração inativa ou inválida", 404

    config = parse_config_integracao(integracao)
    verify_token_configurado = (config.get("verify_token") or integracao["webhook_token"] or "").strip()
    if verify_token_recebido and verify_token_recebido != verify_token_configurado:
        registrar_evento(
            f"webhook_{canal}_verify_token_invalido",
            referencia_id=integracao["id"],
            empresa_id=integracao["empresa_id"]
        )
        return "Verify token inválido", 403

    return challenge or f"HilFlow {canal.title()} webhook pronto", 200


def validar_assinatura_webhook_meta(integracao, raw_body):
    config = parse_config_integracao(integracao)
    app_secret = (config.get("app_secret") or os.environ.get("META_APP_SECRET") or "").strip()
    if not app_secret:
        return True, "assinatura_nao_configurada"

    assinatura = (request.headers.get("X-Hub-Signature-256") or "").strip()
    if not assinatura.startswith("sha256="):
        return False, "assinatura_ausente"

    assinatura_calculada = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body or b"",
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(assinatura, assinatura_calculada):
        return False, "assinatura_invalida"

    return True, "assinatura_valida"


def receber_webhook_canal_seguro(canal, token):
    integracao = buscar_integracao_por_token(canal, token)
    if not integracao:
        return {"ok": False, "erro": "integracao_inativa_ou_invalida"}, 404

    raw_body = request.get_data() or b""
    assinatura_ok, assinatura_status = validar_assinatura_webhook_meta(integracao, raw_body)
    if not assinatura_ok:
        registrar_evento(
            f"webhook_{canal}_assinatura_invalida",
            referencia_id=integracao["id"],
            valor=assinatura_status,
            empresa_id=integracao["empresa_id"]
        )
        return {"ok": False, "erro": assinatura_status}, 403

    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    resposta, status_code = receber_mensagem_canal(canal, token, payload)
    if status_code < 400:
        resposta["assinatura"] = assinatura_status
    return resposta, status_code


def primeiro_item_lista(valor):
    if isinstance(valor, list) and valor:
        primeiro = valor[0]
        return primeiro if isinstance(primeiro, dict) else {}
    return {}


def mensagem_externa_ja_recebida(empresa_id, canal, external_id):
    external_id = (external_id or "").strip()
    if not empresa_id or not canal or not external_id:
        return None

    conn = get_connection()
    mensagem = conn.execute(
        """
        SELECT
            m.id AS mensagem_id,
            m.conversa_id,
            c.contato_id
        FROM mensagens m
        JOIN conversas c ON c.id = m.conversa_id
        WHERE c.empresa_id = ?
          AND m.canal = ?
          AND m.external_id = ?
          AND m.remetente_tipo = 'cliente'
          AND m.direcao = 'recebida'
        ORDER BY m.id DESC
        LIMIT 1
        """,
        (empresa_id, canal, external_id)
    ).fetchone()
    conn.close()
    return mensagem


def extrair_payload_mensagem_webhook(canal, payload):
    if not isinstance(payload, dict):
        return {"erro": "payload_invalido"}

    canal = (canal or "").strip().lower()
    if canal == "whatsapp":
        entry = primeiro_item_lista(payload.get("entry"))
        change = primeiro_item_lista(entry.get("changes"))
        value = change.get("value") or {}
        mensagem = primeiro_item_lista(value.get("messages"))
        if not mensagem and value.get("statuses"):
            return {"ignorado": True, "motivo": "status_whatsapp"}
        contato = primeiro_item_lista(value.get("contacts"))
        texto = ((mensagem.get("text") or {}).get("body") or payload.get("text") or "").strip()
        telefone = (mensagem.get("from") or payload.get("telefone") or payload.get("from") or "").strip()
        nome = ((contato.get("profile") or {}).get("name") or payload.get("nome") or telefone or "Cliente WhatsApp").strip()
        external_id = (mensagem.get("id") or payload.get("external_id") or "").strip()
        return {"texto": texto, "telefone": telefone, "nome": nome, "external_id": external_id}

    entry = primeiro_item_lista(payload.get("entry"))
    messaging = primeiro_item_lista(entry.get("messaging"))
    mensagem = payload.get("message") or messaging.get("message") or {}
    remetente = payload.get("sender") or messaging.get("sender") or {}
    if not mensagem and messaging:
        return {"ignorado": True, "motivo": "evento_instagram_sem_mensagem"}
    texto = (mensagem.get("text") or payload.get("text") or "").strip()
    telefone = (str(remetente.get("id") or payload.get("instagram_user_id") or payload.get("from") or "")).strip()
    nome = (payload.get("nome") or payload.get("username") or telefone or "Cliente Instagram").strip()
    external_id = (mensagem.get("mid") or payload.get("external_id") or "").strip()
    return {"texto": texto, "telefone": telefone, "nome": nome, "external_id": external_id}


def montar_url_graph_meta(integracao, destino_api):
    config = parse_config_integracao(integracao)

    base_url = (config.get("graph_base_url") or os.environ.get("META_GRAPH_BASE_URL") or "https://graph.facebook.com").rstrip("/")
    graph_version = (config.get("graph_version") or os.environ.get("META_GRAPH_VERSION") or "").strip().strip("/")
    if graph_version:
        return f"{base_url}/{graph_version}/{destino_api}/messages"
    return f"{base_url}/{destino_api}/messages"


def enviar_mensagem_externa_canal(canal, integracao, destinatario, conteudo):
    canal = (canal or "").strip().lower()
    destinatario = (destinatario or "").strip()
    conteudo = (conteudo or "").strip()
    access_token = (integracao["access_token"] or "").strip() if integracao else ""
    if not integracao or canal not in ["whatsapp", "instagram"]:
        return {"ok": False, "envio_real": False, "erro": "integracao_invalida"}
    if not destinatario or not conteudo:
        return {"ok": False, "envio_real": False, "erro": "destinatario_ou_conteudo_vazio"}
    if not access_token:
        return {"ok": False, "envio_real": False, "erro": "access_token_nao_configurado"}

    if canal == "whatsapp":
        phone_number_id = (integracao["phone_number_id"] or "").strip()
        if not phone_number_id:
            return {"ok": False, "envio_real": False, "erro": "phone_number_id_nao_configurado"}
        url = montar_url_graph_meta(integracao, phone_number_id)
        payload = {
            "messaging_product": "whatsapp",
            "to": destinatario,
            "type": "text",
            "text": {"body": conteudo},
        }
    else:
        instagram_account_id = (integracao["instagram_account_id"] or integracao["business_account_id"] or "").strip()
        if not instagram_account_id:
            return {"ok": False, "envio_real": False, "erro": "instagram_account_id_nao_configurado"}
        url = montar_url_graph_meta(integracao, instagram_account_id)
        payload = {
            "recipient": {"id": destinatario},
            "message": {"text": conteudo},
        }

    try:
        resposta = requests.post(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )
        data = resposta.json() if resposta.content else {}
        if resposta.status_code >= 400:
            return {
                "ok": False,
                "envio_real": False,
                "status_code": resposta.status_code,
                "erro": data,
            }
        return {
            "ok": True,
            "envio_real": True,
            "status_code": resposta.status_code,
            "resposta": data,
        }
    except Exception as exc:
        return {"ok": False, "envio_real": False, "erro": str(exc)}


def deve_tentar_reenvio_externo(resultado_envio):
    if not resultado_envio or resultado_envio.get("ok"):
        return False

    status_code = resultado_envio.get("status_code")
    if isinstance(status_code, int):
        return status_code >= 500 or status_code == 429

    erro = resultado_envio.get("erro")
    erros_configuracao = [
        "integracao_invalida",
        "destinatario_ou_conteudo_vazio",
        "access_token_nao_configurado",
        "phone_number_id_nao_configurado",
        "instagram_account_id_nao_configurado",
    ]
    if isinstance(erro, str) and erro in erros_configuracao:
        return False

    return True


def enviar_mensagem_externa_canal_com_retry(canal, integracao, destinatario, conteudo, tentativas=2):
    tentativas = max(1, int(tentativas or 1))
    ultimo_resultado = None

    for tentativa in range(1, tentativas + 1):
        ultimo_resultado = enviar_mensagem_externa_canal(canal, integracao, destinatario, conteudo)
        ultimo_resultado["tentativa"] = tentativa
        ultimo_resultado["tentativas_realizadas"] = tentativa
        if ultimo_resultado.get("ok") or not deve_tentar_reenvio_externo(ultimo_resultado):
            return ultimo_resultado

    return ultimo_resultado or {"ok": False, "envio_real": False, "erro": "envio_nao_realizado", "tentativas_realizadas": 0}


def salvar_mensagem_recebida_canal(canal, integracao, payload):
    dados = extrair_payload_mensagem_webhook(canal, payload)
    if dados.get("ignorado"):
        return {
            "ok": True,
            "ignorado": True,
            "motivo": dados.get("motivo"),
        }, 200
    if dados.get("erro"):
        return {"ok": False, "erro": dados.get("erro")}, 400

    texto = dados.get("texto")
    telefone = dados.get("telefone")
    if not texto or not telefone:
        return {"ok": False, "erro": "mensagem_sem_texto_ou_remetente"}, 400

    duplicada = mensagem_externa_ja_recebida(integracao["empresa_id"], canal, dados.get("external_id"))
    if duplicada:
        registrar_evento(
            f"webhook_{canal}_duplicado",
            referencia_id=duplicada["conversa_id"],
            valor=json.dumps({"external_id": dados.get("external_id")}, ensure_ascii=False),
            empresa_id=integracao["empresa_id"]
        )
        return {
            "ok": True,
            "duplicada": True,
            "canal": canal,
            "conversa_id": duplicada["conversa_id"],
            "contato_id": duplicada["contato_id"],
            "external_id": dados.get("external_id"),
        }, 200

    conn = get_connection()
    contato = conn.execute(
        """
        SELECT id
        FROM contatos
        WHERE empresa_id = ? AND telefone = ?
        LIMIT 1
        """,
        (integracao["empresa_id"], telefone)
    ).fetchone()
    if contato:
        contato_id = contato["id"]
        conn.execute(
            """
            UPDATE contatos
            SET nome = COALESCE(NULLIF(nome, ''), ?),
                origem = COALESCE(NULLIF(origem, ''), ?),
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ?
            """,
            (dados.get("nome"), canal, contato_id, integracao["empresa_id"])
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO contatos (empresa_id, nome, telefone, origem)
            VALUES (?, ?, ?, ?)
            """,
            (integracao["empresa_id"], dados.get("nome"), telefone, canal)
        )
        contato_id = cursor.lastrowid
    conn.commit()
    conn.close()

    conversa_id = buscar_ou_criar_conversa(contato_id, empresa_id=integracao["empresa_id"])
    if not conversa_id:
        return {"ok": False, "erro": "conversa_nao_encontrada"}, 404

    mensagem_id = criar_mensagem(conversa_id, "cliente", texto, "recebida", canal=canal, external_id=dados.get("external_id"))
    if not mensagem_id:
        return {"ok": False, "erro": "mensagem_nao_salva"}, 500

    registrar_evento(
        f"webhook_{canal}_recebido",
        referencia_id=conversa_id,
        valor=json.dumps({"contato_id": contato_id, "external_id": dados.get("external_id")}, ensure_ascii=False),
        empresa_id=integracao["empresa_id"]
    )

    return {
        "ok": True,
        "canal": canal,
        "conversa_id": conversa_id,
        "contato_id": contato_id,
        "mensagem_id": mensagem_id,
        "texto": texto,
        "destinatario": telefone,
        "external_id": dados.get("external_id"),
        "duplicada": False,
    }, 200


def processar_resposta_automatica_canal(canal, integracao, conversa_id, destinatario, texto):
    conn = get_connection()
    conversa = conn.execute(
        "SELECT bot_ativo FROM conversas WHERE id = ? AND empresa_id = ?",
        (conversa_id, integracao["empresa_id"])
    ).fetchone()
    conn.close()
    resposta_bot = None
    regra_id = None
    envio_externo = {"ok": False, "envio_real": False, "erro": "sem_resposta_automatica"}
    if conversa and int(conversa["bot_ativo"] or 0) == 1:
        resposta_bot, regra_id = gerar_resposta_bot(texto, conversa_id)
        if resposta_bot:
            criar_mensagem(conversa_id, "bot", resposta_bot, "enviada", regra_id, canal=canal)
            envio_externo = enviar_mensagem_externa_canal_com_retry(canal, integracao, destinatario, resposta_bot)
            registrar_evento(
                f"resposta_{canal}_enviada" if envio_externo.get("envio_real") else f"resposta_{canal}_preparada",
                referencia_id=conversa_id,
                valor=json.dumps(
                    {
                        "regra_id": regra_id,
                        "envio_real": bool(envio_externo.get("envio_real")),
                        "status_code": envio_externo.get("status_code"),
                        "erro": envio_externo.get("erro"),
                    },
                    ensure_ascii=False
                ),
                empresa_id=integracao["empresa_id"]
            )

    return resposta_bot, regra_id, envio_externo


def receber_mensagem_canal(canal, token, payload):
    integracao = buscar_integracao_por_token(canal, token)
    if not integracao:
        return {"ok": False, "erro": "integracao_inativa_ou_invalida"}, 404

    resultado_salvamento, status_code = salvar_mensagem_recebida_canal(canal, integracao, payload)
    if status_code >= 400 or resultado_salvamento.get("ignorado") or resultado_salvamento.get("duplicada"):
        return resultado_salvamento, status_code

    resposta_bot, regra_id, envio_externo = processar_resposta_automatica_canal(
        canal,
        integracao,
        resultado_salvamento["conversa_id"],
        resultado_salvamento["destinatario"],
        resultado_salvamento["texto"]
    )

    return {
        "ok": True,
        "canal": canal,
        "conversa_id": resultado_salvamento["conversa_id"],
        "contato_id": resultado_salvamento["contato_id"],
        "mensagem_id": resultado_salvamento["mensagem_id"],
        "external_id": resultado_salvamento.get("external_id"),
        "resposta_preparada": resposta_bot,
        "envio_real": bool(envio_externo.get("envio_real")),
        "envio_status": envio_externo,
    }, 200


@app.route("/webhooks/whatsapp/<token>", methods=["GET", "POST"])
@csrf.exempt
def webhook_whatsapp(token):
    if request.method == "GET":
        resposta, status_code = validar_get_webhook_meta("whatsapp", token)
        return resposta, status_code
    resposta, status_code = receber_webhook_canal_seguro("whatsapp", token)
    return jsonify(resposta), status_code


@app.route("/webhooks/instagram/<token>", methods=["GET", "POST"])
@csrf.exempt
def webhook_instagram(token):
    if request.method == "GET":
        resposta, status_code = validar_get_webhook_meta("instagram", token)
        return resposta, status_code
    resposta, status_code = receber_webhook_canal_seguro("instagram", token)
    return jsonify(resposta), status_code


@app.route("/teste-banco")
@login_required
def teste_banco():
    empresa_id = obter_empresa_id_logada()
    conn = get_connection()

    total_contatos = conn.execute(
        "SELECT COUNT(*) AS total FROM contatos WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    total_conversas = conn.execute(
        "SELECT COUNT(*) AS total FROM conversas WHERE empresa_id = ?",
        (empresa_id,)
    ).fetchone()["total"]

    total_mensagens = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens
        WHERE conversa_id IN (
            SELECT id FROM conversas WHERE empresa_id = ?
        )
        """,
        (empresa_id,)
    ).fetchone()["total"]

    total_mensagens_com_regra = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM mensagens
        WHERE regra_id IS NOT NULL
          AND conversa_id IN (
              SELECT id FROM conversas WHERE empresa_id = ?
          )
        """,
        (empresa_id,)
    ).fetchone()["total"]

    total_agendamentos = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE empresa_id = ?
        """,
        (empresa_id,)
    ).fetchone()["total"]

    total_fluxos = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM fluxos
        WHERE empresa_id = ?
        """,
        (empresa_id,)
    ).fetchone()["total"]

    conn.close()

    return f"""
    Banco conectado.<br>
    Empresa logada: {buscar_nome_empresa(empresa_id)}<br>
    Total de contatos: {total_contatos}<br>
    Total de conversas: {total_conversas}<br>
    Total de mensagens: {total_mensagens}<br>
    Total de mensagens com regra: {total_mensagens_com_regra}<br>
    Total de agendamentos: {total_agendamentos}<br>
    Total de fluxos: {total_fluxos}
    """

if __name__ == "__main__":
    app.run(debug=True)

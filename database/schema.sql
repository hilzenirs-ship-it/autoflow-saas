PRAGMA foreign_keys = ON;

-- =========================
-- USUÁRIOS
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- EMPRESAS
-- =========================
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nome_empresa TEXT NOT NULL,
    nome_exibicao TEXT,
    email TEXT,
    telefone TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_empresas_user_id ON empresas(user_id);

-- =========================
-- CONTATOS
-- =========================
CREATE TABLE IF NOT EXISTS contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nome TEXT,
    telefone TEXT NOT NULL,
    email TEXT,
    origem TEXT,
    status_lead TEXT DEFAULT 'novo',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contatos_empresa_id ON contatos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_contatos_telefone ON contatos(telefone);
CREATE INDEX IF NOT EXISTS idx_contatos_empresa_telefone ON contatos(empresa_id, telefone);

-- =========================
-- CONVERSAS
-- =========================
CREATE TABLE IF NOT EXISTS conversas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    contato_id INTEGER NOT NULL,
    status TEXT DEFAULT 'aberta',
    bot_ativo INTEGER DEFAULT 1,
    atendente_nome TEXT,
    etapa TEXT,
    contexto_json TEXT,
    fluxo_id_ativo INTEGER,
    bloco_atual_id INTEGER,
    iniciada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE,
    FOREIGN KEY (fluxo_id_ativo) REFERENCES fluxos(id) ON DELETE SET NULL,
    FOREIGN KEY (bloco_atual_id) REFERENCES fluxo_blocos(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_conversas_empresa_id ON conversas(empresa_id);
CREATE INDEX IF NOT EXISTS idx_conversas_contato_id ON conversas(contato_id);
CREATE INDEX IF NOT EXISTS idx_conversas_status ON conversas(status);
CREATE INDEX IF NOT EXISTS idx_conversas_fluxo_id_ativo ON conversas(fluxo_id_ativo);
CREATE INDEX IF NOT EXISTS idx_conversas_bloco_atual_id ON conversas(bloco_atual_id);

-- =========================
-- FLUXOS
-- =========================
CREATE TABLE IF NOT EXISTS fluxos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    ativo INTEGER DEFAULT 1,
    tipo_gatilho TEXT,
    gatilho_valor TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fluxos_empresa_id ON fluxos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_fluxos_ativo ON fluxos(ativo);
CREATE INDEX IF NOT EXISTS idx_fluxos_tipo_gatilho ON fluxos(tipo_gatilho);

-- =========================
-- BLOCOS DOS FLUXOS
-- =========================
CREATE TABLE IF NOT EXISTS fluxo_blocos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fluxo_id INTEGER NOT NULL,
    tipo_bloco TEXT NOT NULL,
    titulo TEXT NOT NULL,
    conteudo TEXT,
    ordem INTEGER NOT NULL,
    proximo_bloco_id INTEGER,
    config_json TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fluxo_id) REFERENCES fluxos(id) ON DELETE CASCADE,
    FOREIGN KEY (proximo_bloco_id) REFERENCES fluxo_blocos(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_fluxo_blocos_fluxo_id ON fluxo_blocos(fluxo_id);
CREATE INDEX IF NOT EXISTS idx_fluxo_blocos_ordem ON fluxo_blocos(ordem);
CREATE INDEX IF NOT EXISTS idx_fluxo_blocos_proximo_bloco_id ON fluxo_blocos(proximo_bloco_id);

-- =========================
-- REGRAS
-- =========================
CREATE TABLE IF NOT EXISTS regras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    tipo_regra TEXT NOT NULL,
    condicao_json TEXT,
    acao_json TEXT,
    fluxo_id INTEGER,
    ativa INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (fluxo_id) REFERENCES fluxos(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_regras_empresa_id ON regras(empresa_id);
CREATE INDEX IF NOT EXISTS idx_regras_ativa ON regras(ativa);
CREATE INDEX IF NOT EXISTS idx_regras_fluxo_id ON regras(fluxo_id);

-- =========================
-- MENSAGENS
-- =========================
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversa_id INTEGER NOT NULL,
    direcao TEXT NOT NULL, -- recebida / enviada
    remetente_tipo TEXT NOT NULL, -- cliente / bot / humano
    conteudo TEXT NOT NULL,
    regra_id INTEGER,
    user_id INTEGER,
    canal TEXT DEFAULT 'interno',
    external_id TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE CASCADE,
    FOREIGN KEY (regra_id) REFERENCES regras(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_mensagens_conversa_id ON mensagens(conversa_id);
CREATE INDEX IF NOT EXISTS idx_mensagens_regra_id ON mensagens(regra_id);
CREATE INDEX IF NOT EXISTS idx_mensagens_remetente_tipo ON mensagens(remetente_tipo);
CREATE INDEX IF NOT EXISTS idx_mensagens_user_id ON mensagens(user_id);
CREATE INDEX IF NOT EXISTS idx_mensagens_canal ON mensagens(canal);
CREATE INDEX IF NOT EXISTS idx_mensagens_external_id_canal ON mensagens(external_id, canal, remetente_tipo, direcao);

-- =========================
-- ATENDENTES POR CONVERSA
-- =========================
CREATE TABLE IF NOT EXISTS conversa_atendentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversa_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    nome_atendente TEXT,
    papel TEXT DEFAULT 'atendente',
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversa_id, user_id),
    FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversa_atendentes_conversa_id ON conversa_atendentes(conversa_id);
CREATE INDEX IF NOT EXISTS idx_conversa_atendentes_user_id ON conversa_atendentes(user_id);

-- =========================
-- MEMORIA CONTEXTUAL DO CLIENTE
-- =========================
CREATE TABLE IF NOT EXISTS cliente_memorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    contato_id INTEGER NOT NULL,
    resumo TEXT,
    preferencias_json TEXT,
    contexto_json TEXT,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(empresa_id, contato_id),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cliente_memorias_empresa_id ON cliente_memorias(empresa_id);
CREATE INDEX IF NOT EXISTS idx_cliente_memorias_contato_id ON cliente_memorias(contato_id);

-- =========================
-- INTEGRACOES DE CANAIS
-- =========================
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
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_canal_integracoes_empresa_id ON canal_integracoes(empresa_id);
CREATE INDEX IF NOT EXISTS idx_canal_integracoes_canal ON canal_integracoes(canal);
CREATE INDEX IF NOT EXISTS idx_canal_integracoes_webhook_token ON canal_integracoes(webhook_token);

-- =========================
-- PLANOS E LIMITES SAAS
-- =========================
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
);

CREATE TABLE IF NOT EXISTS empresa_limites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL UNIQUE,
    plano_id INTEGER,
    limite_conversas INTEGER,
    limite_mensagens INTEGER,
    limite_atendentes INTEGER,
    limite_integracoes INTEGER,
    status TEXT DEFAULT 'ativo',
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (plano_id) REFERENCES planos_saas(id) ON DELETE SET NULL
);

-- =========================
-- AGENDAMENTOS
-- =========================
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    contato_id INTEGER NOT NULL,
    conversa_id INTEGER,
    servico TEXT,
    data TEXT,
    horario TEXT,
    status TEXT DEFAULT 'confirmado',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE,
    FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agendamentos_empresa_id ON agendamentos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_agendamentos_contato_id ON agendamentos(contato_id);
CREATE INDEX IF NOT EXISTS idx_agendamentos_conversa_id ON agendamentos(conversa_id);
CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data);

-- =========================
-- TAGS
-- =========================
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    cor TEXT,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tags_empresa_id ON tags(empresa_id);

-- =========================
-- RELAÇÃO CONTATO / TAG
-- =========================
CREATE TABLE IF NOT EXISTS contato_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contato_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    FOREIGN KEY (contato_id) REFERENCES contatos(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contato_tags_contato_id ON contato_tags(contato_id);
CREATE INDEX IF NOT EXISTS idx_contato_tags_tag_id ON contato_tags(tag_id);

-- =========================
-- MÉTRICAS / EVENTOS
-- =========================
CREATE TABLE IF NOT EXISTS metricas_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    tipo_evento TEXT NOT NULL,
    referencia_id INTEGER,
    valor TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metricas_eventos_empresa_id ON metricas_eventos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_metricas_eventos_tipo_evento ON metricas_eventos(tipo_evento);

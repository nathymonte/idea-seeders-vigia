-- Modelo de dados do VigIA (SQLite)
-- Criar o banco:  sqlite3 dados/banco/vigia.db < dados/banco/schema.sql

PRAGMA foreign_keys = ON;

-- Cidadãos e gestores (subprefeitura / GCM)
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,                 -- nunca guardar a senha em texto puro (bcrypt)
    perfil      TEXT    NOT NULL DEFAULT 'cidadao'
                CHECK (perfil IN ('cidadao', 'gestor')),
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Relatos enviados pelos cidadãos e classificados pela IA
CREATE TABLE IF NOT EXISTS ocorrencias (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id            INTEGER REFERENCES usuarios(id),      -- vazio quando quem criou foi um sensor
    poste_id              INTEGER REFERENCES postes(id),        -- preenchido quando veio de um poste
    texto                 TEXT    NOT NULL CHECK (length(texto) BETWEEN 5 AND 1000),
    bairro                TEXT    NOT NULL,
    latitude              REAL,
    longitude             REAL,
    anonima               INTEGER NOT NULL DEFAULT 1 CHECK (anonima IN (0, 1)),  -- LGPD: anônima por padrão
    categoria             TEXT    CHECK (categoria IN ('iluminacao', 'roubo_furto', 'assedio', 'vandalismo', 'outros')),
    urgencia              TEXT    CHECK (urgencia IN ('baixa', 'media', 'alta')),
    justificativa_ia      TEXT,
    origem_classificacao  TEXT    CHECK (origem_classificacao IN ('gemini', 'regras', 'sensor', 'carga_inicial')),
    status                TEXT    NOT NULL DEFAULT 'aberta'
                          CHECK (status IN ('aberta', 'em_atendimento', 'resolvida')),
    criada_em             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizada_em         TEXT,
    resolvida_em          TEXT
);

-- Postes inteligentes (simulados no Wokwi)
CREATE TABLE IF NOT EXISTS postes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT    NOT NULL UNIQUE,          -- ex.: 'POSTE-001'
    bairro     TEXT    NOT NULL,
    latitude   REAL,
    longitude  REAL
);

-- Leituras enviadas pelos sensores de cada poste
CREATE TABLE IF NOT EXISTS leituras_sensores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    poste_id    INTEGER NOT NULL REFERENCES postes(id),
    luz_ligada  INTEGER NOT NULL CHECK (luz_ligada IN (0, 1)),   -- LDR
    presenca    INTEGER NOT NULL CHECK (presenca IN (0, 1)),     -- PIR
    panico      INTEGER NOT NULL DEFAULT 0 CHECK (panico IN (0, 1)),  -- botão
    lido_em     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_ocorrencias_bairro_status ON ocorrencias (bairro, status);
CREATE INDEX IF NOT EXISTS idx_leituras_poste_data ON leituras_sensores (poste_id, lido_em);

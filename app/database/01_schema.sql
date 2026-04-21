-- ============================================================
-- SEBRAE Gestão de Contratos — Schema PostgreSQL (Supabase)
-- ============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- AUTENTICAÇÃO E USUÁRIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    login         TEXT UNIQUE NOT NULL,
    nome          TEXT NOT NULL,
    perfil        TEXT NOT NULL CHECK (perfil IN ('admin', 'usuario')),
    senha_hash    TEXT NOT NULL,
    ativo         BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMPTZ,
    criado_em     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABELAS DE CONFIGURAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS unidades (
    id    SERIAL PRIMARY KEY,
    nome  TEXT UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS distribuidores (
    id    SERIAL PRIMARY KEY,
    nome  TEXT UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS atribuidos (
    id    SERIAL PRIMARY KEY,
    nome  TEXT UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS garantias (
    id    SERIAL PRIMARY KEY,
    valor TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS demandas (
    id    SERIAL PRIMARY KEY,
    nome  TEXT UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT true
);

-- ============================================================
-- PRAZOS
-- ============================================================

-- Prazos fixos por etapa
CREATE TABLE IF NOT EXISTS prazos_etapas (
    etapa      TEXT PRIMARY KEY,
    dias_uteis INTEGER NOT NULL
);

-- Prazo de VALIDAÇÃO — variável por demanda
CREATE TABLE IF NOT EXISTS prazos_validacao (
    demanda_id INTEGER PRIMARY KEY REFERENCES demandas(id) ON DELETE CASCADE,
    dias_uteis INTEGER NOT NULL
);

-- ============================================================
-- MATRIZ DE APLICABILIDADE (Demanda × Etapa)
-- ============================================================

CREATE TABLE IF NOT EXISTS demandas_etapas_config (
    demanda_id INTEGER NOT NULL REFERENCES demandas(id) ON DELETE CASCADE,
    etapa      TEXT    NOT NULL,
    -- Etapas possíveis:
    -- 'DATA_VALIDAR', 'VALIDADOR',
    -- 'INICIO_JURIDICO', 'FIM_JURIDICO',
    -- 'ATRIB_ASSINATURA', 'DATA_ATRIB_ASSINATURA', 'FIM_ASSINATURA',
    -- 'ATRIB_CADASTRO', 'DATA_ATRIB_CADASTRO', 'FIM_CADASTRO'
    aplica     BOOLEAN NOT NULL,
    PRIMARY KEY (demanda_id, etapa)
);

-- ============================================================
-- FERIADOS E RECESSOS SEBRAE
-- Tabela crítica — usada em TODOS os cálculos de dias úteis
-- ============================================================

CREATE TABLE IF NOT EXISTS feriados (
    id         SERIAL PRIMARY KEY,
    data       DATE UNIQUE NOT NULL,
    dia_semana TEXT GENERATED ALWAYS AS (
        CASE EXTRACT(DOW FROM data)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda'
            WHEN 2 THEN 'Terça'
            WHEN 3 THEN 'Quarta'
            WHEN 4 THEN 'Quinta'
            WHEN 5 THEN 'Sexta'
            WHEN 6 THEN 'Sábado'
        END
    ) STORED,
    descricao  TEXT NOT NULL,
    tipo       TEXT NOT NULL CHECK (tipo IN (
                    'FERIADO_NACIONAL',
                    'FERIADO_DISTRITAL',
                    'RECESSO_SEBRAE'
               )),
    ativo      BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_feriados_data ON feriados(data) WHERE ativo = true;

-- ============================================================
-- TABELA PRINCIPAL — PROCESSOS
-- Apenas campos de entrada (A:U). Campos calculados
-- (prazos, prev_fim, status, tempo) são computados pelo backend.
-- ============================================================

CREATE TABLE IF NOT EXISTS processos (
    id                       SERIAL PRIMARY KEY,
    numero_processo          TEXT UNIQUE NOT NULL,
    instrumento              TEXT,
    contratada               TEXT,
    unidade_id               INTEGER REFERENCES unidades(id),
    data_entrada             DATE,
    distribuidor_id          INTEGER REFERENCES distribuidores(id),
    tem_garantia             TEXT,
    demanda_id               INTEGER REFERENCES demandas(id),

    -- Distribuição → Atribuição
    data_atribuicao          DATE,
    atribuido_para_id        INTEGER REFERENCES atribuidos(id),

    -- Validação
    data_validar             DATE,
    nao_aplica_validacao     BOOLEAN DEFAULT false,
    validador_id             INTEGER REFERENCES distribuidores(id),

    -- Jurídico
    inicio_juridico          DATE,
    nao_aplica_juridico      BOOLEAN DEFAULT false,
    fim_juridico             DATE,

    -- Assinatura
    atrib_assinatura_id      INTEGER REFERENCES atribuidos(id),
    nao_aplica_assinatura    BOOLEAN DEFAULT false,
    data_atrib_assinatura    DATE,
    fim_assinatura           DATE,

    -- Cadastro (auto-preenchido quando demanda = CADASTRO*)
    atrib_cadastro_id        INTEGER REFERENCES atribuidos(id),
    nao_aplica_cadastro      BOOLEAN DEFAULT false,
    data_atrib_cadastro      DATE,
    fim_cadastro             DATE,

    comentario               TEXT,

    -- Controle
    criado_por               UUID REFERENCES usuarios(id),
    criado_em                TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em            TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para filtros frequentes
CREATE INDEX IF NOT EXISTS idx_processos_demanda   ON processos(demanda_id);
CREATE INDEX IF NOT EXISTS idx_processos_unidade   ON processos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_processos_atribuido ON processos(atribuido_para_id);
CREATE INDEX IF NOT EXISTS idx_processos_entrada   ON processos(data_entrada);
CREATE INDEX IF NOT EXISTS idx_processos_numero    ON processos(numero_processo);

-- Atualiza atualizado_em automaticamente
CREATE OR REPLACE FUNCTION update_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_processos_atualizado_em
    BEFORE UPDATE ON processos
    FOR EACH ROW EXECUTE FUNCTION update_atualizado_em();

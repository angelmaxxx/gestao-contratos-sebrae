-- ============================================================
-- SEBRAE Gestão de Contratos — Dados Iniciais
-- ============================================================

-- ============================================================
-- USUÁRIO ADMINISTRADOR
-- Senha: admin123
-- ============================================================

INSERT INTO usuarios (login, nome, perfil, senha_hash, ativo)
VALUES (
    'admin',
    'Administrador',
    'admin',
    '$2b$12$8fB3rBRhVsNCGFLKTO2p3OhQ.xviSlsNrgzqDRpFLEos0zKHCcoZK',
    true
) ON CONFLICT (login) DO NOTHING;

-- ============================================================
-- GARANTIAS
-- ============================================================

INSERT INTO garantias (valor) VALUES
    ('SIM'), ('NÃO'), ('NÃO SE APLICA')
ON CONFLICT (valor) DO NOTHING;

-- ============================================================
-- UNIDADES (30)
-- ============================================================

INSERT INTO unidades (nome) VALUES
    ('GAB/CDN'), ('GAB/PRESI'), ('GAB/DAF'), ('GAB/DITEC'),
    ('INOVAÇÃO'), ('OUVIDORIA'), ('UAC'), ('UAIN'), ('UARI'),
    ('UAS'), ('UASJUR'), ('UAUD'), ('UCOM'), ('UCOMP'),
    ('UCSEBRAE'), ('UCSF'), ('UDT'), ('UEE'), ('UEFDI'),
    ('UGE'), ('UGF'), ('UGOC'), ('UGP'), ('UGS'), ('UIC'),
    ('UPP'), ('URC'), ('UTIC'), ('UAM'), ('UCOM')
ON CONFLICT (nome) DO NOTHING;

-- ============================================================
-- DISTRIBUIDORES / VALIDADORES (7)
-- ============================================================

INSERT INTO distribuidores (nome) VALUES
    ('NÃO SE APLICA'), ('ANA CAPECCHI'), ('FABRÍCIO ANDRADE'),
    ('NADJA RAMOS'), ('RODRIGO SOARES'), ('SÔNIA PIMENTEL'),
    ('VALÉRIA MELO')
ON CONFLICT (nome) DO NOTHING;

-- ============================================================
-- ATRIBUÍDOS (16)
-- ============================================================

INSERT INTO atribuidos (nome) VALUES
    ('NÃO SE APLICA'), ('ANA CAPECCHI'), ('ANDRESSA FERREIRA'),
    ('ENZO LIMA'), ('FABRÍCIO ANDRADE'), ('HIGOR ROSA'),
    ('LORRANE LEMES'), ('LUIZA FARIA'), ('MAYARA CORDEIRO'),
    ('NADJA RAMOS'), ('PALOMA LIMA'), ('PEDRO SILVA'),
    ('RODRIGO SOARES'), ('SÔNIA PIMENTEL'), ('VALÉRIA MELO')
ON CONFLICT (nome) DO NOTHING;

-- ============================================================
-- DEMANDAS (35)
-- ============================================================

INSERT INTO demandas (nome) VALUES
    ('ADITIVO'), ('ADITIVO ACRÉSCIMO'), ('ADITIVO PRAZO'),
    ('ADITIVO REEQUILÍBRIO'), ('ADITIVO SUPRESSÃO'),
    ('APOST. DEMAIS'), ('APOST. PRORROGAÇÃO'), ('APOST. REAJUSTE'),
    ('APOST. REPACTUAÇÃO'), ('ASSINATURA ADITIVO'),
    ('ASSINATURA APOSTILAMENTO'), ('ASSINATURA ARP'),
    ('ASSINATURA CONTRATO'), ('ASSINATURA DISTRATO'),
    ('CADASTRO ALTERAÇÃO DE GESTOR'), ('CADASTRO ALTERAÇÃO DOT.'),
    ('CADASTRO DE AD'), ('CADASTRO DE AF'), ('CADASTRO DE AP'),
    ('CADASTRO DE ARP'), ('CADASTRO DE CT'), ('CADASTRO DE EV'),
    ('CADASTRO DE FORNECEDOR'), ('CADASTRO DE GESTOR'),
    ('CADASTRO DE SGF'), ('CADASTRO DOTAÇÃO'),
    ('CADASTRO ENCERRAMENTO DE CT'), ('CADASTRO FICHA FINANCEIRA'),
    ('CADASTRO LIBERAÇÃO DE PARCELA'), ('CADASTRO PAT'),
    ('DISTRATO'), ('ELABORAÇÃO DE CONTRATO'), ('ELABORAR ARP'),
    ('PENALIDADE + JURÍDICO'), ('DISTRIBUIÇÃO')
ON CONFLICT (nome) DO NOTHING;

-- ============================================================
-- PRAZOS FIXOS POR ETAPA
-- ============================================================

INSERT INTO prazos_etapas (etapa, dias_uteis) VALUES
    ('DISTRIBUICAO', 3),
    ('JURIDICO',     5),
    ('ASSINATURA',   5),
    ('CADASTRO',     5)
ON CONFLICT (etapa) DO UPDATE SET dias_uteis = EXCLUDED.dias_uteis;

-- ============================================================
-- PRAZOS DE VALIDAÇÃO POR DEMANDA (variável)
-- ============================================================

INSERT INTO prazos_validacao (demanda_id, dias_uteis)
SELECT d.id, p.dias_uteis
FROM (VALUES
    ('ADITIVO',                      10),
    ('ADITIVO ACRÉSCIMO',            10),
    ('ADITIVO PRAZO',                10),
    ('ADITIVO REEQUILÍBRIO',         10),
    ('ADITIVO SUPRESSÃO',            10),
    ('APOST. DEMAIS',                 5),
    ('APOST. PRORROGAÇÃO',            5),
    ('APOST. REAJUSTE',               5),
    ('APOST. REPACTUAÇÃO',            5),
    ('ASSINATURA ADITIVO',            5),
    ('ASSINATURA APOSTILAMENTO',      5),
    ('ASSINATURA ARP',                5),
    ('ASSINATURA CONTRATO',           5),
    ('ASSINATURA DISTRATO',           5),
    ('CADASTRO ALTERAÇÃO DE GESTOR',  5),
    ('CADASTRO ALTERAÇÃO DOT.',       5),
    ('CADASTRO DE AD',                5),
    ('CADASTRO DE AF',                5),
    ('CADASTRO DE AP',                5),
    ('CADASTRO DE ARP',               5),
    ('CADASTRO DE CT',                5),
    ('CADASTRO DE EV',                5),
    ('CADASTRO DE FORNECEDOR',        5),
    ('CADASTRO DE GESTOR',            5),
    ('CADASTRO DE SGF',               5),
    ('CADASTRO DOTAÇÃO',              5),
    ('CADASTRO ENCERRAMENTO DE CT',   5),
    ('CADASTRO FICHA FINANCEIRA',     5),
    ('CADASTRO LIBERAÇÃO DE PARCELA', 5),
    ('CADASTRO PAT',                  5),
    ('DISTRATO',                      5),
    ('ELABORAÇÃO DE CONTRATO',        5),
    ('ELABORAR ARP',                  5),
    ('PENALIDADE + JURÍDICO',        20),
    ('DISTRIBUIÇÃO',                  3)
) AS p(nome, dias_uteis)
JOIN demandas d ON d.nome = p.nome
ON CONFLICT (demanda_id) DO UPDATE SET dias_uteis = EXCLUDED.dias_uteis;

-- ============================================================
-- MATRIZ DE APLICABILIDADE (Demanda × Etapa)
-- Etapas: DATA_VALIDAR, VALIDADOR, INICIO_JURIDICO, FIM_JURIDICO,
--         ATRIB_ASSINATURA, DATA_ATRIB_ASSINATURA, FIM_ASSINATURA,
--         ATRIB_CADASTRO, DATA_ATRIB_CADASTRO, FIM_CADASTRO
-- ============================================================

-- Função auxiliar para inserir configuração
DO $$
DECLARE
    v_id INTEGER;
    -- formato: (nome_demanda, dv, val, ij, fj, aa, daa, fa, ac, dac, fc)
    -- true=APLICA, false=NÃO APLICA
    configs TEXT[][] := ARRAY[
        -- Grupo ADITIVO (pipeline completo)
        ARRAY['ADITIVO',                      't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ADITIVO ACRÉSCIMO',             't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ADITIVO PRAZO',                 't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ADITIVO REEQUILÍBRIO',          't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ADITIVO SUPRESSÃO',             't','t','t','t','t','t','t','t','t','t'],
        -- Grupo APOSTILAMENTO (sem jurídico)
        ARRAY['APOST. DEMAIS',                 't','t','f','f','t','t','t','t','t','t'],
        ARRAY['APOST. PRORROGAÇÃO',            't','t','f','f','t','t','t','t','t','t'],
        ARRAY['APOST. REAJUSTE',               't','t','f','f','t','t','t','t','t','t'],
        ARRAY['APOST. REPACTUAÇÃO',            't','t','f','f','t','t','t','t','t','t'],
        -- Grupo ASSINATURA (sem validação e jurídico)
        ARRAY['ASSINATURA ADITIVO',            'f','f','f','f','t','t','t','t','t','t'],
        ARRAY['ASSINATURA APOSTILAMENTO',      'f','f','f','f','t','t','t','t','t','t'],
        ARRAY['ASSINATURA ARP',                'f','f','f','f','t','t','t','t','t','t'],
        ARRAY['ASSINATURA CONTRATO',           'f','f','f','f','t','t','t','t','t','t'],
        ARRAY['ASSINATURA DISTRATO',           'f','f','f','f','t','t','t','t','t','t'],
        -- Grupo CADASTRO (só etapa cadastro)
        ARRAY['CADASTRO ALTERAÇÃO DE GESTOR',  'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO ALTERAÇÃO DOT.',       'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE AD',                'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE AF',                'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE AP',                'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE ARP',               'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE CT',                'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE EV',                'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE FORNECEDOR',        'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE GESTOR',            'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DE SGF',               'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO DOTAÇÃO',              'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO ENCERRAMENTO DE CT',   'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO FICHA FINANCEIRA',     'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO LIBERAÇÃO DE PARCELA', 'f','f','f','f','f','f','f','t','t','t'],
        ARRAY['CADASTRO PAT',                  'f','f','f','f','f','f','f','t','t','t'],
        -- Outros (pipeline completo)
        ARRAY['DISTRATO',                      't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ELABORAÇÃO DE CONTRATO',        't','t','t','t','t','t','t','t','t','t'],
        ARRAY['ELABORAR ARP',                  't','t','t','t','t','t','t','t','t','t'],
        ARRAY['PENALIDADE + JURÍDICO',         't','t','t','t','t','t','t','t','t','t'],
        ARRAY['DISTRIBUIÇÃO',                  'f','f','f','f','f','f','f','f','f','f']
    ];
    etapas TEXT[] := ARRAY[
        'DATA_VALIDAR','VALIDADOR',
        'INICIO_JURIDICO','FIM_JURIDICO',
        'ATRIB_ASSINATURA','DATA_ATRIB_ASSINATURA','FIM_ASSINATURA',
        'ATRIB_CADASTRO','DATA_ATRIB_CADASTRO','FIM_CADASTRO'
    ];
    cfg TEXT[];
    i INTEGER;
BEGIN
    FOREACH cfg SLICE 1 IN ARRAY configs LOOP
        SELECT id INTO v_id FROM demandas WHERE nome = cfg[1];
        IF v_id IS NULL THEN CONTINUE; END IF;

        FOR i IN 1..10 LOOP
            INSERT INTO demandas_etapas_config (demanda_id, etapa, aplica)
            VALUES (v_id, etapas[i], cfg[i+1] = 't')
            ON CONFLICT (demanda_id, etapa) DO UPDATE SET aplica = EXCLUDED.aplica;
        END LOOP;
    END LOOP;
END $$;

-- ============================================================
-- FERIADOS E RECESSOS SEBRAE 2025–2027
-- ============================================================

INSERT INTO feriados (data, descricao, tipo) VALUES
    -- Recesso SEBRAE Dezembro 2025
    ('2025-12-22', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-23', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-24', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-26', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-29', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-30', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2025-12-31', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    -- 2026
    ('2026-01-01', 'Confraternização Universal', 'FERIADO_NACIONAL'),
    ('2026-01-02', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-02-16', 'Carnaval',                  'FERIADO_NACIONAL'),
    ('2026-02-17', 'Carnaval',                  'FERIADO_NACIONAL'),
    ('2026-02-18', 'Quarta de Cinzas',          'FERIADO_NACIONAL'),
    ('2026-04-03', 'Paixão de Cristo',          'FERIADO_NACIONAL'),
    ('2026-04-20', 'Ponte Tiradentes',          'FERIADO_DISTRITAL'),
    ('2026-04-21', 'Tiradentes',                'FERIADO_NACIONAL'),
    ('2026-05-01', 'Dia do Trabalho',           'FERIADO_NACIONAL'),
    ('2026-06-04', 'Corpus Christi',            'FERIADO_NACIONAL'),
    ('2026-06-05', 'Ponte Corpus Christi',      'FERIADO_DISTRITAL'),
    ('2026-09-07', 'Independência do Brasil',   'FERIADO_NACIONAL'),
    ('2026-10-12', 'N. Sra. Aparecida',         'FERIADO_NACIONAL'),
    ('2026-11-02', 'Finados',                   'FERIADO_NACIONAL'),
    ('2026-11-20', 'Consciência Negra / Zumbi', 'FERIADO_NACIONAL'),
    -- Recesso SEBRAE Dezembro 2026
    ('2026-12-21', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-22', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-23', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-24', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-28', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-29', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-30', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    ('2026-12-31', 'Recesso SEBRAE',            'RECESSO_SEBRAE'),
    -- 2027
    ('2027-01-01', 'Confraternização Universal', 'FERIADO_NACIONAL')
ON CONFLICT (data) DO NOTHING;

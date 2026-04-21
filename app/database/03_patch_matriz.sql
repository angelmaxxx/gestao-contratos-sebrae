-- ============================================================
-- PATCH: Corrige matriz Demanda × Etapas conforme planilha real
-- Execute no SQL Editor do Supabase
-- ============================================================

-- ELABORAÇÃO DE CONTRATO — Jurídico NÃO APLICA
UPDATE demandas_etapas_config SET aplica = false
WHERE demanda_id = (SELECT id FROM demandas WHERE nome = 'ELABORAÇÃO DE CONTRATO')
  AND etapa IN ('INICIO_JURIDICO', 'FIM_JURIDICO');

-- ELABORAR ARP — Jurídico NÃO APLICA
UPDATE demandas_etapas_config SET aplica = false
WHERE demanda_id = (SELECT id FROM demandas WHERE nome = 'ELABORAR ARP')
  AND etapa IN ('INICIO_JURIDICO', 'FIM_JURIDICO');

-- PENALIDADE + JURÍDICO — Assinatura e Cadastro NÃO APLICA
UPDATE demandas_etapas_config SET aplica = false
WHERE demanda_id = (SELECT id FROM demandas WHERE nome = 'PENALIDADE + JURÍDICO')
  AND etapa IN (
    'ATRIB_ASSINATURA','DATA_ATRIB_ASSINATURA','FIM_ASSINATURA',
    'ATRIB_CADASTRO','DATA_ATRIB_CADASTRO','FIM_CADASTRO'
  );

-- DISTRATO — pipeline completo (confirma todos como APLICA)
UPDATE demandas_etapas_config SET aplica = true
WHERE demanda_id = (SELECT id FROM demandas WHERE nome = 'DISTRATO');

-- Verifica resultado
SELECT d.nome, e.etapa, e.aplica
FROM demandas_etapas_config e
JOIN demandas d ON d.id = e.demanda_id
WHERE d.nome IN ('ELABORAÇÃO DE CONTRATO','ELABORAR ARP','PENALIDADE + JURÍDICO')
ORDER BY d.nome, e.etapa;

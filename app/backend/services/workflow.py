"""
Motor de workflow — substitui o Worksheet_Change do VBA.
Define quais etapas se aplicam por tipo de demanda e
auto-preenche campos quando a demanda é do tipo CADASTRO.
"""
from typing import Optional
from datetime import date

ETAPAS = [
    "DATA_VALIDAR", "VALIDADOR",
    "INICIO_JURIDICO", "FIM_JURIDICO",
    "ATRIB_ASSINATURA", "DATA_ATRIB_ASSINATURA", "FIM_ASSINATURA",
    "ATRIB_CADASTRO", "DATA_ATRIB_CADASTRO", "FIM_CADASTRO",
]

# Mapeamento etapa → campo no modelo de Processo
ETAPA_PARA_CAMPO = {
    "DATA_VALIDAR":           "data_validar",
    "VALIDADOR":              "validador_id",
    "INICIO_JURIDICO":        "inicio_juridico",
    "FIM_JURIDICO":           "fim_juridico",
    "ATRIB_ASSINATURA":       "atrib_assinatura_id",
    "DATA_ATRIB_ASSINATURA":  "data_atrib_assinatura",
    "FIM_ASSINATURA":         "fim_assinatura",
    "ATRIB_CADASTRO":         "atrib_cadastro_id",
    "DATA_ATRIB_CADASTRO":    "data_atrib_cadastro",
    "FIM_CADASTRO":           "fim_cadastro",
}

# Campos booleanos de nao_aplica correspondentes
ETAPA_PARA_NAO_APLICA = {
    "DATA_VALIDAR":          "nao_aplica_validacao",
    "VALIDADOR":             "nao_aplica_validacao",
    "INICIO_JURIDICO":       "nao_aplica_juridico",
    "FIM_JURIDICO":          "nao_aplica_juridico",
    "ATRIB_ASSINATURA":      "nao_aplica_assinatura",
    "DATA_ATRIB_ASSINATURA": "nao_aplica_assinatura",
    "FIM_ASSINATURA":        "nao_aplica_assinatura",
    "ATRIB_CADASTRO":        "nao_aplica_cadastro",
    "DATA_ATRIB_CADASTRO":   "nao_aplica_cadastro",
    "FIM_CADASTRO":          "nao_aplica_cadastro",
}


def buscar_config_demanda(db, demanda_id: int) -> dict[str, bool]:
    """Retorna dict etapa -> aplica (bool) para a demanda."""
    res = db.table("demandas_etapas_config") \
            .select("etapa, aplica") \
            .eq("demanda_id", demanda_id) \
            .execute()
    return {r["etapa"]: r["aplica"] for r in res.data}


def is_demanda_cadastro(db, demanda_id: int) -> bool:
    """Verifica se a demanda é do tipo CADASTRO*."""
    res = db.table("demandas").select("nome").eq("id", demanda_id).execute()
    if not res.data:
        return False
    return res.data[0]["nome"].upper().startswith("CADASTRO")


def resolver_etapas(
    db,
    demanda_id: int,
    data_atribuicao: Optional[date] = None,
    atribuido_para_id: Optional[int] = None,
) -> dict:
    """
    Dado o tipo de demanda, retorna para cada etapa:
      - aplica: bool — se a etapa se aplica a esta demanda
      - auto:   bool — se o campo é auto-preenchido (regra CADASTRO)
      - valor:  any  — valor pré-preenchido para campos auto

    Substitui a lógica do Worksheet_Change do VBA.
    """
    config = buscar_config_demanda(db, demanda_id)
    eh_cadastro = is_demanda_cadastro(db, demanda_id)
    resultado = {}

    for etapa in ETAPAS:
        aplica = config.get(etapa, False)
        resultado[etapa] = {
            "aplica": aplica,
            "auto": False,
            "valor": None,
        }

    # Regra especial: demandas CADASTRO* — auto-preenche atribuição e data
    if eh_cadastro:
        resultado["ATRIB_CADASTRO"] = {
            "aplica": True,
            "auto": True,
            "valor": atribuido_para_id,
        }
        resultado["DATA_ATRIB_CADASTRO"] = {
            "aplica": True,
            "auto": True,
            "valor": data_atribuicao.isoformat() if data_atribuicao else None,
        }

    return {
        "etapas": resultado,
        "is_cadastro": eh_cadastro,
    }


def aplicar_nao_aplica(processo_data: dict, config_etapas: dict) -> dict:
    """
    Preenche os campos nao_aplica_* e anula valores de campos
    que não se aplicam à demanda. Chamado antes de salvar no banco.
    """
    etapas_map = {
        "validacao":  ["DATA_VALIDAR", "VALIDADOR"],
        "juridico":   ["INICIO_JURIDICO", "FIM_JURIDICO"],
        "assinatura": ["ATRIB_ASSINATURA", "DATA_ATRIB_ASSINATURA", "FIM_ASSINATURA"],
        "cadastro":   ["ATRIB_CADASTRO", "DATA_ATRIB_CADASTRO", "FIM_CADASTRO"],
    }

    for grupo, etapas in etapas_map.items():
        # O grupo não aplica se NENHUMA das etapas se aplica
        alguma_aplica = any(config_etapas.get(e, {}).get("aplica", False) for e in etapas)
        chave_nao_aplica = f"nao_aplica_{grupo}"

        if not alguma_aplica:
            processo_data[chave_nao_aplica] = True
            for etapa in etapas:
                campo = ETAPA_PARA_CAMPO.get(etapa)
                if campo:
                    processo_data[campo] = None
        else:
            processo_data[chave_nao_aplica] = False

    return processo_data

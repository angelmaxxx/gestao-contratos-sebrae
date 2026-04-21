"""
Motor de status e cálculo de prazos — substitui as colunas AH:AV da planilha.
Todos os valores são calculados em tempo de execução (sem armazenamento no banco).
"""
from datetime import date
from typing import Optional
from services.dias_uteis import add_dias_uteis, count_dias_uteis, carregar_feriados

# Valores de status (espelham os da planilha)
EM_ABERTO_NO_PRAZO      = "EM ABERTO NO PRAZO"
EM_ABERTO_FORA_DO_PRAZO = "EM ABERTO FORA DO PRAZO"
REALIZADO_NO_PRAZO      = "REALIZADO NO PRAZO"
REALIZADO_FORA_DO_PRAZO = "REALIZADO FORA DO PRAZO"
PENDENCIAS              = "PENDÊNCIAS NAS ETAPAS"
NA                      = "N/A"

# ── Caches de prazos ──────────────────────────────────────────────────────────
_cache_prazos_fixos: dict | None = None
_cache_prazos_validacao: dict | None = None   # demanda_id → dias_uteis


def _carregar_prazos_fixos(db) -> dict:
    global _cache_prazos_fixos
    if _cache_prazos_fixos is None:
        res = db.table("prazos_etapas").select("*").execute()
        _cache_prazos_fixos = {r["etapa"]: r["dias_uteis"] for r in res.data}
    return _cache_prazos_fixos


def _carregar_prazos_validacao(db) -> dict:
    global _cache_prazos_validacao
    if _cache_prazos_validacao is None:
        res = db.table("prazos_validacao").select("demanda_id,dias_uteis").execute()
        _cache_prazos_validacao = {r["demanda_id"]: r["dias_uteis"] for r in res.data}
    return _cache_prazos_validacao


def invalidar_cache_prazos():
    """Chame quando prazos_etapas ou prazos_validacao forem alterados."""
    global _cache_prazos_fixos, _cache_prazos_validacao
    _cache_prazos_fixos = None
    _cache_prazos_validacao = None


# ── Lógica de status ──────────────────────────────────────────────────────────

def status_etapa(
    prev_fim: Optional[date],
    data_conclusao: Optional[date],
    nao_aplica: bool = False,
) -> Optional[str]:
    """
    Equivalente às colunas AH:AL da planilha.
    Compara data de conclusão real vs. previsão de fim.
    """
    if nao_aplica:
        return NA
    if prev_fim is None:
        return None
    hoje = date.today()
    if data_conclusao:
        return REALIZADO_NO_PRAZO if data_conclusao <= prev_fim else REALIZADO_FORA_DO_PRAZO
    return EM_ABERTO_NO_PRAZO if hoje <= prev_fim else EM_ABERTO_FORA_DO_PRAZO


def status_total(status_list: list[Optional[str]]) -> Optional[str]:
    """
    Equivalente à coluna AN. Agrega o status de todas as etapas.
    PENDÊNCIAS em qualquer etapa → EM ABERTO FORA DO PRAZO no total.
    """
    validos = [s for s in status_list if s and s != NA]
    if not validos:
        return None
    if any(s in (EM_ABERTO_FORA_DO_PRAZO, PENDENCIAS) for s in validos):
        return EM_ABERTO_FORA_DO_PRAZO
    if any(s == REALIZADO_FORA_DO_PRAZO for s in validos):
        return REALIZADO_FORA_DO_PRAZO
    if any(s == EM_ABERTO_NO_PRAZO for s in validos):
        return EM_ABERTO_NO_PRAZO
    if all(s == REALIZADO_NO_PRAZO for s in validos):
        return REALIZADO_NO_PRAZO
    return None


def responsabilidade(st_total: Optional[str], status_list: list[Optional[str]]) -> Optional[str]:
    """Equivalente à coluna AO."""
    if not st_total:
        return None
    if st_total == REALIZADO_NO_PRAZO:
        return "NO PRAZO"
    if "EM ABERTO" in st_total:
        return "EM ABERTO"
    if st_total == REALIZADO_FORA_DO_PRAZO:
        # Verifica se o atraso foi em etapa interna (CADASTRO = UAC) ou externa
        return "RESPONSABILIDADE UAC"
    return None


def calcular_processo_completo(processo: dict, db) -> dict:
    """
    Recebe um processo (dict com campos A:U) e retorna o dict
    enriquecido com todos os campos calculados para a visão Admin.
    Equivalente às colunas V:AV da planilha.

    Os prazos e feriados são carregados via cache (uma única query por
    ciclo de vida do processo, não por processo).
    """
    feriados       = carregar_feriados(db)
    prazos_fixos   = _carregar_prazos_fixos(db)
    prazos_valid_m = _carregar_prazos_validacao(db)

    prazo_dist = prazos_fixos.get("DISTRIBUICAO", 3)
    prazo_jur  = prazos_fixos.get("JURIDICO",     5)
    prazo_assn = prazos_fixos.get("ASSINATURA",   5)
    prazo_cad  = prazos_fixos.get("CADASTRO",     5)

    # Prazo de validação (variável por demanda — lido do cache)
    demanda_id  = processo.get("demanda_id")
    prazo_valid = prazos_valid_m.get(demanda_id, 5) if demanda_id else 5

    # Datas de entrada
    data_entrada        = _parse_date(processo.get("data_entrada"))
    data_atrib          = _parse_date(processo.get("data_atribuicao"))
    data_validar        = _parse_date(processo.get("data_validar"))
    inicio_juridico     = _parse_date(processo.get("inicio_juridico"))
    fim_juridico        = _parse_date(processo.get("fim_juridico"))
    data_atrib_assn     = _parse_date(processo.get("data_atrib_assinatura"))
    fim_assinatura      = _parse_date(processo.get("fim_assinatura"))
    data_atrib_cad      = _parse_date(processo.get("data_atrib_cadastro"))
    fim_cadastro        = _parse_date(processo.get("fim_cadastro"))

    nao_aplica_valid = processo.get("nao_aplica_validacao", False)
    nao_aplica_jur   = processo.get("nao_aplica_juridico",  False)
    nao_aplica_assn  = processo.get("nao_aplica_assinatura",False)
    nao_aplica_cad   = processo.get("nao_aplica_cadastro",  False)

    # Previsões de fim (WORKDAY.INTL)
    prev_dist  = add_dias_uteis(data_entrada,    prazo_dist,  feriados) if data_entrada   else None
    prev_valid = add_dias_uteis(data_atrib,      prazo_valid, feriados) if (data_atrib and not nao_aplica_valid) else None
    prev_jur   = add_dias_uteis(inicio_juridico, prazo_jur,   feriados) if (inicio_juridico and not nao_aplica_jur) else None
    prev_assn  = add_dias_uteis(data_atrib_assn, prazo_assn,  feriados) if (data_atrib_assn and not nao_aplica_assn) else None
    prev_cad   = add_dias_uteis(data_atrib_cad,  prazo_cad,   feriados) if (data_atrib_cad and not nao_aplica_cad) else None

    # Status por etapa
    st_dist  = status_etapa(prev_dist,  data_atrib,      False)
    st_valid = status_etapa(prev_valid, data_validar,    nao_aplica_valid)

    # Jurídico: PENDÊNCIAS quando aplica mas não iniciou e processo avançou além
    if not nao_aplica_jur and inicio_juridico is None:
        _alem_jur = data_atrib_assn or fim_assinatura or data_atrib_cad or fim_cadastro
        st_jur = PENDENCIAS if _alem_jur else None
    else:
        st_jur = status_etapa(prev_jur, fim_juridico, nao_aplica_jur)

    # Assinatura: PENDÊNCIAS quando aplica mas não atribuída e cadastro avançou
    if not nao_aplica_assn and data_atrib_assn is None:
        _alem_assn = data_atrib_cad or fim_cadastro
        st_assn = PENDENCIAS if _alem_assn else None
    else:
        st_assn = status_etapa(prev_assn, fim_assinatura, nao_aplica_assn)

    st_cad   = status_etapa(prev_cad,   fim_cadastro,    nao_aplica_cad)

    # Status total
    st_total = status_total([st_dist, st_valid, st_jur, st_assn, st_cad])
    resp = responsabilidade(st_total, [st_dist, st_valid, st_jur, st_assn, st_cad])

    # Prazo total (soma dos prazos aplicáveis)
    prazos_aplicaveis = [prazo_dist]
    if not nao_aplica_valid:  prazos_aplicaveis.append(prazo_valid)
    if not nao_aplica_jur:    prazos_aplicaveis.append(prazo_jur)
    if not nao_aplica_assn:   prazos_aplicaveis.append(prazo_assn)
    if not nao_aplica_cad:    prazos_aplicaveis.append(prazo_cad)
    prazo_total = sum(prazos_aplicaveis)

    # Previsão de fim total
    prev_fim_total = add_dias_uteis(data_entrada, prazo_total, feriados) if data_entrada else None

    # Tempo real por etapa (NETWORKDAYS)
    tempo_dist  = count_dias_uteis(data_entrada,    data_atrib,     feriados)
    tempo_valid = count_dias_uteis(data_atrib,       data_validar,   feriados)
    tempo_jur   = count_dias_uteis(inicio_juridico,  fim_juridico,   feriados)
    tempo_assn  = count_dias_uteis(data_atrib_assn,  fim_assinatura, feriados)
    tempo_cad   = count_dias_uteis(data_atrib_cad,   fim_cadastro,   feriados)

    # Data de conclusão mais recente (coluna AM)
    datas_conclusao = [d for d in [data_atrib, data_validar, fim_juridico, fim_assinatura, fim_cadastro] if d]
    data_conclusao_final = max(datas_conclusao) if datas_conclusao else None
    tempo_total = count_dias_uteis(data_entrada, data_conclusao_final, feriados)

    return {
        "calculos": {
            "distribuicao": {
                "prazo_du":   prazo_dist,
                "prev_fim":   prev_dist.isoformat()  if prev_dist  else None,
                "status":     st_dist,
                "tempo_real": tempo_dist,
            },
            "validacao": {
                "prazo_du":   prazo_valid if not nao_aplica_valid else None,
                "prev_fim":   prev_valid.isoformat() if prev_valid else None,
                "status":     st_valid,
                "tempo_real": tempo_valid,
            },
            "juridico": {
                "prazo_du":   prazo_jur if not nao_aplica_jur else None,
                "prev_fim":   prev_jur.isoformat()   if prev_jur   else None,
                "status":     st_jur,
                "tempo_real": tempo_jur,
            },
            "assinatura": {
                "prazo_du":   prazo_assn if not nao_aplica_assn else None,
                "prev_fim":   prev_assn.isoformat()  if prev_assn  else None,
                "status":     st_assn,
                "tempo_real": tempo_assn,
            },
            "cadastro": {
                "prazo_du":   prazo_cad if not nao_aplica_cad else None,
                "prev_fim":   prev_cad.isoformat()   if prev_cad   else None,
                "status":     st_cad,
                "tempo_real": tempo_cad,
            },
            "prazo_total":     prazo_total,
            "prev_fim_total":  prev_fim_total.isoformat() if prev_fim_total else None,
            "status_total":    st_total,
            "responsabilidade": resp,
            "tempo_total":     tempo_total,
        }
    }


def _parse_date(v) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except (ValueError, TypeError):
        return None

"""
Motor de cálculo de dias úteis — substitui WORKDAY.INTL e NETWORKDAYS da planilha.
Consome a tabela feriados do Supabase via cache em memória.
O cache é invalidado sempre que feriados são alterados (via invalidar_cache()).
"""
from datetime import date, timedelta
from typing import Optional

_feriados_cache: set[date] | None = None


def carregar_feriados(db) -> set[date]:
    global _feriados_cache
    if _feriados_cache is None:
        res = db.table("feriados").select("data").eq("ativo", True).execute()
        _feriados_cache = {date.fromisoformat(r["data"]) for r in res.data}
    return _feriados_cache


def invalidar_cache():
    """Chamado sempre que a tabela feriados é modificada."""
    global _feriados_cache
    _feriados_cache = None


def is_dia_util(d: date, feriados: set[date]) -> bool:
    return d.weekday() < 5 and d not in feriados


def add_dias_uteis(inicio: date, n: int, feriados: set[date]) -> date:
    """
    Equivalente a WORKDAY.INTL(inicio, n, 1, feriados).
    Avança n dias úteis a partir de inicio (não conta o próprio inicio).
    """
    if n <= 0:
        return inicio
    atual = inicio
    contados = 0
    while contados < n:
        atual += timedelta(days=1)
        if is_dia_util(atual, feriados):
            contados += 1
    return atual


def count_dias_uteis(inicio: date, fim: Optional[date], feriados: set[date]) -> Optional[int]:
    """
    Equivalente a NETWORKDAYS(inicio, fim, feriados).
    Conta dias úteis entre inicio e fim (inclusive ambos).
    Retorna None se alguma data for None.
    """
    if not inicio or not fim:
        return None
    if fim < inicio:
        return 0
    atual = inicio
    contagem = 0
    while atual <= fim:
        if is_dia_util(atual, feriados):
            contagem += 1
        atual += timedelta(days=1)
    return contagem

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database import get_db
from auth import get_usuario_atual, require_admin
from models import ProcessoCreate, ProcessoUpdate, ResolverEtapasRequest
from services.workflow import resolver_etapas, aplicar_nao_aplica
from services.status import calcular_processo_completo

router = APIRouter(prefix="/processos", tags=["Processos"])

# Campos escalares — sem joins (evita ambiguidade de FK no PostgREST)
CAMPOS = (
    "id, numero_processo, instrumento, contratada, tem_garantia, comentario, "
    "criado_em, atualizado_em, "
    "unidade_id, distribuidor_id, demanda_id, atribuido_para_id, validador_id, "
    "atrib_assinatura_id, atrib_cadastro_id, "
    "data_entrada, data_atribuicao, data_validar, nao_aplica_validacao, "
    "inicio_juridico, nao_aplica_juridico, fim_juridico, "
    "nao_aplica_assinatura, data_atrib_assinatura, fim_assinatura, "
    "nao_aplica_cadastro, data_atrib_cadastro, fim_cadastro"
)

# Cache de lookups para evitar N+1 queries
_cache_lookups: dict = {}

def _carregar_lookups(db) -> dict:
    """Carrega todas as tabelas de referência de uma vez."""
    global _cache_lookups
    if not _cache_lookups:
        unidades      = {r["id"]: r["nome"] for r in db.table("unidades").select("id,nome").execute().data}
        distribuidores= {r["id"]: r["nome"] for r in db.table("distribuidores").select("id,nome").execute().data}
        atribuidos    = {r["id"]: r["nome"] for r in db.table("atribuidos").select("id,nome").execute().data}
        demandas      = {r["id"]: r["nome"] for r in db.table("demandas").select("id,nome").execute().data}
        _cache_lookups = {
            "unidades": unidades,
            "distribuidores": distribuidores,
            "atribuidos": atribuidos,
            "demandas": demandas,
        }
    return _cache_lookups

def invalidar_cache_lookups():
    global _cache_lookups
    _cache_lookups = {}

def _enriquecer(row: dict, is_admin: bool, db, lookups: dict) -> dict:
    """Resolve IDs para nomes e adiciona cálculos para todos os perfis."""
    out = dict(row)
    un  = lookups["unidades"]
    di  = lookups["distribuidores"]
    at  = lookups["atribuidos"]
    de  = lookups["demandas"]

    out["unidade_nome"]          = un.get(out.get("unidade_id"))
    out["distribuidor_nome"]     = di.get(out.get("distribuidor_id"))
    out["demanda_nome"]          = de.get(out.get("demanda_id"))
    out["atribuido_para_nome"]   = at.get(out.get("atribuido_para_id"))
    out["validador_nome"]        = di.get(out.get("validador_id"))
    out["atrib_assinatura_nome"] = at.get(out.get("atrib_assinatura_id"))
    out["atrib_cadastro_nome"]   = at.get(out.get("atrib_cadastro_id"))

    # Calculos disponíveis para todos — admin também pode excluir
    calculos = calcular_processo_completo(row, db)
    out["calculos"] = calculos["calculos"]

    return out


@router.post("/resolver-etapas")
def resolver(body: ResolverEtapasRequest, u=Depends(get_usuario_atual)):
    db = get_db()
    return resolver_etapas(db, body.demanda_id, body.data_atribuicao, body.atribuido_para_id)


@router.get("")
def listar_processos(
    page:         int = Query(1, ge=1),
    por_pagina:   int = Query(50, ge=1, le=200),
    status:       Optional[str] = None,
    unidade_id:   Optional[int] = None,
    atribuido_id: Optional[int] = None,
    demanda_id:   Optional[int] = None,
    busca:        Optional[str] = None,
    u=Depends(get_usuario_atual),
):
    db = get_db()
    is_admin = u.get("perfil") == "admin"
    lookups  = _carregar_lookups(db)

    query = db.table("processos").select(CAMPOS)
    if unidade_id:   query = query.eq("unidade_id", unidade_id)
    if atribuido_id: query = query.eq("atribuido_para_id", atribuido_id)
    if demanda_id:   query = query.eq("demanda_id", demanda_id)
    if busca:        query = query.ilike("numero_processo", f"%{busca}%")

    offset = (page - 1) * por_pagina
    res = query.order("criado_em", desc=True).range(offset, offset + por_pagina - 1).execute()

    dados = [_enriquecer(r, is_admin, db, lookups) for r in res.data]

    if status and is_admin:
        dados = [d for d in dados if (d.get("calculos") or {}).get("status_total") == status]

    return {"data": dados, "page": page, "por_pagina": por_pagina}


@router.get("/dashboard")
def dashboard(u=Depends(get_usuario_atual)):
    """Retorna contadores para os cards do Dashboard."""
    db = get_db()
    lookups = _carregar_lookups(db)

    res  = db.table("processos").select(CAMPOS).execute()
    todos = [_enriquecer(r, True, db, lookups) for r in res.data]

    from datetime import date, timedelta
    trinta_dias_atras = date.today() - timedelta(days=30)

    fora_prazo, no_prazo, pendencias, concluidos = [], [], [], []

    for p in todos:
        st = (p.get("calculos") or {}).get("status_total", "")
        if st == "EM ABERTO FORA DO PRAZO":
            fora_prazo.append(p)
        elif st == "EM ABERTO NO PRAZO":
            no_prazo.append(p)
        elif "PENDÊNCIA" in (st or ""):
            pendencias.append(p)
        elif "REALIZADO" in (st or ""):
            data_upd = (p.get("atualizado_em") or "")[:10]
            try:
                if date.fromisoformat(data_upd) >= trinta_dias_atras:
                    concluidos.append(p)
            except ValueError:
                pass

    return {
        "fora_prazo": {"total": len(fora_prazo), "processos": fora_prazo[:20]},
        "no_prazo":   {"total": len(no_prazo),   "processos": no_prazo[:20]},
        "pendencias": {"total": len(pendencias), "processos": pendencias[:20]},
        "concluidos": {"total": len(concluidos), "processos": concluidos[:20]},
        "total_geral": len(todos),
    }


@router.get("/exportar")
def exportar_processos(admin=Depends(require_admin)):
    """Retorna todos os processos com dados completos (incluindo cálculos) para exportação CSV."""
    db = get_db()
    lookups = _carregar_lookups(db)
    res = db.table("processos").select(CAMPOS).order("criado_em", desc=True).execute()
    return [_enriquecer(r, True, db, lookups) for r in res.data]


@router.get("/{processo_id}")
def obter_processo(processo_id: int, u=Depends(get_usuario_atual)):
    db = get_db()
    is_admin = u.get("perfil") == "admin"
    lookups  = _carregar_lookups(db)
    res = db.table("processos").select(CAMPOS).eq("id", processo_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return _enriquecer(res.data[0], is_admin, db, lookups)


@router.post("")
def criar_processo(body: ProcessoCreate, u=Depends(get_usuario_atual)):
    db = get_db()

    existe = db.table("processos").select("id").eq("numero_processo", body.numero_processo).execute()
    if existe.data:
        raise HTTPException(status_code=400, detail="Número de processo já cadastrado")

    dados = body.model_dump(mode="json")
    if dados.get("demanda_id"):
        cfg = resolver_etapas(db, dados["demanda_id"], body.data_atribuicao, body.atribuido_para_id)
        dados = aplicar_nao_aplica(dados, cfg["etapas"])

    dados["criado_por"] = u["id"]
    res = db.table("processos").insert(dados).execute()
    invalidar_cache_lookups()
    return res.data[0]


@router.put("/{processo_id}")
def atualizar_processo(processo_id: int, body: ProcessoUpdate, u=Depends(get_usuario_atual)):
    db = get_db()

    existe = db.table("processos").select("id").eq("id", processo_id).execute()
    if not existe.data:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    dados = body.model_dump(mode="json", exclude_none=True)
    if dados.get("demanda_id"):
        cfg = resolver_etapas(db, dados["demanda_id"],
                              dados.get("data_atribuicao"),
                              dados.get("atribuido_para_id"))
        dados = aplicar_nao_aplica(dados, cfg["etapas"])

    res = db.table("processos").update(dados).eq("id", processo_id).execute()
    return res.data[0]


@router.delete("/{processo_id}")
def excluir_processo(processo_id: int, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("processos").delete().eq("id", processo_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return {"ok": True}

from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import require_admin, get_usuario_atual
from models import ItemNome, PrazoEtapaUpdate, PrazoValidacaoUpdate

router = APIRouter(prefix="/config", tags=["Configurações"])


# ── Dados públicos (usados nos dropdowns) ──────────────────────────────────────

@router.get("/unidades")
def listar_unidades(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("unidades").select("id,nome").eq("ativo", True).order("nome").execute().data


@router.get("/distribuidores")
def listar_distribuidores(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("distribuidores").select("id,nome").eq("ativo", True).order("nome").execute().data


@router.get("/atribuidos")
def listar_atribuidos(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("atribuidos").select("id,nome").eq("ativo", True).order("nome").execute().data


@router.get("/demandas")
def listar_demandas(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("demandas").select("id,nome").eq("ativo", True).order("nome").execute().data


@router.get("/garantias")
def listar_garantias(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("garantias").select("id,valor").order("id").execute().data


@router.get("/prazos")
def listar_prazos(u=Depends(get_usuario_atual)):
    db = get_db()
    fixos = db.table("prazos_etapas").select("*").execute().data
    return {"fixos": fixos}


@router.get("/prazos-validacao")
def listar_prazos_validacao(u=Depends(get_usuario_atual)):
    """Retorna o prazo de validação (d.u.) de cada demanda ativa."""
    db = get_db()
    demandas = db.table("demandas").select("id,nome").eq("ativo", True).order("nome").execute().data
    prazos   = db.table("prazos_validacao").select("demanda_id,dias_uteis").execute().data
    prazo_map = {p["demanda_id"]: p["dias_uteis"] for p in prazos}
    return [
        {"demanda_id": d["id"], "nome": d["nome"], "dias_uteis": prazo_map.get(d["id"], 5)}
        for d in demandas
    ]


@router.put("/prazos-validacao/{demanda_id}")
def atualizar_prazo_validacao(demanda_id: int, body: PrazoValidacaoUpdate, admin=Depends(require_admin)):
    """Atualiza (ou cria) o prazo de validação para uma demanda."""
    from services.status import invalidar_cache_prazos
    if body.dias_uteis < 1 or body.dias_uteis > 365:
        raise HTTPException(status_code=400, detail="Prazo deve ser entre 1 e 365 dias úteis")
    db = get_db()
    existe = db.table("prazos_validacao").select("demanda_id").eq("demanda_id", demanda_id).execute()
    if existe.data:
        db.table("prazos_validacao").update({"dias_uteis": body.dias_uteis}).eq("demanda_id", demanda_id).execute()
    else:
        db.table("prazos_validacao").insert({"demanda_id": demanda_id, "dias_uteis": body.dias_uteis}).execute()
    invalidar_cache_prazos()
    return {"ok": True}


# ── Configuração de etapas por demanda (workflow) ─────────────────────────────

@router.get("/matriz")
def config_matriz_completa(u=Depends(get_usuario_atual)):
    """Retorna toda a matriz demanda × etapas em uma única query."""
    db = get_db()
    demandas = db.table("demandas").select("id,nome").eq("ativo", True).order("nome").execute().data
    configs  = db.table("demandas_etapas_config").select("demanda_id,etapa,aplica").execute().data
    # Agrupa configs por demanda_id
    cfg_map: dict = {}
    for c in configs:
        cfg_map.setdefault(c["demanda_id"], {})[c["etapa"]] = c["aplica"]
    return [
        {"id": d["id"], "nome": d["nome"], "etapas": cfg_map.get(d["id"], {})}
        for d in demandas
    ]


@router.get("/demandas/{demanda_id}/etapas")
def config_etapas_demanda(demanda_id: int, u=Depends(get_usuario_atual)):
    db = get_db()
    res = db.table("demandas_etapas_config") \
            .select("etapa,aplica") \
            .eq("demanda_id", demanda_id) \
            .execute()
    return {r["etapa"]: r["aplica"] for r in res.data}


# ── Endpoints admin ────────────────────────────────────────────────────────────

@router.post("/unidades")
def criar_unidade(body: ItemNome, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("unidades").insert({"nome": body.nome.upper()}).execute()
    return res.data[0]


@router.delete("/unidades/{id}")
def excluir_unidade(id: int, admin=Depends(require_admin)):
    db = get_db()
    db.table("unidades").update({"ativo": False}).eq("id", id).execute()
    return {"ok": True}


@router.post("/atribuidos")
def criar_atribuido(body: ItemNome, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("atribuidos").insert({"nome": body.nome.upper()}).execute()
    return res.data[0]


@router.delete("/atribuidos/{id}")
def excluir_atribuido(id: int, admin=Depends(require_admin)):
    db = get_db()
    db.table("atribuidos").update({"ativo": False}).eq("id", id).execute()
    return {"ok": True}


@router.post("/distribuidores")
def criar_distribuidor(body: ItemNome, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("distribuidores").insert({"nome": body.nome.upper()}).execute()
    return res.data[0]


@router.delete("/distribuidores/{id}")
def excluir_distribuidor(id: int, admin=Depends(require_admin)):
    db = get_db()
    db.table("distribuidores").update({"ativo": False}).eq("id", id).execute()
    return {"ok": True}


@router.put("/prazos")
def atualizar_prazo(body: PrazoEtapaUpdate, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("prazos_etapas").update({"dias_uteis": body.dias_uteis}).eq("etapa", body.etapa).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    return res.data[0]


@router.post("/demandas")
def criar_demanda(body: ItemNome, admin=Depends(require_admin)):
    """Cria uma nova demanda e habilita todas as etapas por padrão."""
    db = get_db()
    # Verifica duplicata
    existe = db.table("demandas").select("id").eq("nome", body.nome.upper()).execute()
    if existe.data:
        raise HTTPException(status_code=400, detail="Demanda já cadastrada com esse nome")
    res = db.table("demandas").insert({"nome": body.nome.upper()}).execute()
    nova = res.data[0]
    # Cria configuração padrão (todas as etapas APLICA)
    etapas = [
        "DATA_VALIDAR", "VALIDADOR",
        "INICIO_JURIDICO", "FIM_JURIDICO",
        "ATRIB_ASSINATURA", "DATA_ATRIB_ASSINATURA", "FIM_ASSINATURA",
        "ATRIB_CADASTRO", "DATA_ATRIB_CADASTRO", "FIM_CADASTRO",
    ]
    rows = [{"demanda_id": nova["id"], "etapa": e, "aplica": True} for e in etapas]
    db.table("demandas_etapas_config").insert(rows).execute()
    return nova


@router.delete("/demandas/{id}")
def excluir_demanda(id: int, admin=Depends(require_admin)):
    """Desativa uma demanda (soft delete)."""
    db = get_db()
    existe = db.table("demandas").select("id").eq("id", id).execute()
    if not existe.data:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    db.table("demandas").update({"ativo": False}).eq("id", id).execute()
    return {"ok": True}


@router.put("/demandas/{demanda_id}/etapas")
def atualizar_config_etapas(demanda_id: int, config: dict, admin=Depends(require_admin)):
    """Atualiza a matriz APLICA/NÃO APLICA para uma demanda."""
    db = get_db()
    for etapa, aplica in config.items():
        db.table("demandas_etapas_config") \
          .upsert({"demanda_id": demanda_id, "etapa": etapa, "aplica": bool(aplica)}) \
          .execute()
    return {"ok": True}

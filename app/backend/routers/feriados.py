from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import require_admin, get_usuario_atual
from models import FeriadoCreate, FeriadoOut
from services.dias_uteis import invalidar_cache

router = APIRouter(prefix="/feriados", tags=["Feriados"])


@router.get("", response_model=list[FeriadoOut])
def listar_feriados(u=Depends(get_usuario_atual)):
    db = get_db()
    return db.table("feriados").select("*").eq("ativo", True).order("data").execute().data


@router.post("", response_model=FeriadoOut)
def criar_feriado(body: FeriadoCreate, admin=Depends(require_admin)):
    db = get_db()
    existe = db.table("feriados").select("id").eq("data", body.data.isoformat()).execute()
    if existe.data:
        raise HTTPException(status_code=400, detail="Já existe feriado nesta data")

    res = db.table("feriados").insert({
        "data":      body.data.isoformat(),
        "descricao": body.descricao,
        "tipo":      body.tipo,
        "ativo":     True,
    }).execute()

    invalidar_cache()  # Recalcula dias úteis com novo feriado
    return res.data[0]


@router.put("/{feriado_id}", response_model=FeriadoOut)
def atualizar_feriado(feriado_id: int, body: FeriadoCreate, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("feriados").update({
        "data":      body.data.isoformat(),
        "descricao": body.descricao,
        "tipo":      body.tipo,
    }).eq("id", feriado_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Feriado não encontrado")

    invalidar_cache()
    return res.data[0]


@router.delete("/{feriado_id}")
def excluir_feriado(feriado_id: int, admin=Depends(require_admin)):
    db = get_db()
    res = db.table("feriados").update({"ativo": False}).eq("id", feriado_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Feriado não encontrado")
    invalidar_cache()
    return {"ok": True}

from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from auth import require_admin, hash_senha, get_usuario_atual
from models import UsuarioCreate, UsuarioUpdate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(admin=Depends(require_admin)):
    db = get_db()
    res = db.table("usuarios").select("id,login,nome,perfil,ativo,ultimo_acesso,criado_em") \
            .order("nome").execute()
    return res.data


@router.post("", response_model=UsuarioOut)
def criar_usuario(body: UsuarioCreate, admin=Depends(require_admin)):
    db = get_db()
    existe = db.table("usuarios").select("id").eq("login", body.login).execute()
    if existe.data:
        raise HTTPException(status_code=400, detail="Login já existe")

    novo = {
        "login":      body.login,
        "nome":       body.nome,
        "perfil":     body.perfil,
        "senha_hash": hash_senha(body.senha),
        "ativo":      True,
    }
    res = db.table("usuarios").insert(novo).execute()
    return res.data[0]


@router.put("/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(usuario_id: str, body: UsuarioUpdate, admin=Depends(require_admin)):
    db = get_db()
    updates = body.model_dump(exclude_none=True)

    if "senha" in updates:
        updates["senha_hash"] = hash_senha(updates.pop("senha"))

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    res = db.table("usuarios").update(updates).eq("id", usuario_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return res.data[0]


@router.get("/me")
def meu_perfil(usuario=Depends(get_usuario_atual)):
    return {k: v for k, v in usuario.items() if k != "senha_hash"}

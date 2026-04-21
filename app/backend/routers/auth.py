from fastapi import APIRouter, HTTPException
from database import get_db
from auth import verificar_senha, criar_token
from models import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/ping")
def ping():
    """Endpoint leve para keep-alive — evita hibernação do servidor gratuito."""
    return {"ok": True}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    db = get_db()
    res = db.table("usuarios").select("*").eq("login", body.login).eq("ativo", True).execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="Login ou senha inválidos")

    usuario = res.data[0]
    if not verificar_senha(body.senha, usuario["senha_hash"]):
        raise HTTPException(status_code=401, detail="Login ou senha inválidos")

    token = criar_token({"sub": usuario["login"], "perfil": usuario["perfil"]})
    return TokenResponse(token=token, perfil=usuario["perfil"], nome=usuario["nome"])

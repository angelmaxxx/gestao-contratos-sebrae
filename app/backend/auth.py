from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from database import get_db, settings

bearer_scheme = HTTPBearer()


def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha_plain.encode("utf-8"), senha_hash.encode("utf-8"))


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def criar_token(dados: dict) -> str:
    payload = dados.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    payload = decodificar_token(credentials.credentials)
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token inválido")

    db = get_db()
    res = db.table("usuarios").select("*").eq("login", payload["sub"]).eq("ativo", True).execute()
    if not res.data:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")

    usuario = res.data[0]
    # Atualiza último acesso
    db.table("usuarios").update({"ultimo_acesso": datetime.utcnow().isoformat()}).eq("id", usuario["id"]).execute()
    return usuario


def require_admin(usuario: dict = Depends(get_usuario_atual)) -> dict:
    if usuario.get("perfil") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    return usuario

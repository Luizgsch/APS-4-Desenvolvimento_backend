from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from schema.auth_schema import LoginCreate, TokenRead
from service.auth_service import autenticar
from schema.usuario_schema import UsuarioRead
from security.dependencies import get_usuario_atual


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/me", response_model=UsuarioRead)
def me(response: Response, usuario: UsuarioRead = Depends(get_usuario_atual)):
    response.headers["Cache-Control"] = "no-store"
    return usuario


@router.post("/login", response_model=TokenRead)
def login(recebido: LoginCreate, response: Response, db: Session = Depends(get_db)):
    try:
        token = autenticar(db, recebido)
    except ValueError:
        # Erros de configuração não são falhas de credenciais do cliente.
        raise HTTPException(503, "Serviço de autenticação indisponível.") from None
    if token is None:
        raise HTTPException(401, "E-mail ou senha inválidos.", headers={"WWW-Authenticate": "Bearer"})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return token

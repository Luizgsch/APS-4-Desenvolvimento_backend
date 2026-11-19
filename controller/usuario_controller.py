from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schema.usuario_schema import UsuarioCreate, UsuarioRead
from service.erros import EmailDuplicadoError
from service.usuario_service import criar_usuario


router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(recebido: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return criar_usuario(db, recebido)
    except EmailDuplicadoError:
        raise HTTPException(409, "Já existe um usuário cadastrado com este e-mail.") from None

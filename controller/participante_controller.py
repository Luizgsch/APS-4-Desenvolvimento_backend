from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from security.dependencies import get_usuario_atual, get_administrador
from schema.participante_schema import ParticipanteCreate, ParticipanteRead, ParticipanteUpdate
from service.erros import EmailDuplicadoError
from service.participante_service import criar_participante, retornar_participantes, pesquisar_participante, atualizar_participante, excluir_participante

router = APIRouter(prefix="/participantes", tags=["Participantes"], dependencies=[Depends(get_usuario_atual)])

@router.post("", response_model=ParticipanteRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_administrador)])
def cadastrar_participante(recebido: ParticipanteCreate, db: Session = Depends(get_db)):
    try:
        return criar_participante(db, recebido)
    except EmailDuplicadoError:
        raise HTTPException(409, "Já existe um participante cadastrado com este e-mail.") from None

@router.get("", response_model=list[ParticipanteRead])
def listar_participantes(db: Session = Depends(get_db)):
    return retornar_participantes(db)

@router.get("/{id}", response_model=ParticipanteRead)
def consultar_participante(id: int, db: Session = Depends(get_db)):
    item = pesquisar_participante(db, id)
    if item is None:
        raise HTTPException(404, "Participante não encontrado.")
    return item

@router.put("/{id}", response_model=ParticipanteRead, dependencies=[Depends(get_administrador)])
def alterar_participante(id: int, recebido: ParticipanteUpdate, db: Session = Depends(get_db)):
    try:
        item = atualizar_participante(db, id, recebido)
    except EmailDuplicadoError:
        raise HTTPException(409, "Já existe um participante cadastrado com este e-mail.") from None
    if item is None:
        raise HTTPException(404, "Participante não encontrado.")
    return item

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_administrador)])
def deletar_participante(id: int, db: Session = Depends(get_db)):
    if not excluir_participante(db, id):
        raise HTTPException(404, "Participante não encontrado.")
    return Response(status_code=204)

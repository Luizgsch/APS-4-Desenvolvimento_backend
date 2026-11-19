from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from security.dependencies import get_administrador
from schema.evento_schema import EventoCreate, EventoRead, EventoUpdate
from service.erros import CapacidadeInsuficienteError
from service.evento_service import criar_evento, retornar_eventos, pesquisar_evento, atualizar_evento, excluir_evento

router = APIRouter(prefix="/eventos", tags=["Eventos"])

@router.post("", response_model=EventoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_administrador)])
def criar_eventos(evento_recebido: EventoCreate, db: Session = Depends(get_db)):
    return criar_evento(db, evento_recebido)

@router.get("", response_model=list[EventoRead])
def ver_eventos(db: Session = Depends(get_db)):
    return retornar_eventos(db)

@router.get("/{id}", response_model=EventoRead)
def listar_evento(id: int, db: Session = Depends(get_db)):
    evento_encontrado = pesquisar_evento(db, id)
    if evento_encontrado is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return evento_encontrado

@router.put("/{id}", response_model=EventoRead, dependencies=[Depends(get_administrador)])
def trocar_evento(id: int, evento_recebido: EventoUpdate, db: Session = Depends(get_db)):
    try:
        evento_atualizado = atualizar_evento(db, id, evento_recebido)
    except CapacidadeInsuficienteError:
        raise HTTPException(409, "Capacidade não pode ser menor que a quantidade de inscritos.") from None
    if evento_atualizado is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return evento_atualizado

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_administrador)])
def deletar_evento(id: int, db: Session = Depends(get_db)):
    if not excluir_evento(db, id):
        raise HTTPException(
            status_code=404,
            detail="Evento não encontrado."
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from database import get_db
from security.dependencies import get_usuario_atual
from schema.participante_schema import ParticipanteRead
from schema.inscricao_schema import InscricaoRead
from service.inscricao_service import criar_inscricao, retornar_inscritos

router = APIRouter(tags=["Inscrições"])

@router.post("/eventos/{evento_id}/inscricoes/{participante_id}", response_model=InscricaoRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_usuario_atual)])
def inscrever_participante(evento_id: int = Path(gt=0), participante_id: int = Path(gt=0), db: Session = Depends(get_db)):
    item, erro = criar_inscricao(db, evento_id, participante_id)
    erros = {
        "evento_nao_encontrado": (404, "Evento não encontrado."),
        "participante_nao_encontrado": (404, "Participante não encontrado."),
        "ja_inscrito": (409, "Participante já está inscrito neste evento."),
        "sem_vagas": (409, "Não existem vagas disponíveis para este evento."),
    }
    if erro:
        codigo, detalhe = erros[erro]
        raise HTTPException(codigo, detalhe)
    return item

@router.get("/eventos/{evento_id}/inscricoes", response_model=list[ParticipanteRead], dependencies=[Depends(get_usuario_atual)])
def listar_inscritos(evento_id: int = Path(gt=0), db: Session = Depends(get_db)):
    itens = retornar_inscritos(db, evento_id)
    if itens is None:
        raise HTTPException(404, "Evento não encontrado.")
    return itens

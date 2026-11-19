from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from security.dependencies import get_administrador
from schema.relatorio_schema import CategoriaEventosRead, CursoParticipantesRead, OcupacaoEventoRead
from service.relatorio_service import eventos_por_categoria, ocupacao_eventos, participantes_por_curso


router = APIRouter(prefix="/relatorios", tags=["Relatórios"], dependencies=[Depends(get_administrador)])


@router.get("/eventos/ocupacao", response_model=list[OcupacaoEventoRead])
def relatorio_ocupacao(db: Session = Depends(get_db)):
    return ocupacao_eventos(db)


@router.get("/eventos/categorias", response_model=list[CategoriaEventosRead])
def relatorio_categorias(db: Session = Depends(get_db)):
    return eventos_por_categoria(db)


@router.get("/participantes/cursos", response_model=list[CursoParticipantesRead])
def relatorio_cursos(db: Session = Depends(get_db)):
    return participantes_por_curso(db)

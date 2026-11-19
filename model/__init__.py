"""Registra todas as entidades na Base compartilhada."""

from model.evento import Evento
from model.participante import Participante
from model.inscricao import Inscricao
from model.usuario import Usuario

__all__ = ["Evento", "Participante", "Inscricao", "Usuario"]

"""Cadastro público e criação administrativa pelo procedimento local."""

import sqlite3

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from model import Usuario
from schema.usuario_schema import UsuarioCreate, UsuarioRead
from security.passwords import gerar_hash
from service.erros import EmailDuplicadoError


def criar_usuario(db: Session, recebido: UsuarioCreate) -> UsuarioRead:
    return _salvar_usuario(db, recebido, "usuario")


def criar_administrador(db: Session, recebido: UsuarioCreate) -> UsuarioRead:
    """Uso exclusivo pelo comando local; não promove contas existentes."""
    return _salvar_usuario(db, recebido, "administrador")


def _salvar_usuario(db: Session, recebido: UsuarioCreate, perfil: str) -> UsuarioRead:
    if perfil not in {"usuario", "administrador"}:
        raise ValueError("Perfil de acesso inválido.")
    usuario = Usuario(
        nome=recebido.nome,
        email=str(recebido.email),
        senha_hash=gerar_hash(recebido.senha.get_secret_value()),
        perfil=perfil,
    )
    db.add(usuario)
    try:
        db.flush()
        resultado = UsuarioRead.model_validate(usuario)
        db.commit()
        return resultado
    except IntegrityError as erro:
        db.rollback()
        if (
            isinstance(erro.orig, sqlite3.IntegrityError)
            and getattr(erro.orig, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            and str(erro.orig) == "UNIQUE constraint failed: usuarios.email"
        ):
            raise EmailDuplicadoError() from None
        raise

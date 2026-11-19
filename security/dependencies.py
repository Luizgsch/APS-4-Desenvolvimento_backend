"""Identidade Bearer centralizada, obtida do usuário atual no banco."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import database
from model import Usuario
from schema.usuario_schema import UsuarioRead
from security.tokens import TokenInvalidoError, validar_token


bearer = HTTPBearer(auto_error=False, scheme_name="BearerJWT", bearerFormat="JWT")


def credenciais_invalidas() -> HTTPException:
    return HTTPException(
        401, "Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UsuarioRead:
    if credentials is None:
        raise credenciais_invalidas()
    try:
        usuario_id = validar_token(credentials.credentials)
    except TokenInvalidoError:
        raise credenciais_invalidas() from None
    except ValueError:
        raise HTTPException(503, "Serviço de autenticação indisponível.") from None

    # A leitura da identidade termina antes da transação de negócio. Compartilhar
    # uma sessão manteria uma leitura SQLite aberta antes do bloqueio de escrita.
    with database.SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if usuario is None:
            raise credenciais_invalidas()
        return UsuarioRead.model_validate(usuario)


def get_administrador(usuario: UsuarioRead = Depends(get_usuario_atual)) -> UsuarioRead:
    """Usa o perfil carregado do banco; nenhuma claim concede privilégios."""
    if usuario.perfil != "administrador":
        raise HTTPException(403, "Você não possui permissão para executar esta operação.")
    return usuario

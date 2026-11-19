"""Verificação de credenciais e emissão de token, sem lógica HTTP."""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from model import Usuario
from schema.auth_schema import LoginCreate, TokenRead
from security.passwords import gerar_hash, verificar_senha
from security.tokens import criar_token


# Mantém uma verificação Argon2 também quando o e-mail não está cadastrado.
# Não é uma credencial de usuário e nunca é persistida.
_HASH_FICTICIO = gerar_hash(secrets.token_urlsafe(32))


def autenticar(db: Session, recebido: LoginCreate) -> TokenRead | None:
    usuario = db.scalar(select(Usuario).where(Usuario.email == str(recebido.email)))
    senha_correta = verificar_senha(
        recebido.senha.get_secret_value(),
        usuario.senha_hash if usuario is not None else _HASH_FICTICIO,
    )
    if usuario is None or not senha_correta:
        return None
    return TokenRead(access_token=criar_token(usuario.id))

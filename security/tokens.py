"""Emissão e validação JWT sem confiar em parâmetros fornecidos pelo cliente."""

from datetime import datetime, timedelta, timezone
import re

import jwt

from security.config import load_security_settings


class TokenInvalidoError(Exception):
    """Token não aceito; não inclui o token nem detalhes criptográficos."""


def criar_token(usuario_id: int) -> str:
    if type(usuario_id) is not int or not 0 < usuario_id <= 9223372036854775807:
        raise ValueError("Identificador de usuário inválido.")
    settings = load_security_settings()
    agora = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(usuario_id), "iat": agora,
         "exp": agora + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def validar_token(token: str) -> int:
    """Valida assinatura e claims e devolve o id; consulta ao banco é etapa 6."""
    settings = load_security_settings()
    try:
        claims = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
        subject = claims["sub"]
        if not isinstance(subject, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", subject):
            raise TokenInvalidoError()
        usuario_id = int(subject)
        if usuario_id > 9223372036854775807:
            raise TokenInvalidoError()
        if (type(claims["exp"]) is not int or type(claims["iat"]) is not int
                or claims["exp"] <= claims["iat"]):
            raise TokenInvalidoError()
        return usuario_id
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise TokenInvalidoError() from None

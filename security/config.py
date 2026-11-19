"""Parâmetros de segurança; nenhuma chave padrão é fornecida."""

from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import SecretStr


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30


@dataclass(frozen=True)
class SecuritySettings:
    secret_key: SecretStr = field(repr=False)
    algorithm: str = field(default=JWT_ALGORITHM, init=False)
    access_token_expire_minutes: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES


def load_security_settings(env_file: Path = ENV_PATH) -> SecuritySettings:
    """Lê .env local; variáveis do processo têm prioridade, inclusive vazias.

    A leitura é explícita para não alterar o ambiente global nem exigir chave
    ao importar módulos. Os serviços de segurança deverão chamar esta função.
    """
    values = {**dotenv_values(env_file, interpolate=False), **os.environ}
    secret = values.get("JWT_SECRET_KEY") or ""
    if len(secret.encode("utf-8")) < 32 or secret == "SUBSTITUA_POR_UMA_CHAVE_ALEATORIA":
        raise ValueError("Configure JWT_SECRET_KEY com uma chave aleatória de pelo menos 32 bytes.")
    try:
        minutes = int(values.get("ACCESS_TOKEN_EXPIRE_MINUTES", str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)))
    except (TypeError, ValueError):
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser um inteiro positivo.") from None
    if minutes <= 0:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES deve ser um inteiro positivo.")
    return SecuritySettings(secret_key=SecretStr(secret), access_token_expire_minutes=minutes)

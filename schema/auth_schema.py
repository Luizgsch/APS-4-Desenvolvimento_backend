"""Entrada JSON do login e resposta contendo somente o token de acesso."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class LoginCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: EmailStr
    senha: SecretStr = Field(max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def remover_espacos_email(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.lower()


class TokenRead(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"

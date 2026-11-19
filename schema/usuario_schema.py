"""Schemas separados para cadastro e resposta pública de usuário."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nome: str = Field(min_length=1, max_length=120)
    email: EmailStr
    senha: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("nome", "email", mode="before")
    @classmethod
    def remover_espacos_externos(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("A senha não pode conter somente espaços.")
        return value


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: Literal["usuario", "administrador"]

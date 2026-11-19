"""Usuário de acesso, independente da entidade Participante."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('usuario', 'administrador')", name="ck_usuarios_perfil"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(collation="NOCASE"), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    perfil: Mapped[str] = mapped_column(String, nullable=False, default="usuario")

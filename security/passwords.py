"""Hash e verificação delegados à biblioteca pwdlib com Argon2."""

from pwdlib import PasswordHash


_password_hash = PasswordHash.recommended()


def gerar_hash(senha: str) -> str:
    return _password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return _password_hash.verify(senha, senha_hash)

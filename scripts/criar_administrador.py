"""Cria uma conta administrativa pelo terminal local, sem senha em argumentos."""

from getpass import GetPassWarning, getpass
from pathlib import Path
import sys
import warnings

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database
from schema.usuario_schema import UsuarioCreate
from service.erros import EmailDuplicadoError
from service.usuario_service import criar_administrador


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["--help"], ["-h"]):
        print("Uso: python scripts/criar_administrador.py\n"
              "Informe nome, e-mail e senha no terminal. A senha será ocultada e confirmada.\n"
              "Cria uma nova conta; não promove nem altera contas existentes.")
        return 0
    if args:
        print("O comando não aceita dados por argumentos. Use --help.", file=sys.stderr)
        return 2

    try:
        print(f"Banco de destino: {database.DATABASE_PATH}")
        nome = input("Nome do administrador: ")
        email = input("E-mail do administrador: ")
        # Não aceita o fallback de getpass que poderia exibir a senha.
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            senha = getpass("Senha (8 a 128 caracteres): ")
            confirmacao = getpass("Confirme a senha: ")
        if senha != confirmacao:
            print("As senhas não conferem. Nenhuma conta foi criada.", file=sys.stderr)
            return 2
        recebido = UsuarioCreate(nome=nome, email=email, senha=senha)
        database.criar_tabelas()
        with database.SessionLocal() as db:
            usuario = criar_administrador(db, recebido)
        print(f"Administrador criado com sucesso: id={usuario.id}, e-mail={usuario.email}, perfil={usuario.perfil}.")
        return 0
    except ValidationError:
        print("Dados inválidos. Informe nome de 1 a 120 caracteres, e-mail válido e senha de 8 a 128 caracteres, não composta somente por espaços.", file=sys.stderr)
        return 2
    except EmailDuplicadoError:
        print("E-mail já cadastrado. Nenhuma conta foi criada ou promovida.", file=sys.stderr)
        return 1
    except GetPassWarning:
        print("Não foi possível ocultar a senha. Execute em um terminal interativo local.", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Operação cancelada. Nenhuma conta foi criada.", file=sys.stderr)
        return 130
    except SQLAlchemyError:
        print("Não foi possível salvar o administrador. Confira o acesso ao banco e tente novamente.", file=sys.stderr)
        return 1
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

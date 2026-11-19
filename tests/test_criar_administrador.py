"""Procedimento local exercitado somente com bancos e credenciais de teste."""

from contextlib import redirect_stderr, redirect_stdout
from getpass import GetPassWarning
from io import StringIO
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api_support import APITestCase
import database
from model import Usuario
from scripts import criar_administrador as command
from security.passwords import verificar_senha


SENHA_TESTE = "Senha local somente teste 123"


class CriarAdministradorTests(APITestCase):
    def run_command(self, nome="Administrador", email="admin@example.com", passwords=None):
        output, errors = StringIO(), StringIO()
        with patch("builtins.input", side_effect=[nome, email]), \
             patch.object(command, "getpass", side_effect=passwords if passwords is not None else [SENHA_TESTE, SENHA_TESTE]), \
             redirect_stdout(output), redirect_stderr(errors):
            code = command.main([])
        text = output.getvalue() + errors.getvalue()
        self.assertNotIn(SENHA_TESTE, text)
        self.assertNotIn("$argon2", text)
        return code, text

    def users(self):
        with self.factory() as db:
            return [(u.email, u.perfil, u.senha_hash) for u in db.scalars(select(Usuario).order_by(Usuario.id))]

    def test_local_creation_reuses_hash_and_persists_administrator(self):
        code, text = self.run_command(nome="  Administrador  ", email="  ADMIN@EXAMPLE.COM  ")
        self.assertEqual(code, 0)
        self.assertIn("Administrador criado com sucesso", text)
        user, = self.users()
        self.assertEqual(user[:2], ("admin@example.com", "administrador"))
        self.assertTrue(user[2].startswith("$argon2id$"))
        self.assertTrue(verificar_senha(SENHA_TESTE, user[2]))

    def test_mismatched_passwords_do_not_write(self):
        with patch.object(database, "criar_tabelas") as create:
            code, text = self.run_command(passwords=[SENHA_TESTE, "outra senha"])
            create.assert_not_called()
        self.assertEqual(code, 2)
        self.assertIn("não conferem", text)
        self.assertEqual(self.users(), [])

    def test_invalid_data_does_not_write_or_echo_values(self):
        for changes in ({"nome": " "}, {"email": "invalido"},
                        {"passwords": ["curta", "curta"]}, {"passwords": [" " * 8, " " * 8]}):
            with self.subTest(changes=list(changes)), patch.object(database, "criar_tabelas") as create:
                code, text = self.run_command(**changes)
                create.assert_not_called()
                self.assertEqual(code, 2)
                self.assertIn("Dados inválidos", text)
        self.assertEqual(self.users(), [])

    def test_duplicate_does_not_promote_public_account(self):
        response = self.client.post("/usuarios", json={"nome": "Público", "email": "admin@example.com", "senha": SENHA_TESTE})
        self.assertEqual(response.status_code, 201)
        before = self.users()
        code, text = self.run_command(email="ADMIN@EXAMPLE.COM")
        self.assertEqual(code, 1)
        self.assertIn("Nenhuma conta foi criada ou promovida", text)
        self.assertEqual(self.users(), before)
        self.assertEqual(before[0][1], "usuario")

    def test_repeated_admin_creation_does_not_change_existing_hash(self):
        self.assertEqual(self.run_command()[0], 0)
        before = self.users()
        self.assertEqual(self.run_command(passwords=["Outra senha de teste", "Outra senha de teste"])[0], 1)
        self.assertEqual(self.users(), before)

    def test_no_echo_fallback_is_rejected(self):
        code, text = self.run_command(passwords=GetPassWarning("fallback"))
        self.assertEqual(code, 2)
        self.assertIn("terminal interativo", text)
        self.assertEqual(self.users(), [])

    def test_cancellation_does_not_write(self):
        for exception in (EOFError(), KeyboardInterrupt()):
            code, text = self.run_command(passwords=exception)
            self.assertEqual(code, 130)
            self.assertIn("cancelada", text)
        self.assertEqual(self.users(), [])

    def test_database_failure_rolls_back_with_generic_message(self):
        with patch.object(Session, "commit", side_effect=OperationalError("SQL", {"senha": SENHA_TESTE}, Exception("INTERNO"))):
            code, text = self.run_command()
        self.assertEqual(code, 1)
        self.assertIn("Não foi possível salvar", text)
        self.assertNotIn("INTERNO", text)
        self.assertEqual(self.users(), [])

    def test_password_arguments_rejected_without_echo_and_help_runs_outside_project(self):
        output = StringIO()
        with redirect_stderr(output), patch.object(database, "criar_tabelas") as create:
            self.assertEqual(command.main(["--senha", SENHA_TESTE]), 2)
            create.assert_not_called()
        self.assertNotIn(SENHA_TESTE, output.getvalue())
        script = Path(command.__file__).resolve()
        result = subprocess.run([sys.executable, "-X", "utf8", str(script), "--help"],
                                cwd=self.directory.name, capture_output=True, text=True, encoding="utf8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("não promove", result.stdout)

    def test_public_registration_stays_common_and_has_no_admin_endpoint(self):
        self.assertEqual(self.run_command()[0], 0)
        response = self.client.post("/usuarios", json={"nome": "Público", "email": "publico@example.com", "senha": SENHA_TESTE})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["perfil"], "usuario")
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertFalse(any("admin" in path or "perfil" in path for path in paths))

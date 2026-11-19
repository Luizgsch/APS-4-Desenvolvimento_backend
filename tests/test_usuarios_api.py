"""Cadastro seguro com SQLite temporário; nenhum dado real é alterado."""

import json
import subprocess
import sys
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from api_support import APITestCase
from model import Usuario
from schema.usuario_schema import UsuarioCreate
from security.passwords import verificar_senha


CADASTRO = {"nome": "Aluno Exemplo", "email": "aluno@example.com", "senha": "Senha de teste 123"}


class UsuariosAPITests(APITestCase):
    def create(self, **changes):
        response = self.client.post("/usuarios", json=CADASTRO | changes)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(set(response.json()), {"id", "nome", "email", "perfil"})
        self.assertEqual(response.json()["perfil"], "usuario")
        self.assertNotIn(CADASTRO["senha"], response.text)
        return response.json()

    def count(self):
        with self.factory() as db:
            return db.scalar(select(func.count()).select_from(Usuario))

    def test_create_normalizes_identity_and_stores_only_argon2_hash(self):
        result = self.create(nome="  Aluno Exemplo  ", email="  ALUNO@EXAMPLE.COM  ")
        self.assertEqual(result["nome"], "Aluno Exemplo")
        self.assertEqual(result["email"], "aluno@example.com")
        with self.factory() as db:
            user = db.get(Usuario, result["id"])
            self.assertTrue(user.senha_hash.startswith("$argon2id$"))
            self.assertNotEqual(user.senha_hash, CADASTRO["senha"])
            self.assertTrue(verificar_senha(CADASTRO["senha"], user.senha_hash))
            self.assertFalse(verificar_senha("outra senha", user.senha_hash))
            columns = [row[1] for row in db.connection().exec_driver_sql("PRAGMA table_info(usuarios)")]
            self.assertNotIn("senha", columns)
            self.assertNotIn(user.senha_hash, json.dumps(result))

    def test_duplicate_email_is_409_and_session_recovers(self):
        self.create()
        for email in (CADASTRO["email"], "ALUNO@EXAMPLE.COM"):
            response = self.client.post("/usuarios", json=CADASTRO | {"email": email})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json(), {"detail": "Já existe um usuário cadastrado com este e-mail."})
            self.assertNotIn(CADASTRO["senha"], response.text)
        self.assertEqual(self.count(), 1)
        self.create(email="outro@example.com")
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_required_fields_invalid_values_and_password_boundaries(self):
        payloads = [{k: v for k, v in CADASTRO.items() if k != missing} for missing in CADASTRO]
        payloads += [CADASTRO | change for change in (
            {"nome": "  "}, {"nome": "a" * 121}, {"nome": None},
            {"email": "invalido"}, {"email": ""}, {"senha": ""},
            {"senha": "a" * 7}, {"senha": "a" * 129}, {"senha": " " * 8},
            {"senha": 12345678}, {"senha": {"segredo": CADASTRO["senha"]}},
        )]
        for payload in payloads:
            with self.subTest(fields=list(payload)):
                response = self.client.post("/usuarios", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(set(response.json()), {"detail"})
                self.assertNotIn(CADASTRO["senha"], response.text)
                self.assertNotIn("input", response.text)
        self.assertEqual(self.count(), 0)
        self.create(senha="a" * 8)
        self.create(email="limite@example.com", senha="a" * 128)

    def test_extra_fields_cannot_create_administrator_or_leak_hash(self):
        for extra in ({"perfil": "administrador"}, {"perfil": "usuario"},
                      {"id": 1}, {"senha_hash": "$argon2id$VALOR_SECRETO"},
                      {CADASTRO["senha"]: "valor"}):
            response = self.client.post("/usuarios", json=CADASTRO | extra)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(CADASTRO["senha"], response.text)
            self.assertNotIn("$argon2id$VALOR_SECRETO", response.text)
        self.assertEqual(self.count(), 0)
        self.create()

    def test_malformed_json_and_wrong_body_do_not_echo_secrets(self):
        for body in ('{"senha":"' + CADASTRO["senha"] + '",',
                     json.dumps([CADASTRO]), json.dumps(CADASTRO["senha"])):
            response = self.client.post("/usuarios", content=body, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(CADASTRO["senha"], response.text)
        self.assertEqual(self.count(), 0)

    def test_database_enforces_unique_email_and_valid_profile(self):
        self.create()
        for email, profile in (("ALUNO@EXAMPLE.COM", "usuario"), ("outro@example.com", "root")):
            with self.factory() as db:
                db.add(Usuario(nome="Teste", email=email, senha_hash="hash somente teste", perfil=profile))
                with self.assertRaises(IntegrityError):
                    db.commit()
                db.rollback()
        self.assertEqual(self.count(), 1)

    def test_hash_has_random_salt_and_password_spaces_are_preserved(self):
        self.create(senha="  senha com espaços  ")
        self.create(email="outro@example.com", senha="  senha com espaços  ")
        with self.factory() as db:
            hashes = list(db.scalars(select(Usuario.senha_hash)))
        self.assertNotEqual(hashes[0], hashes[1])
        self.assertTrue(verificar_senha("  senha com espaços  ", hashes[0]))
        self.assertFalse(verificar_senha("senha com espaços", hashes[0]))
        self.assertNotIn("  senha com espaços  ", repr(UsuarioCreate(**(CADASTRO | {"senha": "  senha com espaços  "}))))

    def test_persistence_in_fresh_process(self):
        self.create()
        code = (
            "import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); "
            "print(json.dumps(c.execute('SELECT nome,email,perfil FROM usuarios').fetchall())); c.close()"
        )
        result = subprocess.run([sys.executable, "-c", code, str(self.path)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [[CADASTRO["nome"], CADASTRO["email"], "usuario"]])

    def test_storage_failure_rolls_back_without_exposing_parameters(self):
        error = OperationalError("INSERT", {"senha": CADASTRO["senha"]}, Exception("hash interno"))
        with patch.object(Session, "commit", side_effect=error):
            response = self.client.post("/usuarios", json=CADASTRO)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(CADASTRO["senha"], response.text)
        self.assertNotIn("hash interno", response.text)
        self.assertEqual(self.count(), 0)
        self.create()

    def test_unrelated_integrity_failure_is_not_duplicate_email(self):
        with patch.object(Session, "flush", side_effect=IntegrityError("SQL", {}, Exception("SEGREDO"))):
            response = self.client.post("/usuarios", json=CADASTRO)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("SEGREDO", response.text)
        self.assertEqual(self.count(), 0)

    def test_openapi_has_separate_input_and_public_output(self):
        schema = self.client.get("/openapi.json").json()
        request = schema["components"]["schemas"]["UsuarioCreate"]
        response = schema["components"]["schemas"]["UsuarioRead"]
        self.assertFalse(request["additionalProperties"])
        self.assertEqual(request["properties"]["senha"]["format"], "password")
        self.assertTrue(request["properties"]["senha"]["writeOnly"])
        self.assertEqual(set(response["properties"]), {"id", "nome", "email", "perfil"})

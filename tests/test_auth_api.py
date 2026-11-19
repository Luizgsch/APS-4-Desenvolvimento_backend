"""Login com banco e chave temporários; respostas nunca ecoam credenciais."""

import secrets
from unittest.mock import patch

from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api_support import APITestCase
from schema.usuario_schema import UsuarioCreate
from security.config import SecuritySettings
from security.tokens import validar_token
from service.usuario_service import criar_administrador


CADASTRO = {"nome": "Aluno", "email": "aluno@example.com", "senha": "Senha somente teste 123"}


class AuthAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        self.settings = SecuritySettings(SecretStr(secrets.token_urlsafe(48)), access_token_expire_minutes=15)
        self.config_patch = patch("security.tokens.load_security_settings", return_value=self.settings)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.user = self.client.post("/usuarios", json=CADASTRO).json()

    def test_login_returns_signed_expiring_bearer_without_sensitive_data(self):
        response = self.client.post("/auth/login", json={"email": "  ALUNO@EXAMPLE.COM  ", "senha": CADASTRO["senha"]})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(set(body), {"access_token", "token_type"})
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(validar_token(body["access_token"]), self.user["id"])
        self.assertNotIn(CADASTRO["senha"], response.text)
        self.assertNotIn("senha_hash", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unknown_email_wrong_and_empty_password_have_same_401(self):
        results = []
        for email, password in (("ausente@example.com", CADASTRO["senha"]), (CADASTRO["email"], "errada"), (CADASTRO["email"], "")):
            response = self.client.post("/auth/login", json={"email": email, "senha": password})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
            results.append(response.json())
        self.assertEqual(results, [{"detail": "E-mail ou senha inválidos."}] * 3)

    def test_unknown_email_also_checks_hash(self):
        with patch("service.auth_service.verificar_senha", return_value=False) as verify:
            response = self.client.post("/auth/login", json={"email": "ausente@example.com", "senha": "teste"})
        self.assertEqual(response.status_code, 401)
        verify.assert_called_once()

    def test_invalid_body_and_json_do_not_echo_password_or_hash(self):
        for payload in ({"email": CADASTRO["email"]}, {"email": "invalido", "senha": CADASTRO["senha"]},
                        {"email": CADASTRO["email"], "senha": CADASTRO["senha"], "senha_hash": "HASH_SECRETO"},
                        {"email": CADASTRO["email"], "senha": "a" * 129}, [CADASTRO]):
            response = self.client.post("/auth/login", json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(CADASTRO["senha"], response.text)
            self.assertNotIn("HASH_SECRETO", response.text)
            self.assertNotIn("input", response.text)
        response = self.client.post("/auth/login", content='{"senha":"' + CADASTRO["senha"] + '",', headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(CADASTRO["senha"], response.text)

    def test_administrator_uses_same_login_without_profile_claim(self):
        with self.factory() as db:
            admin = criar_administrador(db, UsuarioCreate(**(CADASTRO | {"email": "admin@example.com"})))
        response = self.client.post("/auth/login", json={"email": admin.email, "senha": CADASTRO["senha"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(validar_token(response.json()["access_token"]), admin.id)

    def test_missing_configuration_returns_generic_503_without_token(self):
        with patch("security.tokens.load_security_settings", side_effect=ValueError("CHAVE_INTERNA")):
            response = self.client.post("/auth/login", json={"email": CADASTRO["email"], "senha": CADASTRO["senha"]})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Serviço de autenticação indisponível."})
        self.assertNotIn("CHAVE_INTERNA", response.text)

    def test_database_failure_is_generic_and_session_recovers(self):
        with patch.object(Session, "scalar", side_effect=OperationalError("SQL", {"senha": CADASTRO["senha"]}, Exception("INTERNO"))):
            response = self.client.post("/auth/login", json={"email": CADASTRO["email"], "senha": CADASTRO["senha"]})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(CADASTRO["senha"], response.text)
        self.assertNotIn("INTERNO", response.text)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_openapi_login_is_json_and_me_requires_bearer(self):
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/auth/login"]["post"]
        self.assertIn("application/json", operation["requestBody"]["content"])
        self.assertEqual(schema["paths"]["/auth/me"]["get"]["security"], [{"BearerJWT": []}])

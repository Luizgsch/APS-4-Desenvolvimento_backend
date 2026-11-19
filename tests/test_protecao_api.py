"""Autenticação real, sem overrides, com usuário e chave descartáveis."""

import secrets
import time
from unittest.mock import patch

import jwt
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api_support import APITestCase
from model import Usuario
from security.config import SecuritySettings
from schema.usuario_schema import UsuarioCreate
from service.usuario_service import criar_administrador


PROTECTED = [("post", "/eventos"), ("put", "/eventos/1"), ("delete", "/eventos/1"),
             ("post", "/participantes"), ("put", "/participantes/1"), ("delete", "/participantes/1"),
             ("post", "/eventos/1/inscricoes/1"), ("get", "/relatorios/eventos/ocupacao"),
             ("get", "/relatorios/eventos/categorias"), ("get", "/relatorios/participantes/cursos"),
             ("get", "/auth/me"), ("get", "/participantes"), ("get", "/participantes/1"),
             ("get", "/eventos/1/inscricoes")]
EVENTO = dict(titulo="Workshop", descricao="Teste", data="2026-12-01", horario="19:00", local="Sala", capacidade=2, categoria="Workshop")


class ProtecaoAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        self.key = secrets.token_urlsafe(48)
        config = patch("security.tokens.load_security_settings", return_value=SecuritySettings(SecretStr(self.key)))
        config.start()
        self.addCleanup(config.stop)
        self.password = secrets.token_urlsafe(24)
        self.user = self.client.post("/usuarios", json={"nome": "Atual", "email": "atual@example.com", "senha": self.password}).json()
        login = self.client.post("/auth/login", json={"email": self.user["email"], "senha": self.password})
        self.token = login.json()["access_token"]
        self.headers = {"Authorization": "Bearer " + self.token}

    def assert_unauthorized(self, response):
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json(), {"detail": "Não foi possível validar as credenciais."})
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertNotIn(self.password, response.text)
        self.assertNotIn(self.token, response.text)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_all_required_routes_reject_missing_token(self):
        for method, route in PROTECTED:
            with self.subTest(method=method, route=route):
                self.assert_unauthorized(getattr(self.client, method)(route))

    def test_all_required_routes_reject_invalid_and_expired_token(self):
        now = int(time.time())
        expired = jwt.encode({"sub": str(self.user["id"]), "iat": now-120, "exp": now-1}, self.key, algorithm="HS256")
        for token in ("adulterado", expired):
            for method, route in PROTECTED:
                with self.subTest(route=route, expired=token==expired):
                    self.assert_unauthorized(getattr(self.client, method)(route, headers={"Authorization": "Bearer " + token}))

    def test_me_returns_only_current_identity_and_ignores_client_id(self):
        self.client.post("/usuarios", json={"nome": "Outro", "email": "outro@example.com", "senha": self.password})
        response = self.client.get("/auth/me?usuario_id=2&id=2", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.user)
        self.assertEqual(set(response.json()), {"id", "nome", "email", "perfil"})
        self.assertNotIn(self.password, response.text)
        self.assertNotIn("senha_hash", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_identity_is_read_from_database_on_every_request(self):
        with self.factory() as db:
            user = db.get(Usuario, self.user["id"])
            user.nome = "Atualizado no banco"
            db.commit()
        forged_claims = {"sub": str(self.user["id"]), "iat": int(time.time()), "exp": int(time.time())+60,
                         "nome": "Ignorar", "perfil": "administrador"}
        signed = jwt.encode(forged_claims, self.key, algorithm="HS256")
        response = self.client.get("/auth/me", headers={"Authorization": "Bearer " + signed})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome"], "Atualizado no banco")
        self.assertEqual(response.json()["perfil"], "usuario")

    def test_nonexistent_and_deleted_user_tokens_are_rejected(self):
        now = int(time.time())
        token = jwt.encode({"sub": "999", "iat": now, "exp": now+60}, self.key, algorithm="HS256")
        self.assert_unauthorized(self.client.get("/auth/me", headers={"Authorization": "Bearer " + token}))
        with self.factory() as db:
            db.delete(db.get(Usuario, self.user["id"]))
            db.commit()
        self.assert_unauthorized(self.client.get("/auth/me", headers=self.headers))
        self.assert_unauthorized(self.client.post("/eventos", json=EVENTO, headers=self.headers))

    def test_malformed_scheme_and_query_token_are_not_authentication(self):
        for header in ("Bearer", "Bearer ", "Basic abc", "Bearer a.b.c"):
            self.assert_unauthorized(self.client.get("/auth/me", headers={"Authorization": header}))
        self.assert_unauthorized(self.client.get("/auth/me", params={"access_token": self.token, "usuario_id": self.user["id"]}))

    def test_valid_token_allows_business_operations_and_reports(self):
        with self.factory() as db:
            criar_administrador(db, UsuarioCreate(nome="Admin", email="admin@example.com", senha=self.password))
        login = self.client.post("/auth/login", json={"email": "admin@example.com", "senha": self.password})
        self.headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        response = self.client.post("/eventos", json=EVENTO, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        eid = response.json()["id"]
        person = {"nome": "Participante", "email": "p@example.com", "curso": "Computação"}
        response = self.client.post("/participantes", json=person, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        pid = response.json()["id"]
        self.assertEqual(self.client.put(f"/eventos/{eid}", json=EVENTO, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.put(f"/participantes/{pid}", json=person, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post(f"/eventos/{eid}/inscricoes/{pid}", headers=self.headers).status_code, 201)
        for route in ("/relatorios/eventos/ocupacao", "/relatorios/eventos/categorias", "/relatorios/participantes/cursos"):
            self.assertEqual(self.client.get(route, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete(f"/participantes/{pid}", headers=self.headers).status_code, 204)
        self.assertEqual(self.client.delete(f"/eventos/{eid}", headers=self.headers).status_code, 204)

    def test_openapi_and_public_routes(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(schema["components"]["securitySchemes"]["BearerJWT"]["scheme"], "bearer")
        self.assertEqual(schema["paths"]["/auth/me"]["get"]["security"], [{"BearerJWT": []}])
        for method, route in (("post", "/eventos"), ("post", "/participantes"), ("put", "/eventos/{id}"),
                              ("delete", "/eventos/{id}"), ("put", "/participantes/{id}"),
                              ("delete", "/participantes/{id}"), ("post", "/eventos/{evento_id}/inscricoes/{participante_id}"),
                              ("get", "/relatorios/eventos/ocupacao"), ("get", "/relatorios/eventos/categorias"),
                              ("get", "/relatorios/participantes/cursos")):
            self.assertEqual(schema["paths"][route][method]["security"], [{"BearerJWT": []}])
        for method, route in (("get", "/eventos"), ("post", "/auth/login"), ("post", "/usuarios")):
            self.assertNotIn("security", schema["paths"][route][method])
        self.assertEqual(self.client.get("/eventos").status_code, 200)

    def test_identity_database_error_is_sanitized_and_closes_session(self):
        with patch.object(Session, "get", side_effect=OperationalError("SQL", {}, Exception("HASH_INTERNO"))):
            response = self.client.get("/auth/me", headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("HASH_INTERNO", response.text)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_configuration_error_is_not_invalid_client_credentials(self):
        with patch("security.tokens.load_security_settings", side_effect=ValueError("SEGREDO")):
            response = self.client.get("/auth/me", headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SEGREDO", response.text)

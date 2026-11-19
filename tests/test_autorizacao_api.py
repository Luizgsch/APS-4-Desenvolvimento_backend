"""Matriz de acesso por perfil, com login e banco reais temporários."""

import secrets
import time

import jwt
from sqlalchemy import select

from api_support import AuthenticatedAPITestCase
from model import Usuario
from security import tokens


EVENTO = dict(titulo="Workshop", descricao="Teste", data="2026-12-01", horario="19:00", local="Sala", capacidade=2, categoria="Workshop")
PARTICIPANTE = dict(nome="Participante", email="participante@example.com", curso="Computação")
REPORTS = ("/relatorios/eventos/ocupacao", "/relatorios/eventos/categorias", "/relatorios/participantes/cursos")


class AutorizacaoAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        password = secrets.token_urlsafe(24)
        self.common = self.client.post("/usuarios", json={"nome": "Comum", "email": "comum@example.com", "senha": password}).json()
        login = self.client.post("/auth/login", json={"email": self.common["email"], "senha": password})
        self.common_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        self.eid = self.client.post("/eventos", json=EVENTO).json()["id"]
        self.pid = self.client.post("/participantes", json=PARTICIPANTE).json()["id"]

    def assert_forbidden(self, response):
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json(), {"detail": "Você não possui permissão para executar esta operação."})
        self.assertNotIn("senha_hash", response.text)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_common_cannot_mutate_events_or_participants_and_nothing_changes(self):
        before_event = self.client.get(f"/eventos/{self.eid}").json()
        before_person = self.client.get(f"/participantes/{self.pid}").json()
        for method, route, data in (
            ("post", "/eventos", EVENTO), ("put", f"/eventos/{self.eid}", EVENTO | {"titulo": "Não alterar"}),
            ("delete", f"/eventos/{self.eid}", None), ("post", "/participantes", PARTICIPANTE),
            ("put", f"/participantes/{self.pid}", PARTICIPANTE | {"nome": "Não alterar"}),
            ("delete", f"/participantes/{self.pid}", None),
        ):
            with self.subTest(method=method, route=route):
                kwargs = {"json": data} if data is not None else {}
                self.assert_forbidden(getattr(self.client, method)(route, headers=self.common_headers, **kwargs))
        self.assertEqual(self.client.get(f"/eventos/{self.eid}").json(), before_event)
        self.assertEqual(self.client.get(f"/participantes/{self.pid}").json(), before_person)
        self.assertEqual(len(self.client.get("/eventos").json()), 1)
        self.assertEqual(len(self.client.get("/participantes").json()), 1)

    def test_common_reads_participants_and_registrations_but_not_reports(self):
        for route in ("/eventos", f"/eventos/{self.eid}", "/participantes", f"/participantes/{self.pid}", f"/eventos/{self.eid}/inscricoes", "/auth/me"):
            self.assertEqual(self.client.get(route, headers=self.common_headers).status_code, 200)
        for route in REPORTS:
            self.assert_forbidden(self.client.get(route, headers=self.common_headers))

    def test_anonymous_reads_events_but_not_participant_data(self):
        for route in ("/eventos", f"/eventos/{self.eid}"):
            self.assertEqual(self.client.get(route, headers={"Authorization": ""}).status_code, 200)
        for route in ("/participantes", f"/participantes/{self.pid}", f"/eventos/{self.eid}/inscricoes", *REPORTS):
            response = self.client.get(route, headers={"Authorization": ""})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_common_can_register_independent_participants_with_business_rules(self):
        self.assertEqual(self.client.put(f"/eventos/{self.eid}", json=EVENTO | {"capacidade": 1}).status_code, 200)
        other = self.client.post("/participantes", json=PARTICIPANTE | {"email": "outro@example.com"}).json()["id"]
        route = f"/eventos/{self.eid}/inscricoes/{self.pid}"
        self.assertEqual(self.client.post(route, headers=self.common_headers).status_code, 201)
        self.assertEqual(self.client.post(route, headers=self.common_headers).status_code, 409)
        self.assertEqual(self.client.post(f"/eventos/{self.eid}/inscricoes/{other}", headers=self.common_headers).status_code, 409)
        self.assertEqual(self.client.post(f"/eventos/{self.eid}/inscricoes/999", headers=self.common_headers).status_code, 404)
        self.assertEqual(self.client.post(f"/eventos/999/inscricoes/{self.pid}", headers=self.common_headers).status_code, 404)
        self.assertEqual(len(self.client.get(f"/eventos/{self.eid}/inscricoes", headers=self.common_headers).json()), 1)

    def test_admin_executes_mutations_reads_and_reports(self):
        self.assertEqual(self.client.put(f"/eventos/{self.eid}", json=EVENTO | {"titulo": "Atualizado"}).status_code, 200)
        self.assertEqual(self.client.put(f"/participantes/{self.pid}", json=PARTICIPANTE | {"nome": "Atualizado"}).status_code, 200)
        self.assertEqual(self.client.post(f"/eventos/{self.eid}/inscricoes/{self.pid}").status_code, 201)
        for route in REPORTS:
            self.assertEqual(self.client.get(route).status_code, 200)
        self.assertEqual(self.client.delete(f"/participantes/{self.pid}").status_code, 204)
        self.assertEqual(self.client.delete(f"/eventos/{self.eid}").status_code, 204)

    def test_forged_profile_in_signed_token_body_headers_or_query_does_not_grant_access(self):
        now = int(time.time())
        signed = jwt.encode({"sub": str(self.common["id"]), "iat": now, "exp": now+60, "perfil": "administrador"},
                            tokens.load_security_settings().secret_key.get_secret_value(), algorithm="HS256")
        headers = {"Authorization": "Bearer " + signed, "X-Perfil": "administrador", "X-User-Id": "1"}
        self.assert_forbidden(self.client.post("/eventos?perfil=administrador&usuario_id=1", json=EVENTO | {"perfil": "administrador"}, headers=headers))
        response = self.client.get("/auth/me", headers=headers)
        self.assertEqual(response.json()["perfil"], "usuario")

    def test_database_profile_change_takes_effect_without_new_login(self):
        with self.factory() as db:
            admin = db.scalar(select(Usuario).where(Usuario.email == "regressao@example.com"))
            admin.perfil = "usuario"
            db.commit()
        self.assert_forbidden(self.client.post("/eventos", json=EVENTO))
        self.assertEqual(self.client.get("/auth/me").json()["perfil"], "usuario")
        with self.factory() as db:
            admin = db.scalar(select(Usuario).where(Usuario.email == "regressao@example.com"))
            admin.perfil = "administrador"
            db.commit()
        self.assertEqual(self.client.post("/eventos", json=EVENTO).status_code, 201)

    def test_openapi_protects_new_read_routes_and_no_promotion_endpoint_exists(self):
        schema = self.client.get("/openapi.json").json()
        for route in ("/participantes", "/participantes/{id}", "/eventos/{evento_id}/inscricoes"):
            self.assertEqual(schema["paths"][route]["get"]["security"], [{"BearerJWT": []}])
        self.assertFalse(any("admin" in path or "perfil" in path for path in schema["paths"]))

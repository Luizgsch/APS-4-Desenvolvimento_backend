from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import database
import main
import secrets
from pydantic import SecretStr
from security.config import SecuritySettings
from schema.usuario_schema import UsuarioCreate
from service.usuario_service import criar_administrador


class APITestCase(unittest.TestCase):
    """Isola o banco sem alterar dados reais."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "test.db"
        self.engine = create_engine(
            database.URL.create("sqlite+pysqlite", database=str(self.path)),
            connect_args={"check_same_thread": False, "autocommit": False},
        )
        event.listen(self.engine, "connect", database.habilitar_chaves_estrangeiras)
        self.factory = sessionmaker(bind=self.engine, autoflush=False)
        self.patches = [patch.object(database, "engine", self.engine),
                        patch.object(database, "SessionLocal", self.factory),
                        patch.object(main, "engine", self.engine)]
        for item in self.patches:
            item.start()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.engine.dispose()
        self.directory.cleanup()


class AuthenticatedAPITestCase(APITestCase):
    """Regressão de negócio com login real, sem substituir autenticação."""

    def setUp(self):
        super().setUp()
        config = patch("security.tokens.load_security_settings", return_value=SecuritySettings(SecretStr(secrets.token_urlsafe(48))))
        config.start()
        self.addCleanup(config.stop)
        password = secrets.token_urlsafe(24)
        with self.factory() as db:
            criar_administrador(db, UsuarioCreate(nome="Regressão", email="regressao@example.com", senha=password))
        login = self.client.post("/auth/login", json={"email": "regressao@example.com", "senha": password})
        self.assertEqual(login.status_code, 200)
        self.auth_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        self.client.headers.update(self.auth_headers)

    def new_client(self):
        return TestClient(main.app, headers=self.auth_headers)

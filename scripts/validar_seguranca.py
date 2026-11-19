"""Demonstra os 12 cenários da APS 4 por HTTP, sem usar bancos reais."""

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jwt
from scripts.validar_cenarios import Demonstracao, EVENTO, REPORTS
from security.passwords import verificar_senha

OUTPUT = ROOT / "docs/evidencias/aps4-etapa8"


def ocultar(value):
    if isinstance(value, dict):
        return {k: ("OMITIDO" if k in {"senha", "senha_hash", "access_token"} else ocultar(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [ocultar(v) for v in value]
    return value


class Seguranca:
    def __init__(self, directory, key):
        self.demo = Demonstracao(directory)
        self.key = key
        self.password = secrets.token_urlsafe(24)
        self.sensitive = [self.password, key]
        self.result = {"inicio_utc": datetime.now(timezone.utc).isoformat(),
                       "metodo": "HTTP real com Uvicorn; demonstração visual do Swagger registrada separadamente",
                       "banco_temporario": True, "cenarios": []}

    @contextmanager
    def case(self, number, name):
        self.current = {"numero": number, "cenario": name, "requisicoes": [], "resultado": "em execução"}
        self.result["cenarios"].append(self.current)
        try:
            yield
        except Exception:
            self.current["resultado"] = "falhou"
            raise
        else:
            self.current["resultado"] = "aprovado"

    def request(self, method, route, expected, data=None, token=None, raw=None):
        if isinstance(data, dict) and isinstance(data.get("senha"), str) and data["senha"]:
            self.sensitive.append(data["senha"])
        if isinstance(data, dict) and isinstance(data.get("senha_hash"), str) and data["senha_hash"]:
            self.sensitive.append(data["senha_hash"])
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(self.demo.base + route, method=method, headers=headers,
            data=raw if raw is not None else (None if data is None else json.dumps(data).encode()))
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read().decode()
            body = json.loads(content) if content else None
            status = response.status
            challenge = response.headers.get("WWW-Authenticate")
        assert status == expected, f"{method} {route}: esperado {expected}, recebido {status}"
        assert all(secret not in content for secret in self.sensitive), "Resposta expôs um valor sensível"
        if expected == 401:
            assert challenge == "Bearer"
        self.current["requisicoes"].append({"metodo": method, "rota": route,
            "json_enviado": "JSON malformado; conteúdo omitido" if raw is not None else ocultar(data),
            "autenticacao": "Bearer de teste; valor omitido" if token else "ausente",
            "status_esperado": expected, "status_observado": status, "json_recebido": ocultar(body)})
        return body

    def run(self):
        with self.demo.server():
            with self.case(1, "Cadastro público de usuário e validação sem exposição"):
                self.user = self.request("POST", "/usuarios", 201,
                    dict(nome="Aluno APS 4", email="aluno@example.com", senha=self.password))
                assert set(self.user) == {"id", "nome", "email", "perfil"} and self.user["perfil"] == "usuario"
                for extra in ({"perfil": "administrador"}, {"senha_hash": "HASH_TESTE_OMITIDO"}):
                    self.request("POST", "/usuarios", 422,
                        dict(nome="Tentativa", email="extra@example.com", senha=self.password) | extra)
                self.request("POST", "/usuarios", 422, dict(nome="", email="invalido", senha=self.password))
                self.request("POST", "/auth/login", 422, raw=('{"senha":"' + self.password + '",').encode())
            with self.case(2, "Senha persistida somente como hash Argon2id"):
                with closing(sqlite3.connect(self.demo.path)) as db:
                    stored, profile = db.execute("SELECT senha_hash,perfil FROM usuarios WHERE id=?", (self.user["id"],)).fetchone()
                    columns = [r[1] for r in db.execute("PRAGMA table_info(usuarios)")]
                assert stored.startswith("$argon2id$") and stored != self.password
                assert verificar_senha(self.password, stored) and not verificar_senha("incorreta", stored)
                assert "senha" not in columns and profile == "usuario"
                self.sensitive.append(stored)
                self.current["verificacao_banco"] = {"algoritmo": "Argon2id", "senha_original_persistida": False,
                    "verificacao_correta": True, "verificacao_incorreta_rejeitada": True, "hash": "OMITIDO"}
            with self.case(3, "E-mail duplicado"):
                self.request("POST", "/usuarios", 409, dict(nome="Duplicado", email="ALUNO@EXAMPLE.COM", senha=self.password))
            with self.case(4, "Login válido"):
                login = self.request("POST", "/auth/login", 200, dict(email=self.user["email"], senha=self.password))
                self.token = login["access_token"]
                assert login["token_type"] == "bearer"
            with self.case(5, "Login inválido com mensagem indistinguível"):
                wrong = self.request("POST", "/auth/login", 401, dict(email=self.user["email"], senha="incorreta"))
                unknown = self.request("POST", "/auth/login", 401, dict(email="ausente@example.com", senha="incorreta"))
                assert wrong == unknown
            with self.case(6, "Rota protegida sem token"):
                self.request("GET", "/auth/me", 401)
                self.request("POST", "/eventos", 401, EVENTO)
            with self.case(7, "Rota protegida com token válido"):
                assert self.request("GET", "/auth/me", 200, token=self.token) == self.user
                self.request("GET", "/participantes", 200, token=self.token)
            with self.case(8, "Token inválido, adulterado e expirado"):
                now = int(time.time())
                claims = {"sub": str(self.user["id"]), "iat": now, "exp": now+60}
                invalid = ["a.b.c", jwt.encode(claims, secrets.token_urlsafe(48), algorithm="HS256"),
                    jwt.encode(claims | {"iat": now-120, "exp": now-1}, self.key, algorithm="HS256"),
                    jwt.encode(claims, "", algorithm="none"), jwt.encode(claims, self.key, algorithm="HS384"),
                    jwt.encode(claims | {"sub": "999"}, self.key, algorithm="HS256")]
                for token in invalid:
                    self.request("GET", "/auth/me", 401, token=token)
            with self.case(9, "Usuário comum tentando operação administrativa"):
                self.request("POST", "/eventos", 403, EVENTO, self.token)
                self.request("GET", REPORTS[0], 403, token=self.token)
            with self.case(10, "Administrador executando operação administrativa"):
                self.event = self.request("POST", "/eventos", 201, EVENTO, self.demo.token)
                self.person = self.request("POST", "/participantes", 201,
                    dict(nome="Participante", email="p@example.com", curso="Computacao"), self.demo.token)
                self.request("POST", f"/eventos/{self.event['id']}/inscricoes/{self.person['id']}", 201, token=self.token)
            with self.case(11, "Consulta da identidade do token sem confiar no cliente"):
                assert self.request("GET", "/auth/me?usuario_id=1&id=1", 200, token=self.token) == self.user
                assert self.user["id"] != 1
        with self.case(12, "Continuidade da APS 3, relatórios e persistência após reiniciar"):
            with self.demo.server():
                assert self.request("GET", "/auth/me", 200, token=self.token) == self.user
                assert self.request("GET", f"/eventos/{self.event['id']}", 200) == self.event
                occupation = self.request("GET", REPORTS[0], 200, token=self.demo.token)
                assert occupation[0]["total_inscritos"] == 1
                assert self.request("GET", REPORTS[1], 200, token=self.demo.token)[0]["total_inscricoes"] == 1
                assert self.request("GET", REPORTS[2], 200, token=self.demo.token)[0]["total_inscricoes"] == 1
                self.request("POST", f"/eventos/{self.event['id']}/inscricoes/{self.person['id']}", 409, token=self.token)
                self.request("PUT", f"/eventos/{self.event['id']}", 200, EVENTO | {"capacidade": 1}, self.demo.token)
                other = self.request("POST", "/participantes", 201,
                    dict(nome="Outro", email="outro@example.com", curso="Direito"), self.demo.token)
                self.request("POST", f"/eventos/{self.event['id']}/inscricoes/{other['id']}", 409, token=self.token)
                self.request("PUT", f"/participantes/{self.person['id']}", 200,
                    dict(nome="Atualizado", email="p@example.com", curso="Direito"), self.demo.token)
                assert self.request("GET", REPORTS[2], 200, token=self.demo.token)[0]["curso"] == "Direito"
                self.request("DELETE", f"/participantes/{self.person['id']}", 204, token=self.demo.token)
                assert self.request("GET", REPORTS[0], 200, token=self.demo.token)[0]["total_inscritos"] == 0
                self.request("DELETE", f"/eventos/{self.event['id']}", 204, token=self.demo.token)
                assert self.request("GET", REPORTS[0], 200, token=self.demo.token) == []
                assert self.request("GET", REPORTS[1], 200, token=self.demo.token) == []
                with closing(sqlite3.connect(self.demo.path)) as db:
                    assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
                    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
                self.current["reinicializacao_e_integridade"] = "aprovadas"


def main():
    before = hashlib.sha256((ROOT / "eventos.db").read_bytes()).hexdigest() if (ROOT / "eventos.db").exists() else None
    key = secrets.token_urlsafe(48)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aps4-seguranca-") as directory, patch.dict(os.environ, {"JWT_SECRET_KEY": key}):
        demo = Seguranca(directory, key)
        try:
            demo.run()
            after = hashlib.sha256((ROOT / "eventos.db").read_bytes()).hexdigest() if (ROOT / "eventos.db").exists() else None
            assert before == after
            demo.result.update(resultado="aprovado", banco_real_preservado=True)
        finally:
            demo.result["fim_utc"] = datetime.now(timezone.utc).isoformat()
            (OUTPUT / "cenarios-seguranca.json").write_text(json.dumps(demo.result, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print("12 cenários de segurança aprovados. Evidências: docs/evidencias/aps4-etapa8/cenarios-seguranca.json")


if __name__ == "__main__":
    main()

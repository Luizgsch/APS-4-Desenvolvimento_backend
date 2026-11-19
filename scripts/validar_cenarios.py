"""Demonstra os 12 cenários por HTTP real, usando somente banco temporário."""

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import secrets
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "evidencias" / "aps4-regressao.json"
EVENTO = dict(titulo="Workshop", descricao="Demonstração APS 3", data="2026-12-01",
              horario="19:00", local="Sala 1", capacidade=2, categoria="Workshop")
REPORTS = ("/relatorios/eventos/ocupacao", "/relatorios/eventos/categorias", "/relatorios/participantes/cursos")


def serve(path, port):
    import database
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    import uvicorn

    database.engine = create_engine(
        database.URL.create("sqlite+pysqlite", database=str(path)),
        connect_args={"check_same_thread": False, "autocommit": False},
    )
    event.listen(database.engine, "connect", database.habilitar_chaves_estrangeiras)
    database.SessionLocal = sessionmaker(bind=database.engine, autoflush=False)
    from main import app
    uvicorn.run(app, host="127.0.0.1", port=port)


class Demonstracao:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "demonstracao.db"
        self.token = None
        self.password = secrets.token_urlsafe(24)
        self.result = {"inicio_utc": datetime.now(timezone.utc).isoformat(),
                       "metodo": "HTTP real com Uvicorn; não executado pela interface Swagger",
                       "banco_temporario": True, "processos": [], "cenarios": []}

    @contextmanager
    def server(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        log_path = self.directory / f"server-{len(self.result['processos'])}.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve", str(self.path), str(port)],
                cwd=ROOT, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            self.result["processos"].append(process.pid)
            try:
                deadline = time.monotonic() + 20
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(log_path.read_text(encoding="utf-8"))
                    try:
                        urllib.request.urlopen(self.base + "/", timeout=1).close()
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise RuntimeError("Tempo de inicialização excedido")
                        time.sleep(0.1)
                self.authenticate()
                yield
            finally:
                if process.poll() is None:
                    if os.name == "nt":
                        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)

    def authenticate(self):
        """Administrador descartável pelo serviço local; não há promoção HTTP."""
        def send(route, data):
            req = urllib.request.Request(self.base + route, method="POST",
                data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())
        if self.token is None:
            from sqlalchemy import URL, create_engine
            from sqlalchemy.orm import Session
            from schema.usuario_schema import UsuarioCreate
            from service.usuario_service import criar_administrador
            engine = create_engine(URL.create("sqlite+pysqlite", database=str(self.path)),
                                   connect_args={"autocommit": False})
            try:
                with Session(engine) as db:
                    criar_administrador(db, UsuarioCreate(nome="Regressao", email="regressao@example.com", senha=self.password))
            finally:
                engine.dispose()
        self.token = send("/auth/login", dict(email="regressao@example.com", senha=self.password))["access_token"]
        self.result["regressao_autenticada"] = True

    @contextmanager
    def case(self, number, name):
        self.current = {"numero": number, "cenario": name, "resultado": "em execução", "requisicoes": []}
        self.result["cenarios"].append(self.current)
        try:
            yield
        except Exception as exc:
            self.current.update(resultado="falhou", erro=str(exc))
            raise
        else:
            self.current["resultado"] = "aprovado"

    def request(self, method, route, expected, data=None):
        req = urllib.request.Request(self.base + route, method=method,
                                     data=None if data is None else json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.token})
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            content = response.read().decode("utf-8")
            body = json.loads(content) if content and "json" in response.headers.get("Content-Type", "") else None
            self.current["requisicoes"].append({"metodo": method, "rota": route, "json_enviado": data,
                                               "status_esperado": expected, "status_observado": response.status,
                                               "json_recebido": body})
            if response.status != expected:
                raise AssertionError(f"{method} {route}: esperado {expected}, recebido {response.status}: {content}")
            return body

    def reports(self):
        return [self.request("GET", route, 200) for route in REPORTS]

    def run(self):
        with self.server():
            with self.case(1, "Cadastro e consulta de eventos"):
                self.eid = self.request("POST", "/eventos", 201, EVENTO)["id"]
                self.empty = self.request("POST", "/eventos", 201, EVENTO)["id"]
                assert len(self.request("GET", "/eventos", 200)) == 2
                assert self.request("GET", f"/eventos/{self.eid}", 200)["capacidade"] == 2
            with self.case(2, "Cadastro e consulta de participantes"):
                self.people = []
                for n in range(1, 4):
                    p = self.request("POST", "/participantes", 201, dict(nome=f"Teste {n}", email=f"teste{n}@example.com", curso="Computacao" if n < 3 else "Direito"))
                    self.people.append(p)
                    assert self.request("GET", f"/participantes/{p['id']}", 200) == p
                assert len(self.request("GET", "/participantes", 200)) == 3
            with self.case(3, "Atualização e exclusão de registros"):
                e = self.request("POST", "/eventos", 201, EVENTO)["id"]
                self.request("PUT", f"/eventos/{e}", 200, EVENTO | {"titulo": "Atualizado"})
                assert self.request("GET", f"/eventos/{e}", 200)["titulo"] == "Atualizado"
                self.request("DELETE", f"/eventos/{e}", 204)
                self.request("GET", f"/eventos/{e}", 404)
                p = self.request("POST", "/participantes", 201, dict(nome="Temporário", email="temporario@example.com", curso="Outro"))
                self.request("PUT", f"/participantes/{p['id']}", 200, dict(nome="Atualizado", email=p["email"], curso="Outro"))
                self.request("DELETE", f"/participantes/{p['id']}", 204)
                self.request("GET", f"/participantes/{p['id']}", 404)
            with self.case(4, "Inscrição de participante"):
                self.registration = self.request("POST", f"/eventos/{self.eid}/inscricoes/{self.people[0]['id']}", 201)
                assert self.registration["id"] > 0 and self.registration["data_inscricao"]
                assert self.request("GET", f"/eventos/{self.eid}/inscricoes", 200) == self.people[:1]
            with self.case(5, "Inscrição duplicada"):
                assert self.request("POST", f"/eventos/{self.eid}/inscricoes/{self.people[0]['id']}", 409) == {"detail": "Participante já está inscrito neste evento."}
            with self.case(6, "Inscrição em evento inexistente"):
                self.request("POST", f"/eventos/99999/inscricoes/{self.people[0]['id']}", 404)
                self.request("POST", f"/eventos/{self.eid}/inscricoes/99999", 404)
            with self.case(7, "Inscrição sem vagas"):
                self.request("POST", f"/eventos/{self.eid}/inscricoes/{self.people[1]['id']}", 201)
                assert self.request("POST", f"/eventos/{self.eid}/inscricoes/{self.people[2]['id']}", 409) == {"detail": "Não existem vagas disponíveis para este evento."}
                self.before = self.request("GET", f"/eventos/{self.eid}/inscricoes", 200)
        with self.server():
            with self.case(8, "Persistência após reiniciar o processo da API"):
                assert self.result["processos"][0] != self.result["processos"][1]
                assert self.request("GET", f"/eventos/{self.eid}/inscricoes", 200) == self.before
                assert self.request("GET", f"/eventos/{self.eid}", 200)["capacidade"] == 2
                assert len(self.request("GET", "/participantes", 200)) == 3
                self.request("POST", f"/eventos/{self.eid}/inscricoes/{self.people[0]['id']}", 409)
                with closing(sqlite3.connect(self.path)) as connection:
                    row = connection.execute("SELECT id, data_inscricao FROM inscricoes WHERE id = ?", (self.registration["id"],)).fetchone()
                assert row == (self.registration["id"], self.registration["data_inscricao"])
                self.current["inscricao_verificada_no_arquivo"] = list(row)
            with self.case(9, "Relatório de ocupação"):
                assert self.request("GET", REPORTS[0], 200) == [
                    dict(evento_id=self.eid, titulo="Workshop", capacidade=2, total_inscritos=2, vagas_disponiveis=0, percentual_ocupacao=100.0),
                    dict(evento_id=self.empty, titulo="Workshop", capacidade=2, total_inscritos=0, vagas_disponiveis=2, percentual_ocupacao=0.0)]
            with self.case(10, "Relatório por categoria"):
                assert self.request("GET", REPORTS[1], 200) == [dict(categoria="Workshop", total_eventos=2, capacidade_total=4, total_inscricoes=2)]
            with self.case(11, "Relatório por curso"):
                assert self.request("GET", REPORTS[2], 200) == [
                    dict(curso="Computacao", total_participantes=2, total_inscricoes=2),
                    dict(curso="Direito", total_participantes=1, total_inscricoes=0)]
            with self.case(12, "Relatórios após inserir, atualizar e excluir"):
                self.request("POST", f"/eventos/{self.empty}/inscricoes/{self.people[0]['id']}", 201)
                reports = self.reports()
                assert reports[1][0]["total_inscricoes"] == 3
                assert reports[2][0] == dict(curso="Computacao", total_participantes=2, total_inscricoes=3)
                self.request("PUT", f"/eventos/{self.eid}", 200, EVENTO | {"capacidade": 4, "categoria": "Palestra"})
                self.request("PUT", f"/participantes/{self.people[0]['id']}", 200, self.people[0] | {"curso": "Direito"})
                reports = self.reports()
                assert reports[0][0]["percentual_ocupacao"] == 50.0
                assert reports[1] == [dict(categoria="Palestra", total_eventos=1, capacidade_total=4, total_inscricoes=2), dict(categoria="Workshop", total_eventos=1, capacidade_total=2, total_inscricoes=1)]
                assert reports[2] == [dict(curso="Computacao", total_participantes=1, total_inscricoes=1), dict(curso="Direito", total_participantes=2, total_inscricoes=2)]
                self.request("DELETE", f"/participantes/{self.people[0]['id']}", 204)
                reports = self.reports()
                assert reports[0][0]["total_inscritos"] == 1 and reports[0][1]["total_inscritos"] == 0
                assert reports[1][0]["total_inscricoes"] == 1 and reports[1][1]["total_inscricoes"] == 0
                assert reports[2][1]["total_inscricoes"] == 0
                self.request("DELETE", f"/eventos/{self.eid}", 204)
                self.request("DELETE", f"/eventos/{self.empty}", 204)
                reports = self.reports()
                assert reports[:2] == [[], []]
                assert all(row["total_inscricoes"] == 0 for row in reports[2])
                with closing(sqlite3.connect(self.path)) as connection:
                    integrity = connection.execute("PRAGMA integrity_check").fetchall()
                    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
                    inscriptions = connection.execute("SELECT count(*) FROM inscricoes").fetchone()[0]
                assert integrity == [("ok",)] and foreign_keys == [] and inscriptions == 0
                self.result["integridade_banco_temporario"] = {"integrity_check": integrity, "foreign_key_check": foreign_keys, "inscricoes_apos_cascatas": inscriptions}
                self.request("GET", "/docs", 200)
                self.request("GET", "/openapi.json", 200)


def main():
    real_db = ROOT / "eventos.db"
    def fingerprint():
        return hashlib.sha256(real_db.read_bytes()).hexdigest() if real_db.exists() else None
    before = fingerprint()
    with tempfile.TemporaryDirectory(prefix="aps4-cenarios-") as directory, patch.dict(os.environ, {"JWT_SECRET_KEY": secrets.token_urlsafe(48)}):
        demo = Demonstracao(directory)
        try:
            demo.run()
            assert fingerprint() == before, "O banco real foi modificado durante a validação"
            demo.result.update(resultado="aprovado", banco_real_preservado=True)
        finally:
            demo.result["fim_utc"] = datetime.now(timezone.utc).isoformat()
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(json.dumps(demo.result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"12 cenários aprovados. Evidências: {OUTPUT}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--serve":
        serve(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main()

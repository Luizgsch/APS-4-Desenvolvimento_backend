import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import database
import main
from api_support import AuthenticatedAPITestCase as APITestCase
from model import Evento, Inscricao, Participante


EVENTO = dict(titulo="Workshop", descricao="Teste", data="2026-12-01", horario="19:00",
              local="Sala 1", capacidade=3, categoria="Workshop")


class EventosAPITests(APITestCase):
    def create(self, **changes):
        response = self.client.post("/eventos", json=EVENTO | changes)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_crud_and_empty_list(self):
        self.assertEqual(self.client.get("/eventos").json(), [])
        created = self.create()
        eid = created['id']
        self.assertEqual(self.client.get(f"/eventos/{eid}").json(), created)
        response = self.client.put(f"/eventos/{eid}", json=EVENTO | {"titulo": "Atualizado"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['titulo'], "Atualizado")
        self.assertEqual(self.client.get('/eventos').json(), [response.json()])
        response = self.client.delete(f"/eventos/{eid}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get('/eventos').json(), [])

    def test_data_survives_application_restart_and_separate_python_process(self):
        created = self.create()
        eid = created['id']
        response = self.client.put(f'/eventos/{eid}', json=EVENTO | {"titulo": "Persistido"})
        self.assertEqual(response.status_code, 200)
        self.client.__exit__(None, None, None)
        code = (
            "import json,sys; from sqlalchemy import create_engine,URL,select; "
            "from sqlalchemy.orm import Session; from model import Evento; "
            "e=create_engine(URL.create('sqlite+pysqlite',database=sys.argv[1])); "
            "s=Session(e); print(json.dumps([x.titulo for x in s.scalars(select(Evento))])); "
            "s.close(); e.dispose()"
        )
        result = subprocess.run([sys.executable, '-c', code, str(self.path)],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), ['Persistido'])
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual(self.client.get(f'/eventos/{eid}').json()['titulo'], 'Persistido')
        self.assertEqual(self.client.delete(f'/eventos/{eid}').status_code, 204)
        self.client.__exit__(None, None, None)
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual(self.client.get(f'/eventos/{eid}').status_code, 404)

    def test_missing_events_and_invalid_ids(self):
        for method in ('get', 'put', 'delete'):
            kwargs = {'json': EVENTO} if method == 'put' else {}
            response = getattr(self.client, method)('/eventos/999', **kwargs)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {'detail': 'Evento não encontrado.'})
        self.assertEqual(self.client.get('/eventos/invalido').status_code, 422)

    def test_invalid_creation_and_update_do_not_change_database(self):
        created = self.create()
        for invalid in ({'titulo': '  '}, {'capacidade': 0}, {'data': '2026-02-30'}, {'horario': '25:00'}):
            self.assertEqual(self.client.post('/eventos', json=EVENTO | invalid).status_code, 422)
            self.assertEqual(self.client.put(f"/eventos/{created['id']}", json=EVENTO | invalid).status_code, 422)
        self.assertEqual(self.client.put(f"/eventos/{created['id']}", json={'titulo': 'Incompleto'}).status_code, 422)
        self.assertEqual(self.client.get('/eventos').json(), [created])

    def test_trailing_slash_and_documentation(self):
        self.assertEqual(self.client.post('/eventos/', json=EVENTO).status_code, 201)
        self.assertEqual(self.client.get('/docs').status_code, 200)
        schema = self.client.get('/openapi.json').json()
        self.assertIn('201', schema['paths']['/eventos']['post']['responses'])
        self.assertIn('204', schema['paths']['/eventos/{id}']['delete']['responses'])

    def test_api_registrations_and_capacity_are_protected(self):
        eid = self.create()['id']
        for n in (1, 2):
            p = self.client.post('/participantes', json=dict(nome=f'Teste {n}', email=f'teste{n}@example.com', curso='Computacao')).json()
            self.assertEqual(self.client.post(f"/eventos/{eid}/inscricoes/{p['id']}").status_code, 201)
        self.assertEqual(len(self.client.get(f'/eventos/{eid}/inscricoes').json()), 2)
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO | {'capacidade': 1}).status_code, 409)
        self.assertEqual(self.client.get(f'/eventos/{eid}').json()['capacidade'], 3)
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO | {'capacidade': 2}).status_code, 200)
        self.assertEqual(self.client.delete(f'/eventos/{eid}').status_code, 204)
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(Inscricao))), [])
            self.assertEqual(len(list(db.scalars(select(Participante)))), 2)
        self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').status_code, 404)

    def test_persistent_registration_capacity_and_cascade(self):
        eid = self.create()['id']
        with self.factory() as db:
            for n in (1, 2):
                db.add(Inscricao(evento_id=eid, participante=Participante(nome='Teste', email=f'orm{n}@example.com', curso='Computacao')))
            db.commit()
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO | {'capacidade': 1}).status_code, 409)
        self.assertEqual(self.client.delete(f'/eventos/{eid}').status_code, 204)
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(Inscricao))), [])
            self.assertEqual(len(list(db.scalars(select(Participante)))), 2)

    def test_commit_failures_rollback_create_update_and_delete(self):
        created = self.create()
        eid = created['id']
        p = self.client.post('/participantes', json=dict(nome='Teste', email='rollback@example.com', curso='Computacao')).json()
        self.assertEqual(self.client.post(f"/eventos/{eid}/inscricoes/{p['id']}").status_code, 201)
        failure = OperationalError('SQL INTERNO', {}, Exception('CAMINHO INTERNO'))
        for method, url, kwargs in (
            ('post', '/eventos', {'json': EVENTO}),
            ('put', f'/eventos/{eid}', {'json': EVENTO | {'titulo': 'Nao deve gravar'}}),
            ('delete', f'/eventos/{eid}', {}),
        ):
            with self.subTest(method=method), patch.object(Session, 'commit', side_effect=failure):
                response = getattr(self.client, method)(url, **kwargs)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {'detail': 'Não foi possível acessar os dados. Tente novamente.'})
            self.assertEqual(self.client.get('/eventos').json(), [created])
            self.assertEqual(len(self.client.get(f'/eventos/{eid}/inscricoes').json()), 1)
            self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_read_failure_is_sanitized_and_next_request_succeeds(self):
        with patch.object(Session, 'scalars', side_effect=OperationalError('SQL INTERNO', {}, Exception('SEGREDO'))):
            response = self.client.get('/eventos')
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('SEGREDO', response.text)
            self.assertNotIn('SQL INTERNO', response.text)
        self.assertEqual(self.client.get('/eventos').json(), [])
        self.assertEqual(self.engine.pool.checkedout(), 0)


if __name__ == '__main__':
    unittest.main()

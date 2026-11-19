import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from api_support import AuthenticatedAPITestCase as APITestCase
import main
from model import Evento, Inscricao, Participante
from schema.evento_schema import EventoCreate


PARTICIPANTE = dict(nome='Teste', email='teste@example.com', curso='Computacao')
EVENTO = dict(titulo='Workshop', descricao='Teste', data='2026-12-01', horario='19:00',
              local='Sala', capacidade=3, categoria='Workshop')


class ParticipantesAPITests(APITestCase):
    def create(self, **changes):
        response = self.client.post('/participantes', json=PARTICIPANTE | changes)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(set(response.json()), {'id', 'nome', 'email', 'curso'})
        return response.json()

    def test_crud_and_empty_list(self):
        self.assertEqual(self.client.get('/participantes').json(), [])
        participant = self.create()
        pid = participant['id']
        self.assertEqual(self.client.get(f'/participantes/{pid}').json(), participant)
        updated = PARTICIPANTE | {'nome': 'Atualizado', 'curso': 'Direito', 'email': 'novo@example.com'}
        response = self.client.put(f'/participantes/{pid}', json=updated)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), updated | {'id': pid})
        self.assertEqual(self.client.get('/participantes').json(), [response.json()])
        response = self.client.delete(f'/participantes/{pid}')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get('/participantes').json(), [])

    def test_duplicate_email_creation_and_update_are_atomic(self):
        first = self.create()
        second = self.create(email='outro@example.com')
        for email in ('teste@example.com', 'TESTE@EXAMPLE.COM'):
            for method, route in (('post', '/participantes'), ('put', f"/participantes/{second['id']}")):
                with self.subTest(email=email, method=method):
                    response = getattr(self.client, method)(route, json=PARTICIPANTE | {'nome': 'Nao alterar', 'email': email})
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(response.json(), {'detail': 'Já existe um participante cadastrado com este e-mail.'})
                    self.assertEqual(self.client.get('/participantes').json(), [first, second])
                    self.assertEqual(self.engine.pool.checkedout(), 0)
        self.assertEqual(self.client.put(f"/participantes/{first['id']}", json=PARTICIPANTE).status_code, 200)
        self.create(email='apos-conflito@example.com')

    def test_invalid_inputs_and_missing_participants(self):
        created = self.create()
        for change in ({'nome': '  '}, {'curso': ''}, {'email': 'invalido'}):
            for method, route in (('post', '/participantes'), ('put', f"/participantes/{created['id']}")):
                self.assertEqual(getattr(self.client, method)(route, json=PARTICIPANTE | change).status_code, 422)
        self.assertEqual(self.client.put(f"/participantes/{created['id']}", json={'nome': 'Incompleto'}).status_code, 422)
        self.assertEqual(self.client.get('/participantes').json(), [created])
        for method in ('get', 'put', 'delete'):
            kwargs = {'json': PARTICIPANTE} if method == 'put' else {}
            response = getattr(self.client, method)('/participantes/999', **kwargs)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {'detail': 'Participante não encontrado.'})
        self.assertEqual(self.client.get('/participantes/invalido').status_code, 422)

    def test_persistence_after_restart_and_in_separate_process(self):
        pid = self.create()['id']
        updated = PARTICIPANTE | {'nome': 'Persistido', 'email': 'persistido@example.com', 'curso': 'Direito'}
        self.assertEqual(self.client.put(f'/participantes/{pid}', json=updated).status_code, 200)
        self.client.__exit__(None, None, None)
        code = (
            "import json,sys; from sqlalchemy import create_engine,URL,select; "
            "from sqlalchemy.orm import Session; from model import Participante; "
            "e=create_engine(URL.create('sqlite+pysqlite',database=sys.argv[1])); "
            "s=Session(e); print(json.dumps([p.email for p in s.scalars(select(Participante))])); "
            "s.close(); e.dispose()"
        )
        result = subprocess.run([sys.executable, '-c', code, str(self.path)],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), ['persistido@example.com'])
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual(self.client.get(f'/participantes/{pid}').json(), updated | {'id': pid})
        self.assertEqual(self.client.delete(f'/participantes/{pid}').status_code, 204)
        self.client.__exit__(None, None, None)
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual(self.client.get(f'/participantes/{pid}').status_code, 404)

    def test_registration_reflects_participant_updates(self):
        pid = self.create()['id']
        eid = self.client.post('/eventos', json=EVENTO).json()['id']
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        updated = PARTICIPANTE | {'nome': 'Novo nome', 'curso': 'Direito'}
        self.assertEqual(self.client.put(f'/participantes/{pid}', json=updated).status_code, 200)
        self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').json(), [updated | {'id': pid}])
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/999').status_code, 404)
        self.assertEqual(self.client.delete(f'/participantes/{pid}').status_code, 204)
        self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').json(), [])
        self.assertEqual(self.client.get(f'/eventos/{eid}').status_code, 200)

    def test_cascade_preserves_event_and_other_participants(self):
        pid = self.create()['id']
        other = self.create(email='outro@example.com')
        with self.factory() as db:
            evento = Evento(**EventoCreate(**EVENTO).model_dump())
            db.add_all([Inscricao(evento=evento, participante_id=pid),
                        Inscricao(evento=evento, participante_id=other['id'])])
            db.commit()
            eid = evento.id
        self.assertEqual(self.client.delete(f'/participantes/{pid}').status_code, 204)
        with self.factory() as db:
            self.assertIsNotNone(db.get(Evento, eid))
            self.assertEqual([i.participante_id for i in db.scalars(select(Inscricao))], [other['id']])

    def test_commit_failures_rollback_without_erasing_registrations(self):
        created = self.create()
        pid = created['id']
        eid = self.client.post('/eventos', json=EVENTO).json()['id']
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        for method, route, kwargs in (
            ('post', '/participantes', {'json': PARTICIPANTE | {'email': 'novo@example.com'}}),
            ('put', f'/participantes/{pid}', {'json': PARTICIPANTE | {'nome': 'Nao gravar'}}),
            ('delete', f'/participantes/{pid}', {}),
        ):
            failure = OperationalError('SQL INTERNO', {}, Exception('SEGREDO'))
            with self.subTest(method=method), patch.object(Session, 'commit', side_effect=failure):
                response = getattr(self.client, method)(route, **kwargs)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {'detail': 'Não foi possível acessar os dados. Tente novamente.'})
            self.assertEqual(self.client.get('/participantes').json(), [created])
            self.assertEqual(len(self.client.get(f'/eventos/{eid}/inscricoes').json()), 1)
            self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_unrelated_integrity_error_is_not_reported_as_duplicate_email(self):
        failure = IntegrityError('SQL INTERNO', {}, Exception('OUTRA RESTRICAO'))
        with patch.object(Session, 'flush', side_effect=failure):
            response = self.client.post('/participantes', json=PARTICIPANTE)
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('OUTRA RESTRICAO', response.text)
        self.assertEqual(self.client.get('/participantes').json(), [])

    def test_read_failures_and_documentation(self):
        with patch.object(Session, 'scalars', side_effect=OperationalError('SQL', {}, Exception('SEGREDO'))):
            response = self.client.get('/participantes')
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('SEGREDO', response.text)
        self.assertEqual(self.client.get('/participantes').json(), [])
        self.assertEqual(self.client.get('/docs').status_code, 200)
        schema = self.client.get('/openapi.json').json()
        self.assertEqual(schema['paths']['/participantes']['post']['responses']['201']['content']['application/json']['schema'],
                         {'$ref': '#/components/schemas/ParticipanteRead'})


if __name__ == '__main__':
    unittest.main()

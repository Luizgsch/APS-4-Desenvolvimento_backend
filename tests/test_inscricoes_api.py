from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from api_support import AuthenticatedAPITestCase as APITestCase
import main
from model import Evento, Inscricao


EVENTO = dict(titulo='Workshop', descricao='Teste', data='2026-12-01', horario='19:00',
              local='Sala', capacidade=1, categoria='Workshop')


class InscricoesAPITests(APITestCase):
    def event(self, capacity=1):
        response = self.client.post('/eventos', json=EVENTO | {'capacidade': capacity})
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def participant(self, n=1):
        response = self.client.post('/participantes', json=dict(nome=f'Teste {n}', email=f'teste{n}@example.com', curso='Computacao'))
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def count(self, eid):
        with self.factory() as db:
            return db.scalar(select(func.count()).select_from(Inscricao).where(Inscricao.evento_id == eid))

    def test_creation_fields_relational_listing_and_empty_event(self):
        eid, pid = self.event(), self.participant()
        self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').json(), [])
        response = self.client.post(f'/eventos/{eid}/inscricoes/{pid}')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(set(data), {'id', 'evento_id', 'participante_id', 'data_inscricao'})
        self.assertGreater(data['id'], 0)
        self.assertEqual(data['evento_id'], eid)
        self.assertEqual(data['participante_id'], pid)
        self.assertEqual(date.fromisoformat(data['data_inscricao']), date.today())
        expected = self.client.get(f'/participantes/{pid}').json()
        self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').json(), [expected])
        with self.factory() as db:
            row = db.get(Inscricao, data['id'])
            self.assertEqual(row.evento.id, eid)
            self.assertEqual(row.participante.id, pid)

    def test_duplicate_precedes_full_event_and_capacity_recovers_after_deletion(self):
        eid, pid, other = self.event(), self.participant(), self.participant(2)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        response = self.client.post(f'/eventos/{eid}/inscricoes/{pid}')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {'detail': 'Participante já está inscrito neste evento.'})
        response = self.client.post(f'/eventos/{eid}/inscricoes/{other}')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {'detail': 'Não existem vagas disponíveis para este evento.'})
        self.assertEqual(self.count(eid), 1)
        self.assertEqual(self.client.delete(f'/participantes/{pid}').status_code, 204)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{other}').status_code, 201)

    def test_missing_entities_invalid_paths_and_recovery(self):
        eid, pid = self.event(), self.participant()
        for e, p, message in ((999, pid, 'Evento não encontrado.'), (eid, 999, 'Participante não encontrado.')):
            response = self.client.post(f'/eventos/{e}/inscricoes/{p}')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {'detail': message})
        self.assertEqual(self.client.get('/eventos/999/inscricoes').status_code, 404)
        for route in (f'/eventos/0/inscricoes/{pid}', f'/eventos/{eid}/inscricoes/-1', f'/eventos/{eid}/inscricoes/abc'):
            self.assertEqual(self.client.post(route).status_code, 422)
        self.assertEqual(self.count(eid), 0)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_registration_survives_application_restart(self):
        eid, pid = self.event(), self.participant()
        created = self.client.post(f'/eventos/{eid}/inscricoes/{pid}').json()
        self.client.__exit__(None, None, None)
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual(len(self.client.get(f'/eventos/{eid}/inscricoes').json()), 1)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 409)
        with self.factory() as db:
            row = db.get(Inscricao, created['id'])
            self.assertEqual(row.data_inscricao.isoformat(), created['data_inscricao'])

    def test_increasing_capacity_allows_next_registration(self):
        eid, pid, other = self.event(), self.participant(), self.participant(2)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO | {'capacidade': 2}).status_code, 200)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{other}').status_code, 201)
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO).status_code, 409)
        self.assertEqual(self.count(eid), 2)

    def test_write_and_read_failures_are_atomic_and_sanitized(self):
        eid, pid = self.event(), self.participant()
        for method in ('flush', 'commit'):
            with self.subTest(method=method), patch.object(Session, method, side_effect=OperationalError('SQL INTERNO', {}, Exception('SEGREDO'))):
                response = self.client.post(f'/eventos/{eid}/inscricoes/{pid}')
                self.assertEqual(response.status_code, 500)
                self.assertNotIn('SEGREDO', response.text)
            self.assertEqual(self.count(eid), 0)
            self.assertEqual(self.engine.pool.checkedout(), 0)
        with patch.object(Session, 'flush', side_effect=IntegrityError('SQL', {}, Exception('OUTRA RESTRICAO'))):
            self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 500)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        with patch.object(Session, 'scalars', side_effect=OperationalError('SQL', {}, Exception('SEGREDO'))):
            self.assertEqual(self.client.get(f'/eventos/{eid}/inscricoes').status_code, 500)
        self.assertEqual(len(self.client.get(f'/eventos/{eid}/inscricoes').json()), 1)

    def concurrent(self, operations):
        barrier = Barrier(len(operations))
        def execute(operation):
            barrier.wait(timeout=5)
            return operation().status_code
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(execute, operations))

    def test_concurrent_requests_do_not_overbook_last_vacancy(self):
        eid = self.event()
        pids = [self.participant(n) for n in range(1, 5)]
        operations = [lambda pid=pid: self.client.post(f'/eventos/{eid}/inscricoes/{pid}') for pid in pids]
        self.assertEqual(sorted(self.concurrent(operations)), [201, 409, 409, 409])
        self.assertEqual(self.count(eid), 1)

    def test_concurrent_duplicate_requests_create_one_registration(self):
        eid, pid = self.event(3), self.participant()
        operations = [lambda: self.client.post(f'/eventos/{eid}/inscricoes/{pid}') for _ in range(3)]
        self.assertEqual(sorted(self.concurrent(operations)), [201, 409, 409])
        self.assertEqual(self.count(eid), 1)

    def test_concurrent_capacity_reduction_and_registration_stay_consistent(self):
        eid, pid, other = self.event(2), self.participant(), self.participant(2)
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)
        statuses = self.concurrent([
            lambda: self.client.post(f'/eventos/{eid}/inscricoes/{other}'),
            lambda: self.client.put(f'/eventos/{eid}', json=EVENTO),
        ])
        self.assertIn(statuses, ([201, 409], [409, 200]))
        with self.factory() as db:
            self.assertLessEqual(self.count(eid), db.get(Evento, eid).capacidade)


if __name__ == '__main__':
    unittest.main()

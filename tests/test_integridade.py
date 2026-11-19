from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import patch

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api_support import AuthenticatedAPITestCase as APITestCase
from model import Inscricao


EVENTO = dict(titulo='Revisão', descricao='Teste', data='2026-12-01', horario='19:00',
              local='Sala', capacidade=2, categoria='Workshop')
PARTICIPANTE = dict(nome='Teste', email='integridade@example.com', curso='Computacao')


class IntegridadeTests(APITestCase):
    def seed(self):
        eid = self.client.post('/eventos', json=EVENTO).json()['id']
        pid = self.client.post('/participantes', json=PARTICIPANTE).json()['id']
        response = self.client.post(f'/eventos/{eid}/inscricoes/{pid}')
        self.assertEqual(response.status_code, 201)
        return eid, pid, response.json()['id']

    def test_concurrent_duplicate_emails_create_one_participant(self):
        barrier = Barrier(2)
        def create():
            barrier.wait(timeout=5)
            return self.client.post('/participantes', json=PARTICIPANTE).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(sorted(statuses), [201, 409])
        self.assertEqual(len(self.client.get('/participantes').json()), 1)
        self.assertEqual(self.engine.pool.checkedout(), 0)

    def test_foreign_key_updates_are_rejected_and_rollback_preserves_registration(self):
        eid, pid, iid = self.seed()
        for attribute in ('evento_id', 'participante_id'):
            with self.subTest(attribute=attribute), self.factory() as db:
                setattr(db.get(Inscricao, iid), attribute, 99999)
                with self.assertRaises(IntegrityError):
                    db.commit()
                db.rollback()
                row = db.get(Inscricao, iid)
                self.assertEqual((row.evento_id, row.participante_id), (eid, pid))
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('PRAGMA integrity_check')).all(), [('ok',)])
            self.assertEqual(connection.execute(text('PRAGMA foreign_key_check')).all(), [])

    def test_unique_constraint_protects_registration_if_precheck_misses_duplicate(self):
        eid, pid, _ = self.seed()
        # Força falha na consulta prévia; a restrição real do SQLite deve decidir.
        with patch.object(Session, 'scalar', side_effect=[None, 0]):
            response = self.client.post(f'/eventos/{eid}/inscricoes/{pid}')
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json(), {'detail': 'Participante já está inscrito neste evento.'})
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Inscricao)), 1)
        self.assertEqual(self.engine.pool.checkedout(), 0)


if __name__ == '__main__':
    unittest.main()

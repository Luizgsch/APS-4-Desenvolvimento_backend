import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api_support import AuthenticatedAPITestCase as APITestCase
import main


EVENTO = dict(titulo='Workshop', descricao='Teste', data='2026-12-01', horario='19:00',
              local='Sala', capacidade=3, categoria='Workshop')
ROUTES = ('/relatorios/eventos/ocupacao', '/relatorios/eventos/categorias', '/relatorios/participantes/cursos')


class RelatoriosAPITests(APITestCase):
    def event(self, **changes):
        response = self.client.post('/eventos', json=EVENTO | changes)
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def participant(self, n=1, curso='Computacao'):
        response = self.client.post('/participantes', json=dict(nome=f'Teste {n}', email=f'teste{n}@example.com', curso=curso))
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def register(self, eid, pid):
        self.assertEqual(self.client.post(f'/eventos/{eid}/inscricoes/{pid}').status_code, 201)

    def report(self, index):
        response = self.client.get(ROUTES[index])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('application/json', response.headers['content-type'])
        return response.json()

    def test_empty_database(self):
        for index in range(3):
            self.assertEqual(self.report(index), [])

    def test_occupancy_includes_empty_partial_and_full_events(self):
        empty, partial, full = self.event(), self.event(), self.event(capacidade=1)
        pid = self.participant()
        self.register(partial, pid)
        self.register(full, pid)
        self.assertEqual(self.report(0), [
            dict(evento_id=empty, titulo='Workshop', capacidade=3, total_inscritos=0, vagas_disponiveis=3, percentual_ocupacao=0.0),
            dict(evento_id=partial, titulo='Workshop', capacidade=3, total_inscritos=1, vagas_disponiveis=2, percentual_ocupacao=33.33),
            dict(evento_id=full, titulo='Workshop', capacidade=1, total_inscritos=1, vagas_disponiveis=0, percentual_ocupacao=100.0),
        ])

    def test_categories_do_not_multiply_or_deduplicate_equal_capacities(self):
        first, second = self.event(capacidade=10), self.event(capacidade=10)
        self.event(capacidade=4, categoria='Palestra')
        pids = [self.participant(n) for n in range(1, 4)]
        for pid in pids:
            self.register(first, pid)
        self.register(second, pids[0])
        self.assertEqual(self.report(1), [
            dict(categoria='Palestra', total_eventos=1, capacidade_total=4, total_inscricoes=0),
            dict(categoria='Workshop', total_eventos=2, capacidade_total=20, total_inscricoes=4),
        ])

    def test_courses_count_each_participant_once_and_include_unregistered(self):
        first, second = self.event(), self.event()
        pid = self.participant()
        self.participant(2)
        self.participant(3, 'Direito')
        self.register(first, pid)
        self.register(second, pid)
        self.assertEqual(self.report(2), [
            dict(curso='Computacao', total_participantes=2, total_inscricoes=2),
            dict(curso='Direito', total_participantes=1, total_inscricoes=0),
        ])

    def test_reports_update_after_insert_update_and_cascade_deletions(self):
        eid = self.event()
        pid = self.participant()
        self.assertEqual(self.report(0)[0]['total_inscritos'], 0)
        self.assertEqual(self.report(1)[0]['total_inscricoes'], 0)
        self.assertEqual(self.report(2)[0]['total_inscricoes'], 0)
        self.register(eid, pid)
        self.assertEqual(self.report(0)[0]['total_inscritos'], 1)
        self.assertEqual(self.report(1)[0]['total_inscricoes'], 1)
        self.assertEqual(self.report(2)[0]['total_inscricoes'], 1)
        self.assertEqual(self.client.put(f'/eventos/{eid}', json=EVENTO | {'capacidade': 4, 'categoria': 'Palestra', 'titulo': 'Novo'}).status_code, 200)
        self.assertEqual(self.client.put(f'/participantes/{pid}', json=dict(nome='Novo', email='teste1@example.com', curso='Direito')).status_code, 200)
        self.assertEqual(self.report(0), [dict(evento_id=eid, titulo='Novo', capacidade=4, total_inscritos=1, vagas_disponiveis=3, percentual_ocupacao=25.0)])
        self.assertEqual(self.report(1), [dict(categoria='Palestra', total_eventos=1, capacidade_total=4, total_inscricoes=1)])
        self.assertEqual(self.report(2), [dict(curso='Direito', total_participantes=1, total_inscricoes=1)])
        self.assertEqual(self.client.delete(f'/participantes/{pid}').status_code, 204)
        self.assertEqual(self.report(0)[0]['percentual_ocupacao'], 0.0)
        self.assertEqual(self.report(1)[0]['total_inscricoes'], 0)
        self.assertEqual(self.report(2), [])
        other = self.participant(2)
        self.register(eid, other)
        self.assertEqual(self.client.delete(f'/eventos/{eid}').status_code, 204)
        self.assertEqual(self.report(0), [])
        self.assertEqual(self.report(1), [])
        self.assertEqual(self.report(2), [dict(curso='Computacao', total_participantes=1, total_inscricoes=0)])

    def test_reports_survive_application_restart(self):
        self.register(self.event(), self.participant())
        before = [self.report(index) for index in range(3)]
        self.client.__exit__(None, None, None)
        self.client = self.new_client()
        self.client.__enter__()
        self.assertEqual([self.report(index) for index in range(3)], before)

    def test_one_report_select_plus_identity_and_documentation(self):
        self.register(self.event(), self.participant())
        statements = []
        def capture(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                statements.append(statement)
        event.listen(self.engine, 'before_cursor_execute', capture)
        try:
            for index in range(3):
                statements.clear()
                self.report(index)
                self.assertEqual(len(statements), 2)
                self.assertIn("usuarios", statements[0])
                self.assertNotIn("usuarios", statements[1])
        finally:
            event.remove(self.engine, 'before_cursor_execute', capture)
        schema = self.client.get('/openapi.json').json()
        for route in ROUTES:
            self.assertIn('200', schema['paths'][route]['get']['responses'])
        self.assertEqual(self.client.get('/docs').status_code, 200)

    def test_read_failures_are_sanitized_and_sessions_released(self):
        for route in ROUTES:
            with patch.object(Session, 'execute', side_effect=OperationalError('SQL INTERNO', {}, Exception('SEGREDO'))):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {'detail': 'Não foi possível acessar os dados. Tente novamente.'})
            self.assertEqual(self.engine.pool.checkedout(), 0)
            self.assertEqual(self.client.get(route).json(), [])


if __name__ == '__main__':
    unittest.main()

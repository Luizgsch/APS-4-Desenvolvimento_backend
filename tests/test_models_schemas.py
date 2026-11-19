from datetime import date, time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, delete, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import database
from model import Evento, Inscricao, Participante
from schema.evento_schema import EventoCreate, EventoRead, EventoUpdate
from schema.inscricao_schema import InscricaoCreate, InscricaoRead
from schema.participante_schema import ParticipanteCreate, ParticipanteRead, ParticipanteUpdate


EVENTO = dict(titulo="Workshop", descricao="Teste", data="2026-12-01", horario="19:00",
              local="Sala 1", capacidade=2, categoria="Workshop")
PARTICIPANTE = dict(nome="Teste", email="teste@example.com", curso="Computacao")


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            database.URL.create("sqlite+pysqlite", database=str(Path(self.directory.name) / "models.db")),
            connect_args={"autocommit": False},
        )
        event.listen(self.engine, "connect", database.habilitar_chaves_estrangeiras)
        with patch.object(database, "engine", self.engine):
            database.criar_tabelas()

    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()

    def seed(self, session):
        evento = Evento(**EventoCreate(**EVENTO).model_dump())
        participante = Participante(**PARTICIPANTE)
        inscricao = Inscricao(evento=evento, participante=participante)
        session.add(inscricao)
        session.commit()
        return evento, participante, inscricao

    def test_fields_relationships_and_serialization_after_reconnection(self):
        with Session(self.engine) as session:
            evento, participante, inscricao = self.seed(session)
            ids = evento.id, participante.id, inscricao.id
        self.engine.dispose()
        with Session(self.engine) as session:
            inscricao = session.get(Inscricao, ids[2])
            self.assertEqual(inscricao.evento.inscricoes, [inscricao])
            self.assertEqual(inscricao.participante.inscricoes, [inscricao])
            self.assertEqual(inscricao.data_inscricao, date.today())
            self.assertEqual(InscricaoRead.model_validate(inscricao).evento_id, ids[0])
            self.assertEqual(EventoRead.model_validate(inscricao.evento).horario, time(19))
            self.assertEqual(ParticipanteRead.model_validate(inscricao.participante).email, PARTICIPANTE['email'])
        self.assertEqual(set(inspect(self.engine).get_table_names()), {"eventos", "participantes", "inscricoes", "usuarios"})

    def test_duplicate_email_rejected_including_ascii_case(self):
        with Session(self.engine) as session:
            self.seed(session)
            for email in ("teste@example.com", "TESTE@example.com"):
                with self.subTest(email=email), self.assertRaises(IntegrityError):
                    session.add(Participante(nome="Outro", email=email, curso="Outro"))
                    session.commit()
                session.rollback()

    def test_duplicate_registration_and_invalid_references_rejected(self):
        with Session(self.engine) as session:
            evento, participante, _ = self.seed(session)
            for eid, pid in ((evento.id, participante.id), (999, participante.id), (evento.id, 999)):
                with self.subTest(evento=eid, participante=pid), self.assertRaises(IntegrityError):
                    session.add(Inscricao(evento_id=eid, participante_id=pid))
                    session.commit()
                session.rollback()

    def test_nonpositive_capacity_and_required_columns_rejected(self):
        for change in ({"capacidade": 0}, {"capacidade": -1}, {"titulo": None}):
            with self.subTest(change=change), Session(self.engine) as session:
                values = EventoCreate(**EVENTO).model_dump() | change
                session.add(Evento(**values))
                with self.assertRaises(IntegrityError):
                    session.commit()

    def test_parent_deletion_removes_only_registrations(self):
        for parent_type in (Evento, Participante):
            for mode in ("orm_loaded", "orm_unloaded", "database"):
                with self.subTest(parent=parent_type, mode=mode), Session(self.engine) as session:
                    evento, participante, inscricao = self.seed(session)
                    eid, pid, iid = evento.id, participante.id, inscricao.id
                    session.expunge_all()
                    parent_id = eid if parent_type is Evento else pid
                    if mode == "database":
                        session.execute(delete(parent_type).where(parent_type.id == parent_id))
                    else:
                        parent = session.get(parent_type, parent_id)
                        if mode == "orm_loaded":
                            self.assertEqual(len(parent.inscricoes), 1)
                        session.delete(parent)
                    session.commit()
                    session.expire_all()
                    self.assertIsNone(session.get(Inscricao, iid))
                    other = Participante if parent_type is Evento else Evento
                    other_id = pid if other is Participante else eid
                    self.assertIsNotNone(session.get(other, other_id))
                    session.delete(session.get(other, other_id))
                    session.commit()

    def test_removing_registration_from_collection_deletes_orphan(self):
        with Session(self.engine) as session:
            evento, participante, inscricao = self.seed(session)
            iid = inscricao.id
            evento.inscricoes.remove(inscricao)
            session.commit()
            self.assertIsNone(session.get(Inscricao, iid))
            self.assertIsNotNone(session.get(Participante, participante.id))


class SchemaTests(unittest.TestCase):
    def test_valid_inputs_and_trimmed_text(self):
        self.assertEqual(EventoCreate(**(EVENTO | {"titulo": "  Workshop  "})).titulo, "Workshop")
        self.assertEqual(ParticipanteCreate(**PARTICIPANTE).email, "teste@example.com")
        self.assertEqual(InscricaoCreate(evento_id=1, participante_id=2).participante_id, 2)

    def test_invalid_event_fields_and_missing_required_values(self):
        for schema in (EventoCreate, EventoUpdate):
            for change in ({"titulo": "   "}, {"capacidade": 0}, {"data": "2026-02-30"},
                           {"horario": "25:00"}, {"categoria": ""}):
                with self.subTest(schema=schema, change=change), self.assertRaises(ValidationError):
                    schema(**(EVENTO | change))
            with self.assertRaises(ValidationError):
                schema(titulo="Incompleto")

    def test_invalid_participant_and_registration_fields(self):
        for schema in (ParticipanteCreate, ParticipanteUpdate):
            for change in ({"nome": "  "}, {"email": "invalido"}, {"curso": ""}):
                with self.subTest(schema=schema, change=change), self.assertRaises(ValidationError):
                    schema(**(PARTICIPANTE | change))
            with self.assertRaises(ValidationError):
                schema(nome="Incompleto")
        for ids in ({"evento_id": 0, "participante_id": 1}, {"evento_id": 1, "participante_id": -1}):
            with self.assertRaises(ValidationError):
                InscricaoCreate(**ids)


if __name__ == "__main__":
    unittest.main()

"""Opt-in PostgreSQL tests. Run against a dedicated local test database only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError, DataError

from src.db import get_engine
from src.ingest_data import load
from src.verify_ingestion import verify, compare_reports

FIXTURE = Path(__file__).parent / "fixtures/valid"


@unittest.skipUnless(os.environ.get("PHASE1_TEST_DB") == "1", "Set PHASE1_TEST_DB=1 for a dedicated test database")
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_engine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.connection.execute(text("INSERT INTO source.patients VALUES ('aaaaaaaa-0000-4000-8000-000000000001', '2000-01-01', NULL, 'X')"))
        self.connection.execute(text("INSERT INTO source.organizations VALUES ('bbbbbbbb-0000-4000-8000-000000000001', 'Test', 'City', NULL)"))

    def tearDown(self):
        self.transaction.rollback()
        self.connection.close()

    def insert_encounter(self, **overrides):
        values = dict(e="cccccccc-0000-4000-8000-000000000001", p="aaaaaaaa-0000-4000-8000-000000000001",
                      o="bbbbbbbb-0000-4000-8000-000000000001", start="2020-01-01T10:00:00Z", stop=None,
                      kind="new-valid-class", cost="0.00")
        values.update(overrides)
        self.connection.execute(text("""INSERT INTO source.encounters VALUES
            (:e, :p, :o, :start, :stop, :kind, :cost)"""), values)

    def test_null_stop_zero_cost_and_new_class_allowed(self):
        self.insert_encounter()

    def test_repeated_patient_org_start_allowed(self):
        self.insert_encounter()
        self.insert_encounter(e="cccccccc-0000-4000-8000-000000000002")

    def test_duplicate_primary_key_rejected(self):
        self.insert_encounter()
        with self.assertRaises(IntegrityError):
            self.insert_encounter()

    def test_orphan_foreign_key_rejected(self):
        with self.assertRaises(IntegrityError):
            self.insert_encounter(p="aaaaaaaa-0000-4000-8000-999999999999")

    def test_parent_delete_restricted(self):
        self.insert_encounter()
        with self.assertRaises(IntegrityError):
            self.connection.execute(text("DELETE FROM source.patients WHERE patient_id='aaaaaaaa-0000-4000-8000-000000000001'"))

    def test_stop_before_start_rejected(self):
        with self.assertRaises(IntegrityError):
            self.insert_encounter(stop="2019-01-01T10:00:00Z")

    def test_negative_cost_rejected(self):
        with self.assertRaises(IntegrityError):
            self.insert_encounter(cost="-0.01")

    def test_nonfinite_cost_rejected(self):
        with self.assertRaises((IntegrityError, DataError)):
            self.insert_encounter(cost="NaN")

    def test_blank_class_rejected(self):
        with self.assertRaises(IntegrityError):
            self.insert_encounter(kind=" \t ")

    def test_required_reference_rejected(self):
        with self.assertRaises(IntegrityError):
            self.insert_encounter(o=None)


@unittest.skipUnless(os.environ.get("PHASE1_TEST_DB") == "1", "Set PHASE1_TEST_DB=1 for a dedicated test database")
class TransactionTests(unittest.TestCase):
    def test_failed_reload_preserves_every_row(self):
        engine = get_engine()
        before = verify(engine)

        def fail_after_deletes(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().startswith("INSERT INTO source.encounters"):
                raise RuntimeError("Deliberately injected insertion failure")

        event.listen(engine, "before_cursor_execute", fail_after_deletes)
        try:
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    load(engine, FIXTURE, Path(temp) / "failed.json")
        finally:
            event.remove(engine, "before_cursor_execute", fail_after_deletes)
        after = verify(engine)
        self.assertTrue(compare_reports(before, after)["passed"])
        engine.dispose()

    def test_empty_input_does_not_change_database(self):
        engine = get_engine()
        before = verify(engine)
        with tempfile.TemporaryDirectory() as temp:
            with patch("src.ingest_data.validate_directory", return_value=({"patients": [], "organizations": [], "encounters": []}, {})):
                with self.assertRaisesRegex(ValueError, "empty"):
                    load(engine, FIXTURE, Path(temp) / "empty.json")
        self.assertTrue(compare_reports(before, verify(engine))["passed"])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()

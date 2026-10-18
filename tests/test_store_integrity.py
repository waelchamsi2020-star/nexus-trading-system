import sqlite3
import tempfile
import unittest
from pathlib import Path

from nexus.store import Store


class StoreIntegrityTests(unittest.TestCase):
    def test_reopen_preserves_day_and_audit_without_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ledger.sqlite3'
            store=Store(path);day=store.ensure_day('fixture',50,100,1000,1700000000)
            store.audit('FIXTURE',{'value':1});store.close()
            reopened=Store(path)
            try:
                self.assertEqual(day,reopened.get_day('fixture',1700000000))
                self.assertEqual('FIXTURE',reopened.recent_audit()[0]['event'])
            finally:reopened.close()

    def test_damaged_database_is_refused_and_original_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ledger.sqlite3'
            db=sqlite3.connect(path)
            try:db.execute('CREATE TABLE evidence(value TEXT)');db.commit()
            finally:db.close()
            damaged=b'INVALID SQLITE!!'+path.read_bytes()[16:];path.write_bytes(damaged)
            with self.assertRaises(sqlite3.DatabaseError):Store(path)
            self.assertEqual(damaged,path.read_bytes())

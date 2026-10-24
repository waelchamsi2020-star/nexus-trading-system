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

    def test_legacy_audit_migration_preserves_payload_and_recovers_only_explicit_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'legacy.sqlite3';db=sqlite3.connect(path)
            try:
                db.execute('CREATE TABLE audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL)')
                db.execute('INSERT INTO audit(at,event,payload) VALUES(1,?,?)',('OWNED','{"account_key":"acct-a","result":1}'))
                db.execute('INSERT INTO audit(at,event,payload) VALUES(2,?,?)',('AMBIGUOUS','{"result":2}'))
                db.commit()
            finally:db.close()
            store=Store(path)
            try:
                rows={row['event']:row for row in store.recent_audit()}
                self.assertEqual(rows['OWNED']['account_key'],'acct-a')
                self.assertIsNone(rows['AMBIGUOUS']['account_key'])
                self.assertEqual(rows['OWNED']['payload'],{'account_key':'acct-a','result':1})
                self.assertEqual(rows['AMBIGUOUS']['payload'],{'result':2})
            finally:store.close()

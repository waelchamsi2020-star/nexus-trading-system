"""Real SQLite commit failures; isolated files, no broker connections."""
import sqlite3

import pytest

from nexus.store import Store


def test_commit_failure_rolls_back_ledger_and_audit_and_allows_recovery(tmp_path):
    store = Store(tmp_path / "ledger.sqlite3")
    try:
        store.db.executescript("""
            CREATE TABLE parent(id INTEGER PRIMARY KEY);
            CREATE TABLE child(parent_id INTEGER REFERENCES parent(id)
                DEFERRABLE INITIALLY DEFERRED);
        """)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"), store.transaction() as db:
            db.execute("INSERT INTO child VALUES(999)")
            store.audit("UNCOMMITTED_OPERATION", {"fixture": True})
        assert not store.db.in_transaction
        assert store.db.execute("SELECT COUNT(*) FROM child").fetchone()[0] == 0
        assert store.recent_audit() == []
        # A failed commit cannot poison the connection's next operation.
        store.ensure_day("fixture", 50, 100, 1000, 1700000000)
        assert store.get_day("fixture", 1700000000)["risk_amount"] == 50
    finally:
        store.close()


def test_transaction_interrupt_rolls_back_ledger_and_audit(tmp_path):
    store = Store(tmp_path / "ledger.sqlite3")
    try:
        with pytest.raises(KeyboardInterrupt), store.transaction():
            store.audit("INTERRUPTED_OPERATION", {"fixture": True})
            raise KeyboardInterrupt
        assert not store.db.in_transaction
        assert store.recent_audit() == []
    finally:
        store.close()

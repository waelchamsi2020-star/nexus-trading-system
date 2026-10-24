"""Failed local connection initialization releases every partial resource."""
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nexus.broker import SimBroker
from nexus.engine import Engine
from nexus.store import Store

ROOT = Path(__file__).resolve().parents[1]


def test_saved_scalp_preference_does_not_require_or_create_session_on_read_only_connect(tmp_path):
    engine = Engine(ROOT, tmp_path)
    try:
        engine.config['scalping'] = {'fast': {'enabled': True, 'target_value': 100,
                                            'risk_percent': 2, 'variant': 'fast'}}
        engine._connect(True)
        state = engine._refresh_scalping()['fast']
        assert state['progress']['status'] == 'NOT_AUTHORIZED'
        assert not state['progress']['entries_allowed']
        assert engine.store.db.execute('SELECT COUNT(*) FROM scalp_sessions').fetchone()[0] == 0
        assert engine.executor.mode == 'READ_ONLY'
    finally:
        engine.stop_worker()
        if engine.store:
            engine.store.close()
        engine.cache.db.close()
        engine.news.db.close()


@pytest.mark.parametrize('failure', ['ledger', 'learning'])
def test_partial_connection_failure_clears_broker_and_all_execution_state(tmp_path, failure):
    engine = Engine(ROOT, tmp_path)
    broker = SimBroker(engine.clock)
    broker.close = Mock(wraps=broker.close)
    opened = []

    def open_store(path):
        if failure == 'ledger':
            raise sqlite3.DatabaseError('fixture corrupt ledger')
        store = Store(path)
        opened.append(store)
        return store

    try:
        with patch('nexus.engine.SimBroker', return_value=broker), \
                patch('nexus.engine.Store', side_effect=open_store), \
                patch('nexus.engine.LearningMemory', side_effect=sqlite3.DatabaseError('fixture learning error')), \
                pytest.raises(sqlite3.DatabaseError, match='fixture'):
            engine._connect(True)
        broker.close.assert_called_once()
        for name in ('broker', 'store', 'risk', 'executor', 'scanner', 'learner',
                     'learning_account', '_connected_source', '_connected_account_key'):
            assert getattr(engine, name) is None, name
        assert engine.status == 'DISCONNECTED'
        assert 'fixture' in engine.error
        for store in opened:
            with pytest.raises(sqlite3.ProgrammingError, match='closed'):
                store.db.execute('SELECT 1')
        engine._publish()
        assert engine.snapshot()['account'] is None
        assert engine.snapshot()['mode'] == 'READ_ONLY'
        # A later explicit connect can recover; no broken broker survives.
        engine._connect(True)
        assert engine.executor is not None
        assert engine.status == 'READ_ONLY'
    finally:
        engine.stop_worker()
        if engine.store:
            engine.store.close()
        engine.cache.db.close()
        engine.news.db.close()

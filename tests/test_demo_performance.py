import json
import sqlite3
import time

from tools.demo_performance import summarize


def test_closed_positions_include_magic_zero_exits_and_signed_costs_without_legacy():
    db = sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE state(key TEXT,value TEXT); CREATE TABLE deals(payload TEXT);'
                     'CREATE TABLE attempts(model TEXT,result TEXT,status TEXT);')
    db.execute('INSERT INTO state VALUES (?,?)', ('history_reconciled_at', json.dumps(time.time())))
    db.execute('INSERT INTO attempts VALUES (?,?,?)', ('model_a', '{"deal":1}', 'FILLED'))
    def deal(ticket, entry, magic, profit, volume=.01):
        return {'ticket': ticket, 'position_id': 100, 'entry': entry, 'magic': magic,
                'type': 0, 'profit': profit, 'volume': volume, 'commission': -.1,
                'swap': 0., 'fee': 0., 'symbol': 'EURUSD', 'time_msc': ticket * 1000}
    first = deal(1, 0, 20261019, 0)
    db.execute('INSERT INTO deals VALUES (?)', (json.dumps(first),))
    missing = summarize(db, {'positions': []}, True)
    assert missing['trades'] == 0 and missing['incomplete_positions'] == 1
    db.execute('INSERT INTO deals VALUES (?)', (json.dumps(deal(2, 1, 0, 1)),))
    legacy = {**deal(3, 1, 741903, -99), 'position_id': 300}
    db.execute('INSERT INTO deals VALUES (?)', (json.dumps(legacy),))
    result = summarize(db, {'positions': []}, True)
    assert result['trades'] == 1 and result['wins'] == 1
    assert result['net_realized'] == .8 and result['costs'] == -.2
    assert result['complete'] and result['rows'][0]['strategy'] == 'model_a'
    assert summarize(db, {'positions': [{'identifier': 100}]}, True)['trades'] == 0
    assert summarize(db, {'positions': []}, False)['trades'] is None
    db.execute('UPDATE state SET value=?', (json.dumps(time.time() - 200),))
    assert summarize(db, {'positions': []}, True)['net_realized'] is None
    db.close()

"""Observed Demo performance, attributed by position identity, never entry deals."""
import json
import math
import time


def summarize(db, status, fresh):
    result = {'rows': [], 'trades': None, 'net_realized': None, 'costs': None,
              'max_drawdown': None, 'source': 'DEMO_SERVICE_20261019',
              'scope': 'broker_history_since_first_service_attempt', 'complete': False}
    stamp = db.execute("SELECT value FROM state WHERE key='history_reconciled_at'").fetchone()
    if not fresh or 'positions' not in status or stamp is None:
        return result
    if not 0 <= time.time() - json.loads(stamp[0]) < 120:
        return result
    deals = [json.loads(row[0]) for row in db.execute('SELECT payload FROM deals')]
    open_ids = {p.get('identifier', p.get('ticket')) for p in status['positions']}
    owners = {}
    for model, raw in db.execute("SELECT model,result FROM attempts WHERE status='FILLED'"):
        fill = json.loads(raw)
        owners[fill.get('deal')] = model
    grouped = {}
    for deal in deals:
        pid = deal.get('position_id')
        if pid:
            grouped.setdefault(pid, []).append(deal)
    rows = {}
    closed = []
    observed_tickets = {d.get('ticket') for d in deals}
    incomplete = len(set(owners) - observed_tickets)
    for pid, records in grouped.items():
        entries = [d for d in records if d.get('entry') == 0 and d.get('type') in (0, 1)
                   and d.get('magic') == 20261019 and d.get('ticket') in owners]
        if not entries or pid in open_ids:
            continue
        exits = [d for d in records if d.get('entry') in (1, 3) and d.get('type') in (0, 1)]
        # Missing exits while the observer was offline must not count as zero-return trades.
        if not exits or not math.isclose(sum(d['volume'] for d in entries),
                                        sum(d['volume'] for d in exits), abs_tol=1e-8):
            incomplete += 1
            continue
        models = {owners[d['ticket']] for d in entries}
        if len(models) != 1 or any(d.get('entry') == 2 for d in records):
            incomplete += 1
            continue
        model = next(iter(models))
        gross = sum(d['profit'] for d in records)
        costs = sum(d['commission'] + d['swap'] + d['fee'] for d in records)
        net = gross + costs
        row = rows.setdefault(model, {'strategy': model, 'symbol': entries[0]['symbol'],
                                     'trades': 0, 'gross': 0., 'costs': 0., 'net': 0.,
                                     'validation': 'Demo — مراكز مغلقة'})
        row['trades'] += 1
        row['gross'] += gross
        row['costs'] += costs
        row['net'] += net
        closed.append((max(d['time_msc'] for d in exits), net))
    equity = peak = drawdown = 0.
    for _, net in sorted(closed):
        equity += net
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    result.update(rows=list(rows.values()), trades=len(closed), net_realized=sum(v[1] for v in closed),
                  costs=sum(r['costs'] for r in rows.values()), max_drawdown=drawdown,
                  wins=sum(net > 0 for _, net in closed), incomplete_positions=incomplete,
                  history_reconciled_at=json.loads(stamp[0]), complete=incomplete == 0)
    return result

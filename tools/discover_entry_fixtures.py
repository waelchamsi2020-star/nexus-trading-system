"""Find deterministic synthetic branch fixtures, never performance evidence.

This development utility searches only test inputs for READY branches. It does
not tune rules, evaluate returns, access a broker or qualify a strategy.
"""
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from nexus import strategies as st


def scenario(seed):
    rng = random.Random(seed)
    rows = []; value = 100.
    drift = rng.uniform(-.12, .12)
    period = rng.randrange(6, 40)
    for i in range(120):
        step = rng.gauss(drift, .6) + math.sin(i/period*math.tau)*.3
        if seed % 4 == 0 and i >= 90:
            step *= .12
        opening = value
        value += step
        if i == 119:
            value += rng.uniform(-3, 3)
        high = max(opening, value)+rng.uniform(.05, .5)
        low = min(opening, value)-rng.uniform(.05, .5)
        rows.append({'time': 1700000000+i*3600, 'open': opening, 'high': high,
                         'low': low, 'close': value, 'tick_volume': rng.randrange(50, 250)})
    return rows


def main():
    wanted = json.loads((ROOT/'reports/entry-acceptance-map.json').read_text(encoding='utf-8'))['unmapped_in_this_report']
    wanted = [sid for sid in wanted if sid != 'four_school_confluence']
    found = {}; missing = {(sid, side) for sid in wanted for side in ('BUY', 'SELL')}
    for seed in range(1500):
        rows = scenario(seed); now = rows[-1]['time']+3600
        context = {'data_kind': 'synthetic', 'anchor_time': rows[-30]['time']}
        for sid in sorted({sid for sid, _ in missing}):
            card = st.analyze_strategy(sid, 'FIXTURE', 'H1', rows, now, context)
            key = sid, card['direction']
            if card['actionable'] and key in missing:
                found.setdefault(sid, {})[card['direction']] = {'seed': seed, 'generator': 'synthetic-branch-v1'}
                missing.remove(key)
        if not missing:
            break
    out = ROOT/'tests/fixtures/discovered-entry-seeds.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'type': 'SYNTHETIC_BRANCH_FIXTURES', 'profitability_evidence': False,
                                  'cases': found, 'not_found': [list(x) for x in sorted(missing)]}, indent=2), encoding='utf-8')
    print(json.dumps({'models': len(found), 'sides': sum(map(len, found.values())), 'missing': sorted(missing)}))


if __name__ == '__main__':
    main()

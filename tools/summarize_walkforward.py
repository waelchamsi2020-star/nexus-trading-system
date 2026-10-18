"""Attach dataset fingerprints and descriptive rejection tables to a review."""
import hashlib
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    reports=ROOT/'reports'
    data_path=reports/'walkforward-input.json'
    study_path=reports/'walkforward-review.json'
    study=json.loads(study_path.read_text(encoding='utf-8'))
    data_hash=hashlib.sha256(data_path.read_bytes()).hexdigest()
    if data_hash!=study['input_sha256']:raise ValueError('Study input fingerprint mismatch')
    archive=reports/'walkforward-data';archive.mkdir(exist_ok=True)
    saved=archive/(data_hash+'.json')
    if saved.exists() and saved.read_bytes()!=data_path.read_bytes():raise ValueError('Immutable capture conflict')
    saved.write_bytes(data_path.read_bytes())
    rows=[]
    for result in study['results']:
        skips=[s for fold in result['folds'] for s in fold['skipped']]
        entries=[s for s in skips if 'entry_zone' in s]
        widths=[s['entry_zone'][1]-s['entry_zone'][0] for s in entries]
        cost=sum(s.get('classification')=='COST_ENTRY_ZONE_OR_BRACKET' for s in skips)
        gap=sum(s.get('classification')=='GAP_OR_STRUCTURE' for s in skips)
        other=len(skips)-cost-gap
        raw=sum(f['signals'] for f in result['folds'])+other
        row={'model':result['strategy_id'],'raw_ready':raw,'cost_rejected':cost,
             'gap_or_structure_rejected':gap,'training_volatility_rejected':other,
             'width_min':min(widths) if widths else None,
             'width_median':statistics.median(widths) if widths else None,
             'width_max':max(widths) if widths else None,**result['review'],
             'data_path':str(saved.relative_to(ROOT)),'data_sha256':data_hash,
             'remaining_gap':'No economic inference without fills; zero READY is not a cost-rejection proof'}
        rows.append(row)
    summary={'data_sha256':data_hash,'data_path':str(saved.relative_to(ROOT)),
             'models':rows,'source_study_sha256':hashlib.sha256(study_path.read_bytes()).hexdigest(),
             'orders_sent':0,'statistical_independence_established':False}
    (reports/'walkforward-measurements.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines=['| model | READY | cost | gap | other ATR | fills | net R | win rate | max DD R | trade Sharpe | width min/median/max |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        values=[r[k] for k in ('model','raw_ready','cost_rejected','gap_or_structure_rejected','training_volatility_rejected','trades','net_r','win_rate','max_drawdown_r','sharpe_trade_nonannualized')]
        values.append('/'.join(str(r[k]) for k in ('width_min','width_median','width_max')))
        lines.append('| '+' | '.join(map(str,values))+' |')
    (reports/'walkforward-measurements.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'models':len(rows),'bars':study['completed_bars'],
                      'folds_per_model':sorted({r['nonoverlapping_test_folds'] for r in rows}),
                      'raw_ready':sum(r['raw_ready'] for r in rows),'cost_rejected':sum(r['cost_rejected'] for r in rows),
                      'gap_rejected':sum(r['gap_or_structure_rejected'] for r in rows),
                      'trades':sum(r['trades'] for r in rows),'data_sha256':data_hash}))


if __name__=='__main__':main()

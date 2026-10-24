"""Enforce branch coverage, never substitute statement or combined coverage."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'reports/coverage.json'
    data=json.loads(source.read_text(encoding='utf-8'))
    rows=[]
    for name in ('risk.py','execution.py','store.py','learning/__init__.py','learning/proposals.py',
                 'learning/sandbox.py','learning/drift_monitor.py','regime_router.py',
                 'timeframe_filter.py','cross_asset_filter.py','session_filter.py'):
        matches=[value for path,value in data['files'].items() if path.replace('\\','/').endswith('/nexus/'+name)]
        summary=matches[0]['summary'] if len(matches)==1 else {}
        total=summary.get('num_branches',0);covered=summary.get('covered_branches',0)
        percent=100*covered/total if total else None
        rows.append({'module':name,'covered_branches':covered,'total_branches':total,
                     'branch_percent':percent,'passed':percent is not None and percent>=85,
                     'source_sha256':hashlib.sha256((ROOT/'src/nexus'/name).read_bytes()).hexdigest()})
    report={'threshold':85,'metric':'branch coverage per critical module','modules':rows,
            'coverage_report_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'passed':all(row['passed'] for row in rows)}
    (ROOT/'reports/critical-coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

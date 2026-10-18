"""Run quality commands, preserving actual exit codes and first-party logs."""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report_status(results, required):
    complete = len(results) == len(required) and {x['check'] for x in results} == set(required)
    return {'results':results,'complete':complete,
            'passed':complete and all(x['exit_code']==0 for x in results)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--coverage',action='store_true')
    args=parser.parse_args()
    env = dict(os.environ, PYTHONPATH=str(ROOT/'src'))
    commands = {
        'lint': [sys.executable, '-m', 'ruff', 'check', 'src', 'tests', 'tools'],
        'typecheck': [sys.executable, '-m', 'mypy', 'src', '--ignore-missing-imports'],
        'unit': [sys.executable, '-m', 'pytest', '-q', 'tests'],
        'integration': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_core_integration.py', '-v'],
    }
    if args.coverage:
        commands['unit'].extend(['--cov=nexus','--cov-branch','--cov-report=term',
                                 '--cov-report=json:reports/coverage.json'])
    results = []
    for name, command in commands.items():
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, env=env, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace')
        output = completed.stdout+completed.stderr
        log = ROOT/'reports'/f'quality-{name}.log'
        log.write_text(output, encoding='utf-8')
        item = {'check': name, 'command': command, 'cwd': str(ROOT), 'exit_code': completed.returncode,
                    'utc': datetime.datetime.now(datetime.UTC).isoformat(),
                    'seconds': round(time.monotonic()-started, 3), 'log': str(log.relative_to(ROOT)),
                    'summary': output.strip().splitlines()[-4:]}
        results.append(item)
        print(json.dumps(item), flush=True)
        (ROOT/'reports/quality-gate.json').write_text(json.dumps(report_status(results,commands), indent=2), encoding='utf-8')
        if completed.returncode:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

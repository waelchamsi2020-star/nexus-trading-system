# Quant Trading AI — 0.7.0

Research release 0.7.0. Check reports/release-0.7.0.json for the verified packaging/deployment state.
It is a local, rule-based MT5 Demo research/execution application. It is not a
profit guarantee, a complete implementation of every analytical school, or an
exchange order-flow terminal.

## Architecture and authority

MT5 completed OHLC/tick activity -> validated chart snapshot -> bounded models
-> evidence-family committee -> independent risk authority -> guarded executor
-> broker reconciliation -> attributable learning journal.

The registry contains 58 models: 57 chart hypotheses can produce an actionable
price plan. The four-school research card is advisory; its separate evaluator
requires an actual executable quote and checks its own structural plan.
Correlated transformations do not gain independent votes by duplication.

Tick volume is an activity proxy. No signed trades, DOM, delta or footprint
feed is invented. MT5 calendar coverage acts as an event veto; external news
headlines do not create a directional edge. Local fundamental calculators need
explicit published financial inputs and have no execution authority.

## Local development

Use Python 3.12 on Windows. Install `requirements.txt` for the desktop runtime.
Install `requirements-dev.txt` for the verification tools. A pure synthetic test
run never connects to MT5 or sends orders to a broker.

```powershell
$env:PYTHONPATH='src'
python tools/build_school_catalog.py
python tools/build_knowledge.py
python tools/quality_gate.py
python tools/audit_entry_acceptance.py
python tools/audit_rules.py
node tests/ui_static_check.cjs
node tests/session_view_check.cjs
```

`quality_gate.py` preserves real command exit codes and full logs in `reports`.
Ruff uses its project defaults. Its configuration documents individual API
compatibility exceptions without file-wide ignores. Mypy is run without skipping
local imports; the sole missing-import allowance concerns the installed official
MT5 adapter, which ships no stubs or py.typed marker. This is not a strict typing
claim for every dynamically typed function.

## Runtime and recovery

```powershell
python launch.py --headless --no-connect --data-dir <isolated-test-directory>
```

For a production desktop session use the verified Windows package and the
existing data directory. Read-only and revocation states are meaningful: a
connection alone is not trading authorization. Uncertain broker acknowledgements
must be reconciled, not blindly resent. Stopping entries does not remove broker
protection from existing positions. Real accounts remain blocked in this release.

Do not delete SQLite ledgers, outstanding intents or account learning history.
Persistent data lives in `%LOCALAPPDATA%/NEXUS` in the installed application.
Tests use temporary databases. Account ownership, rule revisions, attributed
outcomes and late cost corrections remain separate and auditable.

## Learning and release acceptance

The local chart classifier is SHADOW_ONLY. Classification calibration and the
holdout economic review are separate. Positive classification results do not
prove profitability; experimental outcomes cannot automatically change live
weights, risk limits or rule code.

The workspace `ACCEPTANCE.md`, `PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md`,
`EVIDENCE.md` and `MODELS_MATRIX.md` track acceptance. A passing synthetic fixture
is branch evidence, not statistical validation. Desktop replacement requires an
integrated verified package, not an isolated code change. Keep one installed
folder and the latest verified ZIP; keep learning history in application data.


## Versioned configuration and execution assumptions
`src/nexus/config/models.yaml` (JSON-compatible YAML) has 58 pinned model entries;
`models.schema.json` validates schema2/profile1.1.0, min_bars and entry_zone_atr_fraction.
Defaults do not change. The min_bars floor cannot fall below algorithm warmup.
The base replay is MARKET_NEXT_OPEN, not Limit. Slippage remains 10 points per
side, a trader-selected scenario, not an empirical broker estimate. Historical
spread is read from the CSV. Commission must have an explicit fee source.
The fast multi-school live router has a separate entry plan; base-model replay
is not a simulation of that complete router. No profitability conclusion follows
from zero fills alone. MetaTrader5 lacks type stubs; mypy permits only
`--ignore-missing-imports`, documented in DECISIONS.md.

## Native-data edge gate (research only)
Export original M5 or H1 candles from MT5, not an M1 aggregation. Save UTF-8 CSV
or tab-delimited MT5 columns `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL>
<SPREAD>` in `data/real/`. At least5000 completed consecutive candles are required.
Record timestamp conversion to UTC and native provenance; the tool cannot
independently authenticate a provider. The metadata JSON must declare:
`source=MT5_NATIVE`, `aggregated=false`, `timeframe=M5` or `H1`, `timezone=UTC`,
`symbol`, positive `point` and `contract_size`, nonnegative `commission_per_lot`,
nonempty `fee_source`, matching `account_currency` and `profit_currency`.

```powershell
$env:PYTHONPATH='src'
python tools/edge_test.py --csv data/real/EURUSD-M5.csv --metadata data/real/EURUSD-M5.metadata.json --output reports/edge-EURUSD-M5.json
```
EDGE_FOUND means only positive observed net R with >=30 simulated trades under
the declared costs. It is not significance, certification, a live policy change,
or a guarantee that random data never pass. Single-file review has no paired
asset/daily auxiliary context. Missing original history blocks evaluation.

## Daily shadow learning framework
The `nexus.learning` package preserves its existing imports. `proposals.py`
stores account-isolated research proposals and transactional decision audit in
a separate SQLite file. Human research approval never applies a live change.
`sandbox.py` compares supplied paired held-out net outcomes with the same costs;
net-R or trade-R Sharpe degradation rejects the candidate. It does not generate
or backtest arbitrary strategy code. `drift_monitor.py` fits training μ±3σ per
school/context. A daily caller can run one explicit cycle; this release does not
install a scheduler or modify live weights.

```powershell
python tools/learning_loop.py --input research-account-export.json --db research-proposals.db --day 2026-10-18 --output reports/learning-cycle.json
```
The input requires one `account_key`, `schools` with revision/symbol/timeframe,
train/heldout feature vectors and names, and optional candidates containing
paired heldout outcomes with original training/prediction/entry/close times.
No candidate or insufficient outcomes produces a recorded research rejection,
not invented parameters. The real131-outcome snapshot had110 separate groups,
max4 samples: NOT_EVALUABLE_REAL_DATA. Synthetic bootstrap results are test-only.

## Running and verification
Windows portable: `Quant Trading AI.exe` or `run.bat`; source run.bat creates a
venv and installs requirements. `run.sh` starts browser/research mode without MT5
connection on a suitable Python3 environment; it is not a Linux MT5 bridge.
Python3.12+ is required for source and development tooling.
`pip install -r requirements-dev.txt`, `python -m playwright install chromium`,
then `python tools/quality_gate.py --coverage` and browser_e2e with a local axe
file. GitHub Actions is configured in .github/workflows/ci.yml; a hosted run
requires this folder to be committed to a repository with Actions enabled.


## CI Setup

Run these commands from the application source folder containing pyproject.toml
and .github/workflows/ci.yml, not from the parent workspace. Create an empty
private GitHub repository first. Install Git and authenticate using your own
GitHub account; no MT5 credentials or live databases are needed.

```powershell
git init -b main
git add .
git diff --cached --stat
git diff --cached --name-only
# Inspect the staged files; never commit account data, broker exports or secrets.
git commit -m "Quant Trading AI quality gates"
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

Replace YOUR_ACCOUNT/YOUR_REPOSITORY with the real repository. For an existing
repository, retain its remote/history instead of reinitializing or replacing it.
Enable Actions in repository Settings → Actions → General if disabled. Push and
pull_request trigger Windows quality gates; workflow_dispatch allows a manual
rerun from Actions. No repository secrets are required for synthetic tests.
Open Actions → Candidate quality gates → latest run, and copy its URL.
Evidence artifacts include lint/types/full tests/integration, branch coverage
and browser/axe reports. A local PASS is not evidence of a hosted run.

Manual follow-ups: docs/MANUAL_ACCESSIBILITY_AUDIT.md; native history instructions:
data/real/README.md. Batch research: `python tools/edge_test.py --data-root data/real`.


## Preliminary segmented research (unreleased candidate)

The normal native-data gate remains >=5000 candles. The explicitly selected
`--preliminary-segments` route instead splits on every unexplained calendar gap,
runs isolated rolling train/test/embargo windows on each segment >=200 bars,
and reports the largest segment separately without double-counting it.
If no segment reaches200, the largest is evaluated with an explicit fallback
flag. No history, open trade or training window crosses a rejected gap.

```powershell
python tools/edge_test.py --csv data/real/H1/EURUSD_H1.csv --metadata scenario-metadata.json --preliminary-segments --commission-scenarios 0 3 7 --output reports/preliminary-H1.json
```

Scenario metadata declares numeric contract/point and hypothetical fees, not a
verified broker commission. Entry/exit simulation is computed once at zero fee;
0/3/7 round-trip fees reprice identical trades. An independent test compares this
against separate authoritative quant.replay runs. Historical spread and adverse
10-point slippage on each side remain fixed. PRELIMINARY_EDGE means positive
observed net R with at least one trade, not statistical significance, independent
portfolio profitability, complete school coverage or permission to execute.
All results remain `qualified=false` and carry no execution authority.

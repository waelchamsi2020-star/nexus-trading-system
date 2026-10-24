# Quant Trading AI — 0.7.17 candidate

Candidate 0.7.16 makes the execution state visible once in the top bar, keeps the lower account panel focused on trading facts and controls, and labels the overview decision card as a preview of the best qualified opportunity with a route to the full list. It does not change school logic, risk limits, or trading authority. The separate Demo sender is not started by this release.
It is a local, rule-based MT5 Demo research/execution application. It is not a
profit guarantee, a complete implementation of every analytical school, or an
exchange order-flow terminal.

## 0.7.16 candidate changes

The executor state appears in the top bar with the technical stop reason available to assistive technology and as a tooltip. The lower execution panel no longer repeats the stopped state. The dashboard explicitly reports that its decision card previews the best opportunity, while the Research view remains the place to inspect model cards. Browser regression checks exercise stopped and unavailable states. No order is sent and no strategy is reclassified as complete or profitable.

## 0.7.15 candidate changes

The default interface is a dark navy AI control room with a subtle connected-node background, compact scan and decision cards, clearer account and trading panels, and a right-side mobile drawer. Six selectable themes remain available. Static and browser checks validate the stylesheet route and MIME type, keyboard use, axe, and ordinary plus Demo-integrated scan, decision, account, and execution-panel geometry at 375/768/1024/1440/1920 px in Arabic and English. Trading remains read-only in the desktop app.

## 0.7.11 candidate changes

The API now returns a compact, account-scoped intent history while keeping the
full ledger and evidence in SQLite. Unresolved intents remain visible; older
settled intents are counted as archived. Audit ownership is a separate
database field, and ambiguous legacy audit rows are not exposed as belonging
to a connected account. This patch did not change model logic, costs, risk
limits, or trading permissions.

The 0.7.6–0.7.10 release line adds optional multi-provider shadow research,
native context/routing studies, and the compact dashboard. See
[Multi-API research bridge](docs/MULTI_API_RESEARCH_BRIDGE.md). Both layers are
advisory only; MT5 remains the sole source for executable quotes, account state
and orders. Research connectors and routing studies do not have order authority.

## Release 0.7.10 changes

The release documents causal market-state, native H4/D1, currency-oriented native
DXY/FX and UTC-session vetoes without adding a model. See
[context protocol](docs/CONTEXT_STUDY_PROTOCOL.md) and
[precise rules](docs/STAGE1_CONTEXT_RULES.md). The routing flag defaults off;
these filters never authorize an order. The user's eight-stage program retains
READ_ONLY until acceptance and six real Demo months. Current research does not
meet stage1's positive economic acceptance criterion; a passing software suite
does not qualify the routing policy or replace the desktop installation.

A maintenance fix makes a verified unchanged connection idempotent.
It preserves an existing unexpired authorization, settings and stopped-entry
state; it cannot activate READ_ONLY, renew a permit or bypass a changed account,
uncertain permissions, daily limits or unresolved sends. Data and financial
results under reports/ remain private and are not published with the source.

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

## Discovery and spread policy — 2026-10-24
The 2026-10-24 read-only Market Watch snapshot is documented in
`reports/PHASE0_DISCOVERY_2026-10-24.md`. A standalone spread threshold no longer
rejects an instrument; median/p90 spread remain observable and actual execution
costs still enter monetary risk and net-reward checks. The generated
`config/instruments.yaml` keeps every route disabled pending a strategy-specific
review. Crypto M1/M5 stay disabled under the prior explicit policy. The mapping
of current system modules and the factual limits of school coverage are in
`ARCHITECTURE.md`; the existing school coverage report remains authoritative for
what is and is not implemented.


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

## Long rolling native-history research

The explicit `--long-history` route uses H1 5000/1000/500 or M5
20000/5000/2500 train/test/step bars, with24 embargo bars. It preserves all
three USD0/3/7 commission scenarios, native spread and10-point adverse slippage
per side. Overlapping full-window diagnostics are kept separate from the
unique chronological primary book; unknown gap exposures retain `R=null`.
No rule, live risk limit, learner or broker position is modified.

```powershell
python tools/edge_test.py --long-history --csv data/real/H1/EURUSD_H1.csv --metadata data/real/H1/EURUSD_H1.metadata.json --output reports/long-study/H1.json --workers 6
python tools/edge_test.py --long-history --csv data/real/M5/EURUSD_M5.csv --metadata data/real/M5/EURUSD_M5.metadata.json --output reports/long-study/M5.json --workers 6
```

Native metadata must include source `MT5_NATIVE`, `aggregated=false`, exact
`csv_sha256`, symbol/frame, point, contract size, profit currency and calendar
profile. Unknown actual fees remain unknown; hypothetical research scenarios
do not become broker fee evidence. Interrupted computation resumes verified
atomic signal-cache chunks. See [the full protocol](docs/LONG_HISTORY_PROTOCOL.md)
for training isolation, censoring, currency conversion, ranking, multiplicity
and retrospective temporal-validation limits.

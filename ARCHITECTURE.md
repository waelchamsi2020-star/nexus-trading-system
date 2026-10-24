# Multi-symbol research and execution architecture

This document maps the requested modular architecture onto the existing NEXUS
source tree. It describes implemented code and explicit limits; it does not
claim that every trading-school interpretation is complete or profitable.

## Existing components

| Responsibility | Existing implementation | Authority |
|---|---|---|
| MT5 access and contract metadata | `src/nexus/broker.py` | Reads quotes, bars, symbol and account data; order operations remain behind the executor |
| Market discovery | `src/nexus/market.py` | Discovers the broker universe and validates contract, quote, session and history |
| School/model registry | `src/nexus/strategies.py`, `src/nexus/local_models.py`, `src/nexus/extended_models.py`, `src/nexus/specialists.py` | 58 registered local models; 57 may produce a price plan, while the four-school card is advisory |
| Multi-school committee | `src/nexus/committee.py`, `src/nexus/confluence.py`, `src/nexus/multischool.py` | Combines model evidence; missing or conflicting evidence abstains |
| Independent risk and durable reservations | `src/nexus/risk.py`, `src/nexus/store.py` | Owns position and daily-risk checks, audit, idempotency, and unresolved-send protection |
| Broker order pipeline | `src/nexus/execution.py` | Checks, reserves, sends once, and reconciles ambiguous outcomes |
| API and desktop control | `src/nexus/server.py`, `src/nexus/app.py` | Localhost-only authenticated control surface; existing desktop UI remains separate |
| Replay, validation and research | `src/nexus/quant.py`, `src/nexus/walkforward.py`, `src/nexus/learning/` | Historical/shadow analysis; not an automatic license to change live rules |
| Optional external and LLM research | `src/nexus/external_research.py`, `src/nexus/llm_research.py` | Research-only and outside the order-critical path |

## Spread policy

There is no standalone spread rejection threshold. The scanner may display a
spread warning and records median/p90 for review, but spread alone does not
exclude a symbol. The actual bid/ask and other execution costs remain inputs to
monetary risk and net-reward checks; the independent Risk Manager can still
veto an order. A stale quote, closed session, unavailable contract data,
missing signal, invalid stop, or risk-limit violation remains a valid rejection.

## School coverage and data limits

The current reference contains 58 entries and 345 documented rule records:
30 technical, 20 fundamental and 8 analytical approaches. Registry tests cover
local algorithm branches, not every published interpretation. A candle-derived
Order Flow/SMC/ICT proxy is not real order-book or signed-trade data. Fundamental
calculators need explicit source data. The audit continues to report
`all_schools_complete=false` and `profitability_proven=false` until those claims
are supported by representative implementation and evidence.

## Discovery result and routing

`config/instruments.yaml` is generated from a read-only Market Watch snapshot.
All symbols are non-routable by default. `ELIGIBLE` in the snapshot means only
that the quote/history sample was sufficiently fresh and minimum-volume stop
risk fit the 1% research budget. It does not mean a strategy exists, a symbol
was activated, or an order may be sent. Crypto M1/M5 remain policy-disabled;
higher timeframes remain research-only until a matching strategy is validated.

Run the profile generator after creating a new read-only snapshot:

```powershell
python tools/generate_instrument_profiles.py --source outputs/<snapshot>.json --output config/instruments.yaml
```

The generator uses the JSON-compatible subset of YAML, the Python standard
library, keeps existing `operator_overrides`, excludes account identifiers, and
never sets `routing.enabled=true`.

## Runtime protection

The existing running `demo_live.py`, its process, authorization, live settings,
and ticket 7808213 were not changed by this source/configuration work. The new
discovery file is not loaded into the running executor. Real-account operation
remains blocked by the existing account-mode guard.

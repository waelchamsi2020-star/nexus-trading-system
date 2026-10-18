# Long-history research protocol

This protocol is research only. It changes no entry rule, model configuration,
account authorization, risk limit, live learner, or broker position.

## Native inputs and rolling schedule

`tools/edge_test.py --long-history --csv <native.csv> --metadata
<native.metadata.json> --output reports/long-study/H1.json --workers 6`

The explicit route requires native, unaggregated M5/H1 metadata whose SHA256
matches the CSV. Actual commission remains unknown in native metadata; research
USD0/3/7 round-trip-per-lot scenarios are separate assumptions. The original
strict route and preliminary segment route retain their previous validation.

| Frame | Train bars | Test bars | Step bars | Embargo bars | Input count | Full folds |
|---|---:|---:|---:|---:|---:|---:|
| H1 | 5000 | 1000 | 500 | 24 | 30860 | 50 |
| M5 | 20000 | 5000 | 2500 | 24 | 100000 | 30 |

The embargo exceeds the unchanged maximum12-bar holding policy. Training fits
only the training-only median arithmetic ATR14 from within-segment windows.
There is no parameter search or machine-learning fit. Signal features use at
most300 completed bars, matching the existing H1/M5 replay lookback. Inputs
after the current decision are inaccessible to the signal calculation.

## Overlapping tests and source gaps

Full test windows overlap. They are reported separately to count profitable
windows and are dependent diagnostics. Their trade lists are never summed
into the primary result.

The primary chronological book uses the most recently trained fold at each
signal. An open position survives later fold updates. There is at most one
position per model and instrument. Each entry appears only once. Different
models are independent research books, not a combined portfolio.

The declared calendar is an unverified research assumption. Unexpected gaps
reset signal history and exclude cross-gap training ATR windows. If a missing
interval prevents identifying an entry or exit, the outcome is censored with
`R=null`, never imputed as zero or closed at the preceding observed price.
Later segments begin separate conditional episodes; this does not assert that
a real broker position was closed. Observable complete-case results can be
overturned by unknown exposures and cannot qualify the strategy.

## Execution and cost assumptions

The existing next-open market geometry is preserved: bid OHLC, row spread,
adverse10 observed symbol points on each side, original price zone, structural
stop and target rounded to the observed point grid, stop before target when
both are touched, completed-close invalidation and time expiry at the next
observed open, and the planned study boundary close. Repricing commission
does not change entry/exit decisions.

USD profit currency uses commission/contract size in quote-price units.
USDJPY uses commission multiplied by the historical exit quote before
dividing by contract size. This is an approximation, not a reconstruction of
historical currency-conversion bid/ask executions. Sharpe is per-trade and
nonannualized. Drawdown is closed-trade R, not account-equity drawdown.

## Ranking and validation

The selected H1 model is fixed by USD7 netR among models with at least30
observable closed trades, with a model-id tie break. Fee0/3 do not choose the
primary winner. All58 registered models remain in Bonferroni/BH correction,
including no-trade models with p=1. Bootstrap uses10000 n-of-n resamples,
centered two-sided null tests and a +1 Monte Carlo correction. Whole-fold
cluster resampling is a temporal-dependence sensitivity diagnostic.

Cross-symbol tests freeze that same selected model on native GBPUSD, USDJPY
and XAUUSD. Any count shortfall, missing context, censored exposure or source
limitation remains visible. Three equal UTC calendar-time periods use three
fresh books and training fits; grouping the original ledger is not substituted
for those replays. All periods are retrospective because historical model
selection already inspected the archive. They are not a pristine future holdout.

## Reproducibility

`tools/long_signal_cache.py` stores compact execution cards in atomic,
SHA-validated gzip chunks. Its cache key includes native CSV bytes, all engine
Python/configuration sources, cache algorithm, Python version, symbol, point,
calendar, frame, lookback, model set and decision start. Interrupted work resumes
verified chunks. A source or native-data mutation aborts computation.

Private prices, account histories, reports and SQLite data remain excluded from
Git. Tests use isolated synthetic fixtures to prove mechanics; those fixtures
never become market-performance evidence or live learning observations.

Every report retains `qualified=false` and `execution_authority=false`.

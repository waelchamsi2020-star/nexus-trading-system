# Post-selection statistical validation protocol

These research tools never grant execution authority. They do not change model
rules, live weights, broker protection, account limits, or the learning database.
Native prices and private reports are excluded from the public Git repository.

## Reproduce

From the source root with the pinned runtime and development dependencies:

```powershell
$env:PYTHONPATH='src'
python tools/statistical_validation.py
python tools/symbol_generalization.py --count 10000
python tools/temporal_validation.py
python -m pytest -q tests/test_statistical_validation.py tests/test_symbol_generalization.py tests/test_temporal_validation_audit.py
```

The first and third commands require the original private native EURUSD H1 CSV,
its metadata and archived preliminary report. Missing data is not generated or
substituted. The second command needs an existing authenticated MT5 terminal and
only reads symbol specifications and historical rates; it sends no orders.

## Fixed scope

- `support_bounce`, H1, existing rule and model configuration unchanged.
- USD 7 per lot round trip is a hypothetical sensitivity, not a verified broker
  fee. Slippage stays at ten observed symbol points per side; spread comes from
  each actual historical row.
- EURUSD/GBPUSD commissions divide by the actual USD-profit contract size.
  Gold uses its own observed contract size and point. USDJPY converts the USD
  fee to JPY at the historical replay exit quote, explicitly approximating the
  conversion execution spread. Returns remain quote-price-risk R, not USD
  portfolio or account returns.
- Calendar-aware segments never bridge an unexplained gap. The pre-existing
  preliminary window policy is preserved; fallback results below 200 bars are
  marked inadequate for generalization rather than silently accepted as proof.

## Bootstrap and multiple comparisons

The archived 47-trade EURUSD sample is repriced at the fixed USD 7 scenario.
NumPy `default_rng(20261018)` generates 10,000 replacement samples of size 47.
The confidence interval uses the 2.5th and 97.5th percentiles of sample means.
Multiplying by 47 gives the interval for a hypothetical fixed-size 47-trade
total; this is not an account-profit forecast.

For the null test, subtract the observed mean from each resampled mean, then
compare absolute centered means against the absolute observed mean. The
two-sided Monte Carlo p-value is `(exceedances + 1) / (10000 + 1)`. The fraction
of positive uncentered samples is not used as a p-value. Within-segment circular
blocks of four trades provide an additional dependence sensitivity; neither
method creates independent market observations or corrects model selection.

All 42 H1 models with trades receive a two-sided test. Positive net return is
counted separately from positive, statistically significant return. Bonferroni
is primary because models share market evidence. Benjamini-Hochberg values are
descriptive; its dependence assumptions have not been independently established.
The report also includes a 58-model registry sensitivity. The broader historical
search across models, frames and fee scenarios remains a selection limitation.
Tiny trade samples do not become reliable evidence through resampling.

## Temporal validation and decision

Split the original 10,000 chronological H1 candles at index 5,000. Freeze the
existing rule/configuration; fit only the ATR volatility baseline on the first
half using windows that do not cross unexplained gaps. Replay the second half
with that frozen baseline and causal indicator warmup confined to each segment.
This is a retrospective audit: the same data already informed model selection,
so it cannot be described as a previously unseen holdout.

`EDGE_CANDIDATE` requires all four criteria: positive bootstrap significance,
survival of multiple-comparison correction, adequate positive cross-symbol
results, and an independently unseen chronological test. Any failed or
unavailable criterion yields the requested operational label
`PRELIMINARY_LUCK`, with `qualified=false`. This label means **unvalidated**;
failure to reject zero does not prove that luck caused the result or that the
true effect is zero. A positive retrospective split is not a passed unseen test.

Method references: [bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
and [false discovery control](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html).
SciPy is a methodology reference, not an added runtime dependency.

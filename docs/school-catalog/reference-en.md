# Quant Trading AI school reference — version 1.2.0

All 58 user-listed entries are preserved. Rules are original sourced summaries, checklists and scope declarations, not complete reproductions of every school's literature or proof of full executable coverage. Overlapping entries are linked and do not multiply committee votes.

SOURCE_PRINCIPLE is a concise sourced principle; OPERATIONAL_CHECKLIST is a Quant Trading AI-authored review procedure; HOUSE_DEFINITION is a declared Quant Trading AI code rule. References are not fetched automatically during trading.

Every extension adds a versioned rule, source evidence, inputs, bullish/bearish and invalidation tests. Knowledge storage is separate from execution authority. Learning records outcomes; it does not change rules or risk without a reviewed version.

## Technical analysis — 30 entries

### 1. Classical Technical Analysis

ID: `ta_classical`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Classify higher highs/lows, lower highs/lows, or a range when neither sequence holds.
- **Operational checklist:** Treat support/resistance as zones around confirmed pivots; record anchors and tests.
- **Operational checklist:** A reversal pattern needs its confirmation break; projected height is an estimate.
- **Operational checklist:** Specify breakout close, volatility tolerance, retest and invalidation before scanning.
- **Operational checklist:** Do not use later pivots at formation time; retain each pivot confirmation time.

Exceptions and limits:

- Retrospectively drawn lines can produce false confirmation.
- Geometric targets are not validated success probabilities.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `classic_reversal_patterns`, `geometric_triangle_breakout`, `support_bounce`, `breakout_retest`, `rectangle_breakout`, `flag_breakout`, `darvas_rising_boxes`

Sources and attribution scope:

- [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf): Technical-analysis and Dow framework; no endorsement of Quant Trading AI thresholds
- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 2. Dow Theory

ID: `ta_dow`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** Separate primary, secondary and short-term movements. — [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf)
- **Source principle:** Independent market-average confirmation belongs to the historical formulation; one-symbol structure is a bounded proxy. — [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf)
- **Source principle:** Maintain the trend hypothesis until a defined reversal signal appears. — [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf)
- **Source principle:** Assess volume confirmation when actual traded volume is available. — [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf)
- **Quant Trading AI computational definition:** Quant Trading AI checks confirmed price pivots; it does not verify every Dow principle.

Exceptions and limits:

- Original market averages are not interchangeable with arbitrary correlated pairs.
- Trend-confirmation delay must be declared.

Required data:

- Completed timestamped OHLC bars
- Explicit synchronized comparison-asset history
- Source-identified actual traded volume

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Explicit synchronized comparison-asset history; Source-identified actual traded volume. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `dow_structure`, `interasset_confirmation`

Sources and attribution scope:

- [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf): Technical-analysis and Dow framework; no endorsement of Quant Trading AI thresholds

### 3. Technical Indicators

ID: `ta_indicators`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Store formula, lookback, input, smoothing and initialization.
- **Operational checklist:** Moving averages measure trend and oscillators measure momentum; an extreme alone is not a reversal order.
- **Operational checklist:** Detect crossovers from two completed bars rather than intrabar flicker.
- **Operational checklist:** Do not count indicators derived from the same data as independent evidence.
- **Operational checklist:** Match calculation and configuration; a tick-weighted mean is not actual trade-volume VWAP.

Exceptions and limits:

- Platform initialization can change early indicator values.
- Ichimoku offsets require correct timestamps without future leakage.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs
- Tick counts explicitly identified as an activity proxy

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs; Tick counts explicitly identified as an activity proxy. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `ema_cross`, `rsi_rebound`, `ichimoku_cross`, `volatility_breakout`, `atr_channel_break`, `vwap_reclaim`, `stochastic_rebound`, `rsi_wilder_rebound`, `macd_signal_cross`, `adx_di_cross`, `cci_reentry`, `williams_reentry`

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula

### 4. Quantitative / Statistical Technical Analysis

ID: `ta_quantitative`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Translate the hypothesis into reproducible signal, entry, target and invalidation.
- **Operational checklist:** Use chronological development, validation and test splits; prevent leakage and test-set reuse.
- **Operational checklist:** Measure performance after spread, commission, slippage and applicable financing.
- **Operational checklist:** Report sample count, uncertainty, drawdown, parameter sensitivity and multiple trials.
- **Operational checklist:** A z-score does not establish Gaussianity or stationarity; test those assumptions separately.
- **Operational checklist:** Learning compares explicit versions; it does not raise risk limits or silently rewrite the reference.

Exceptions and limits:

- An undefined statistic is neither zero nor success.
- Overlapping trade samples are not independent trials.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `zscore_reversion`, `regression_reentry`, `band_reentry`, `momentum_acceleration`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 5. Elliott Wave Theory

ID: `ta_elliott`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** In an ordinary impulse, wave two must not pass the start of wave one. — [Elliott Wave International: Impulse](https://www.elliottwave.com/waveopedia/impulse/)
- **Source principle:** Wave three is not the shortest of waves one, three and five. — [Elliott Wave International: Impulse](https://www.elliottwave.com/waveopedia/impulse/)
- **Source principle:** Wave four does not overlap wave one in an ordinary impulse; diagonals are a separate family. — [Elliott Wave International: Impulse](https://www.elliottwave.com/waveopedia/impulse/)
- **Operational checklist:** Check subdivisions and degree; keep alternate counts with invalidations rather than one certain count.
- **Operational checklist:** Alternation and ratios are ranking guidelines rather than universally mandatory rules.
- **Quant Trading AI computational definition:** Current execution is a first-leg/pullback/break hypothesis, not a complete nested motive/corrective-wave parser.
- **Source principle:** A standard impulse has internal 5-3-5-3-5 subdivisions; six-pivot geometry alone does not verify those subdivisions. — [Elliott Wave International: Waveopedia](https://www.elliottwave.com/waveopedia/)
- **Operational checklist:** A zigzag has internal 5-3-5 subdivisions; local B-retracement and C-length bounds are declared execution parameters.
- **Quant Trading AI computational definition:** Local models separate the two-wave hypothesis, impulse geometry and ABC geometry; each keeps its own confirmation, invalidation, target, revision and outcomes.

Exceptions and limits:

- Do not apply ordinary impulse constraints to diagonals or every correction.
- Unconfirmed pivots remain candidates.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `elliott_candidate`, `elliott_impulse_reversal`, `elliott_zigzag_reversal`

Sources and attribution scope:

- [Elliott Wave International: Impulse](https://www.elliottwave.com/waveopedia/impulse/): Ordinary impulse constraints and distinction from diagonals
- [Elliott Wave International: Waveopedia](https://www.elliottwave.com/waveopedia/): Wave families and degrees; the full source is not reproduced

### 6. Harmonic Analysis

ID: `ta_harmonic`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Fix chronologically ordered pivots and measure leg lengths before ratios.
- **Source principle:** Equal-leg geometry combines a final leg near the first-leg length with a compatible retracement and projection. — [Scott Carney / Harmonic Trader: AB=CD](https://harmonictrader.com/harmonic-patterns/abcd-pattern/)
- **Operational checklist:** Each pattern family needs its own ratio table; do not name unmatched geometry as that pattern.
- **Operational checklist:** Predefine measurement tolerance, confluence zone, reversal confirmation and invalidation.
- **Quant Trading AI computational definition:** The executed Quant Trading AI model is equal-leg only; other families require separate modules and tests.

Exceptions and limits:

- Ratio completion does not guarantee reversal.
- Changing pivots after observing the outcome introduces bias.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `harmonic_abcd`, `harmonic_gartley`, `harmonic_bat`, `harmonic_butterfly`

Sources and attribution scope:

- [Scott Carney / Harmonic Trader: AB=CD](https://harmonictrader.com/harmonic-patterns/abcd-pattern/): Equal-leg geometry and ratio confluence; Quant Trading AI tolerances are model specific

### 7. Price Action

ID: `ta_price_action`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Begin with trend/range context and a level known before the signal bar.
- **Operational checklist:** Compare body, wicks and close location with the prior range and volatility.
- **Operational checklist:** A rejection requires a level test and a close away from it; a wick alone is not confirmed direction.
- **Operational checklist:** Specify breakout/retest entry and structural invalidation.
- **Operational checklist:** Record confirmation bar and current quote; do not enter after price leaves the declared zone.

Exceptions and limits:

- Bar behavior does not reveal participant identity.
- Mid-range signals require different conditions from boundary signals.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `support_bounce`, `pin_rejection`, `inside_bar_break`, `engulfing`, `breakout_retest`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 8. Time Analysis

ID: `ta_time`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define server time, conversion, daylight saving and holidays.
- **Operational checklist:** Do not compare an incomplete opening window with a completed one.
- **Operational checklist:** Fix cycle/seasonality definitions before testing rather than fitting past peaks.
- **Operational checklist:** Use calendar arithmetic for monthly closes rather than fixed seconds.
- **Quant Trading AI computational definition:** The local opening-range model uses a declared UTC window, not an automatically inferred exchange session.
- **Operational checklist:** An interval confirms at its actual end; retain formation, availability and decision times separately.
- **Operational checklist:** Test timing/cycles on later observations; choosing a window after seeing the move creates a new versioned hypothesis.

Exceptions and limits:

- Different contract calendars change time samples.
- Estimated periodicity requires history spanning several cycles.

Required data:

- Completed timestamped OHLC bars
- Session, trade-server and time-zone definitions
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Session, trade-server and time-zone definitions; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `utc_opening_range`, `seasonality`

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula
- [MetaQuotes: CalendarValueHistory](https://www.mql5.com/en/docs/calendar/calendarvaluehistory): Terminal calendar events and trade-server time convention

### 9. Sentiment / Positioning Analysis

ID: `ta_sentiment`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify the sample: survey, options, positioning or internal journal.
- **Operational checklist:** Use publication time, not the described period date, in backtests.
- **Source principle:** Commitments-of-Traders reports are periodic aggregates, not live orders. — [CFTC: Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
- **Operational checklist:** An extreme does not imply immediate reversal; test continuation and reversal separately.
- **Operational checklist:** Do not infer actual participant sentiment from candle color alone.

Exceptions and limits:

- Broker-sample versus whole-market differences must be visible.
- Missing sentiment is missing data, not neutral sentiment.

Required data:

- Local positioning/sentiment file with publication times
- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Local positioning/sentiment file with publication times; Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFTC: Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm): Periodic aggregate positioning, not real-time trade flow
- [CFA Institute: Behavioral Finance — Careers and Definition](https://www.cfainstitute.org/insights/articles/behavioral-finance-careers): Decision biases; mitigation procedures are locally authored

### 10. Inner Circle Trader (ICT)

ID: `ta_ict`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define context range and known highs/lows before detecting a sweep.
- **Quant Trading AI computational definition:** A bullish three-bar gap lies between bar-one high and bar-three low; bearish is mirrored, using completed bars.
- **Operational checklist:** A structure shift needs a confirmed-pivot break under a declared close/wick convention.
- **Operational checklist:** Separate price evidence from institutional-order claims; price alone does not prove order identity.
- **Operational checklist:** Fix first-return zone, invalidation and session window rather than redrawing after the outcome.

Exceptions and limits:

- Terminology varies by lesson/version; the catalog states its local definition.
- Do not count a gap as evidence independent of its underlying price move.

Required data:

- Completed timestamped OHLC bars
- Session, trade-server and time-zone definitions

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Session, trade-server and time-zone definitions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `smc_ict_proxy`, `fvg_first_return`, `smt_proxy`, `four_school_confluence`, `liquidity_bos_retest`

Sources and attribution scope:

- [The Inner Circle Trader: Fair Value Gap & Market Structure Shifts](https://www.youtube.com/watch?v=Bkt8B3kLATQ): Author source for gap and structure-shift concepts; local implementation is explicitly defined

### 11. Wyckoff Method

ID: `ta_wyckoff`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** The three laws concern supply/demand, cause/effect and effort/result. — [Wyckoff Analytics: The Wyckoff Method](https://www.wyckoffanalytics.com/wyckoff-method/)
- **Operational checklist:** Compare price movement with actual volume when available; tick count is a bounded activity measure.
- **Operational checklist:** Do not label a range as certain accumulation/distribution; retain reaccumulation/redistribution alternatives.
- **Operational checklist:** A spring, return and lighter test require a pre-existing range, departure and confirmation.
- **Operational checklist:** Point-and-figure cause measurement needs explicit data and column construction, not arbitrary bar counts.

Exceptions and limits:

- Not every phase event occurs in every case.
- Current execution covers only a local spring-test model.

Required data:

- Completed timestamped OHLC bars
- Source-identified actual traded volume
- Tick counts explicitly identified as an activity proxy

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Source-identified actual traded volume; Tick counts explicitly identified as an activity proxy. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `wyckoff_spring`, `wyckoff_range_expansion`

Sources and attribution scope:

- [Wyckoff Analytics: The Wyckoff Method](https://www.wyckoffanalytics.com/wyckoff-method/): Three laws and phase context; the local spring-test model is bounded

### 12. Gann Analysis

ID: `ta_gann`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Fix price/time units and scale; visual angles change when axes are stretched.
- **Source principle:** Fan/grid tools express geometric relationships from a declared anchor. — [MetaTrader 5 Help: Gann Tools](https://www.metatrader5.com/en/terminal/help/objects/gann)
- **Operational checklist:** A projected time point needs a tolerance window, independent price condition and invalidation.
- **Quant Trading AI computational definition:** The local root grid uses volatility normalization and a quarter-unit shift; this is a Quant Trading AI rule, not a universal Gann law.
- **Operational checklist:** Separate the arithmetic projection from its independently tested success rate.

Exceptions and limits:

- This catalog does not establish all Gann cycles or historical Square-of-Nine rules.
- Changing scale after the signal invalidates comparisons.

Required data:

- Completed timestamped OHLC bars
- Session, trade-server and time-zone definitions
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Session, trade-server and time-zone definitions; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `gann`

Sources and attribution scope:

- [MetaTrader 5 Help: Gann Tools](https://www.metatrader5.com/en/terminal/help/objects/gann): Gann drawing geometry and scale sensitivity only; not all Gann writings

### 13. Fibonacci Analysis

ID: `ta_fibonacci`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Select and retain a confirmed low-to-high or high-to-low anchor leg.
- **Source principle:** Measure retracement as a fraction of leg length; common levels include 38.2% and 61.8%. — [Fidelity: Fibonacci Retracement](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/fibonacci-retracement)
- **Source principle:** The midpoint is commonly plotted but is not an original Fibonacci ratio. — [Fidelity: Fibonacci Retracement](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/fibonacci-retracement)
- **Operational checklist:** Projection from a retracement endpoint differs from within-leg retracement.
- **Operational checklist:** Treat a level as a candidate zone requiring confirmation; avoid retrospective ratio fitting.

Exceptions and limits:

- Different anchors change the reading.
- Multiple-level confluence does not guarantee reversal.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `fib_retracement`, `harmonic_abcd`, `harmonic_gartley`, `harmonic_bat`, `harmonic_butterfly`

Sources and attribution scope:

- [Fidelity: Fibonacci Retracement](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/fibonacci-retracement): Retracement levels and distinction of the midpoint from Fibonacci ratios

### 14. Market Structure

ID: `ta_market_structure`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Store pivot confirmation rule, left/right bar counts and availability time.
- **Operational checklist:** Define external/internal highs and lows at a consistent time scale.
- **Operational checklist:** Structure break, continuation and character change need explicit definitions.
- **Operational checklist:** Treat close and wick breaks separately and record the broken level.
- **Operational checklist:** Expose cross-scale structural conflicts rather than merging them into one direction.
- **Operational checklist:** A pivot's chart timestamp is not its availability time; an eligible break follows confirmation and cannot reuse an earlier break.

Exceptions and limits:

- A pivot becomes confirmed after its occurrence.
- Price structure does not establish order ownership.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `dow_structure`, `breakout_retest`, `donchian_20`

Sources and attribution scope:

- [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf): Technical-analysis and Dow framework; no endorsement of Quant Trading AI thresholds

### 15. Supply & Demand Zones

ID: `ta_supply_demand`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** A price zone models historical response, not directly measured remaining supply/demand.
- **Operational checklist:** Define the base, displacement and zone bounds before a return.
- **Operational checklist:** Store visits, age and prior breaks; a first return differs from repeated tests.
- **Operational checklist:** Invalidate at a declared break event and do not move the boundary after a loss.
- **Operational checklist:** Do not label the zone an institutional order without supporting order data.

Exceptions and limits:

- Wide wicks can make the stop size unsuitable.
- Displacement and expiry thresholds are local testable definitions.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `supply_demand_proxy`, `base_first_return`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 16. Liquidity Analysis

ID: `ta_liquidity`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** Execution liquidity concerns spread, depth and cost at the proposed size. — [CME Group: Liquidity Tool Methodology](https://www.cmegroup.com/education/articles-and-reports/understanding-the-cme-liquidity-tool-methodology)
- **Operational checklist:** Equal highs/prior lows are candidate levels, not proof of stop-order size.
- **Quant Trading AI computational definition:** A local sweep crosses a prior boundary then closes back inside; retain the boundary window.
- **Operational checklist:** Separate sweeps from sustained breakouts using return and expiry conditions.
- **Operational checklist:** With depth, record cancellations, trades and spread changes; displayed depth alone is not guaranteed liquidity.

Exceptions and limits:

- Stop orders are generally not fully visible in public books.
- Displayed orders may be canceled before execution.

Required data:

- Completed timestamped OHLC bars
- Historical order-book updates and cancellations

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Historical order-book updates and cancellations. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `failed_range_break`, `smc_ict_proxy`, `smt_proxy`, `liquidity_bos_retest`

Sources and attribution scope:

- [CME Group: Liquidity Tool Methodology](https://www.cmegroup.com/education/articles-and-reports/understanding-the-cme-liquidity-tool-methodology): Spread, depth and size-dependent execution cost
- [CME Group: Market by Order](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html): Distinguishes an order book from bars and tick counts

### 17. Smart Money Concepts

ID: `ta_smart_money`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Declare the concept set and version instead of an untestable umbrella name.
- **Operational checklist:** Define structure shift, displacement, zone and gap with reproducible price rules.
- **Operational checklist:** Order context, event, confirmation and execution, with candidate expiry.
- **Operational checklist:** Institution/market-maker attribution needs participant data and is not inferred from bars.
- **Operational checklist:** Overlapping concepts share an evidence family to avoid vote inflation.

Exceptions and limits:

- There is no single universal standard for every use of the term.
- A convincing retrospective label does not validate an entry rule.

Required data:

- Completed timestamped OHLC bars
- Historical order-book updates and cancellations

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Historical order-book updates and cancellations. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `smc_ict_proxy`, `fvg_first_return`, `base_first_return`, `smt_proxy`, `liquidity_bos_retest`

Sources and attribution scope:

- [The Inner Circle Trader: Fair Value Gap & Market Structure Shifts](https://www.youtube.com/watch?v=Bkt8B3kLATQ): Author source for gap and structure-shift concepts; local implementation is explicitly defined
- [CME Group: Market by Order](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html): Distinguishes an order book from bars and tick counts

### 18. Volume Analysis

ID: `ta_volume`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Distinguish actual trade volume, quote-update count and unavailable volume.
- **Operational checklist:** Compare volume with prior similar-session/instrument observations, not a universal absolute threshold.
- **Operational checklist:** Higher-activity breakouts are a testable clue; volume alone does not determine side.
- **Operational checklist:** True VWAP needs prices and actual sizes; a tick-count version is labeled a proxy.
- **Operational checklist:** Do not infer volume-at-price from aggregated bar volume without an explicit allocation assumption.
- **Source principle:** Cumulative OBV changes by the bar's volume signed by the close change; an unchanged close leaves OBV unchanged. — [Fidelity: On Balance Volume (OBV)](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv)
- **Operational checklist:** Compare OBV at the same confirmed price pivots; divergence is a candidate requiring a price reclaim, not standalone reversal proof.

Exceptions and limits:

- One broker's volume is not global FX volume.
- Replacing missing volume with zero corrupts comparisons.

Required data:

- Completed timestamped OHLC bars
- Source-identified actual traded volume
- Tick counts explicitly identified as an activity proxy

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Source-identified actual traded volume; Tick counts explicitly identified as an activity proxy. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `vwap_reclaim`, `tick_activity_rejection`, `order_flow`, `obv_divergence_reclaim`, `mfi_tick_rebound`, `wyckoff_range_expansion`

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula
- [CME Group: Market by Order](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html): Distinguishes an order book from bars and tick counts
- [Fidelity: On Balance Volume (OBV)](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv): Close-signed cumulative volume and divergence; reclaim/confirmation thresholds are local model rules

### 19. Japanese Candlestick Patterns

ID: `ta_candlesticks`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define body and upper/lower wicks as range fractions; reject zero range.
- **Operational checklist:** Engulfing concerns bodies under an explicit convention; full-range engulfing is different.
- **Operational checklist:** Doji and long wicks suggest indecision/rejection only with level/trend context.
- **Operational checklist:** Multi-bar patterns need chronological order and gap assumptions appropriate to instrument/session.
- **Operational checklist:** Wait for completed bars and declared confirmation; do not count the same candlestick and price-action event twice.

Exceptions and limits:

- Continuous markets may lack traditional daily-gap conditions.
- A candle name does not automatically define stop or size.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `engulfing`, `pin_rejection`, `inside_bar_break`, `three_bar_reversal`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored
- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula

### 20. Chart / Geometric Patterns

ID: `ta_chart_patterns`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Test head/shoulders and double tops/bottoms using confirmed pivots, explicit symmetry tolerance and neckline.
- **Operational checklist:** A triangle needs converging bounds, multiple touches and pre-break chronology.
- **Operational checklist:** Flags, wedges and rectangles are separate families; approximate resemblance is insufficient.
- **Operational checklist:** Without confirmed breakout, geometry remains a candidate; targets use declared height projection.
- **Operational checklist:** Store fit quality, residuals, age and invalidation events.

Exceptions and limits:

- Tolerance and neckline parameters are implementation specific.
- The release does not execute every flag, wedge or possible family.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `classic_reversal_patterns`, `geometric_triangle_breakout`, `darvas_box`, `rectangle_breakout`, `flag_breakout`, `darvas_rising_boxes`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 21. False Breakout

ID: `ta_false_breakout`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Calculate the range boundary only from bars preceding the signal.
- **Operational checklist:** A cross then return is distinct from a boundary touch.
- **Operational checklist:** Specify same-bar failure or a bounded later-return window.
- **Operational checklist:** Close confirmation and breakout size relative to volatility control boundary noise.
- **Operational checklist:** Invalidation lies beyond the sweep extreme; exit follows a declared plan.

Exceptions and limits:

- An intrabar return may disappear before close.
- Do not infer deliberate stop hunting from price behavior.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `failed_range_break`, `pin_rejection`, `tick_activity_rejection`

Sources and attribution scope:

- [Fidelity: Technical Indicator Guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/using-technical-analysis): Technical tool categories; operational checklists are Quant Trading AI authored

### 22. NEoWave

ID: `ta_neowave`

Documented method scope and development prerequisites, not the entire original NEoWave rulebook.

Rules and review checklist:

- **Operational checklist:** The method is a specialized wave-analysis extension, not another name for a local two-leg hypothesis.
- **Operational checklist:** Declare wave construction, degree, price and time measurements before labeling.
- **Operational checklist:** Separate pattern formation from later confirmation; pre-confirmation labels remain candidates.
- **Operational checklist:** Each model needs identified sources, precise constraints and case tests before executable registration.
- **Operational checklist:** This catalog stores scope and an implementation plan; it neither reproduces the book nor claims a complete NEoWave parser.
- **Operational checklist:** Record price, duration, wave sequence and confirmation for each hypothesis; storing the name does not implement the full NEoWave rule matrix.

Exceptions and limits:

- Basic Elliott rules do not establish complete NEoWave coverage.
- Sampling choices may change wave units.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs
- Session, trade-server and time-zone definitions

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs; Session, trade-server and time-zone definitions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; the current release has no registered trading model covering this school.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [Glenn Neely: NEoWave Forecasting Explained](https://www.neowave.com/neowave-explained.asp): Method scope and confirmation; not the complete NEoWave rulebook

### 23. Order Flow

ID: `ta_order_flow`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Executed flow needs actual trades with size, price and aggressor side; a quote update is not a trade.
- **Operational checklist:** Execution delta is aggressive buy volume minus aggressive sell volume under a documented classifier.
- **Source principle:** Depth needs displayed orders, updates and cancellations; a completed trade is a separate event. — [CME Group: Market by Order](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html)
- **Operational checklist:** A footprint aggregates size by price and side; a heatmap requires historical displayed liquidity.
- **Operational checklist:** Absorption candidates need actual flow with limited price response, not a candle wick alone.
- **Quant Trading AI computational definition:** The current activity agent uses tick counts and close location; it is not true delta, footprint or book analysis.

Exceptions and limits:

- Unverified aggressor side prevents reliable delta.
- Local depth may cover only one broker or venue.

Required data:

- Actual trades with price, size and verified aggressor side
- Historical order-book updates and cancellations
- Tick counts explicitly identified as an activity proxy

Rule application and review protocol — version 1.0.0

- Reference inputs: Actual trades with price, size and verified aggressor side; Historical order-book updates and cancellations; Tick counts explicitly identified as an activity proxy. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `order_flow`, `tick_activity_rejection`

Sources and attribution scope:

- [CME Group: Market by Order](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html): Distinguishes an order book from bars and tick counts
- [CME Group: Liquidity Tool Methodology](https://www.cmegroup.com/education/articles-and-reports/understanding-the-cme-liquidity-tool-methodology): Spread, depth and size-dependent execution cost

### 24. Chaos & Fractal Analysis

ID: `ta_chaos_fractal`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Separate a technical pivot fractal, fractal dimension and a deterministic-chaos claim.
- **Operational checklist:** A five-bar pivot fractal cannot confirm its middle bar before two subsequent bars complete.
- **Operational checklist:** Dimension/Hurst estimation needs a method, sample, sensitivity and bias checks.
- **Operational checklist:** A forward chart offset does not make future observations available.
- **Operational checklist:** A recurring shape does not establish deterministic predictability.
- **Source principle:** An upward fractal has a central high above both highs on each side; a downward fractal reverses the low comparison. — [MetaTrader 5 Help: Fractals](https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals)
- **Quant Trading AI computational definition:** The local five-bar model uses strict comparisons and a fresh post-confirmation close break; ties, tolerances and level age are defined in its versioned contract.

Exceptions and limits:

- The local fractal break implements neither Alligator filters nor the full Bill Williams system, and does not establish deterministic chaos.
- Short-series estimates can be unstable.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `fractal_5_breakout`

Sources and attribution scope:

- [MetaQuotes: iFractals](https://www.mql5.com/en/docs/indicators/ifractals): Fractal indicator interface; does not establish deterministic market chaos
- [MetaTrader 5 Help: Fractals](https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals): Five-bar fractal definition and Alligator-filter context; the local model is not the full Bill Williams system

### 25. Cycle Theory

ID: `ta_cycles`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify calendar, spectral or economic cycles.
- **Operational checklist:** Predefine detrending, sample length and searched periods.
- **Operational checklist:** Test stability, phase and amplitude on later data rather than refitting every peak.
- **Quant Trading AI computational definition:** Local FX seasonality uses only completed prior same-month samples with a declared sample minimum.
- **Operational checklist:** Account for multiple searched periods and compare with a no-cycle baseline.

Exceptions and limits:

- Estimated periodicity may disappear after regime change.
- Monthly seasonality is not a comprehensive cycle engine.

Required data:

- Completed timestamped OHLC bars
- Sufficient history and documented trading costs
- Session, trade-server and time-zone definitions

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Sufficient history and documented trading costs; Session, trade-server and time-zone definitions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `seasonality`, `utc_opening_range`

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula

### 26. Intermarket Analysis

ID: `ta_intermarket`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Declare comparison assets from instrument/currency identity, not similar names.
- **Operational checklist:** Synchronize bars and sessions; do not compare a live asset with stale closed-market data.
- **Operational checklist:** Prefer returns for correlation; price-level correlations may be spurious.
- **Operational checklist:** Correlation varies and does not prove causality, cointegration or lead/lag.
- **Operational checklist:** Test divergent sweeps separately from joint breakouts with predeclared windows/tolerances.

Exceptions and limits:

- Current local pairs use explicit currency metadata, not all global relationships.
- Different price scales need suitable normalization.

Required data:

- Completed timestamped OHLC bars
- Explicit synchronized comparison-asset history
- Sufficient history and documented trading costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Explicit synchronized comparison-asset history; Sufficient history and documented trading costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `interasset_confirmation`, `smt_proxy`

Sources and attribution scope:

- [CMT Association: Technical Analysis — Modern Perspectives](https://cmtassociation.org/wp-content/uploads/2019/01/Technical-Analysis-Modern-Perspectives-CMT-Association.pdf): Technical-analysis and Dow framework; no endorsement of Quant Trading AI thresholds

### 27. Volume Theories

ID: `ta_volume_theories`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** This overlapping volume entry is retained to preserve the user's list.
- **Operational checklist:** On-balance volume signs volume by close change; it is not trade delta.
- **Operational checklist:** Close-location accumulation/distribution is an arithmetic estimate, not participant identification.
- **Operational checklist:** Volume-spread analysis compares range, close and volume with prior context; it does not prove institutional intent.
- **Operational checklist:** Do not give multiple independent votes to transformations of the same volume evidence.
- **Operational checklist:** OBV's initial value is arbitrary; use one consistent volume source and do not mix traded units and tick counts within the series.

Exceptions and limits:

- Actual-volume analysis requires actual volume; tick counts remain labeled proxies.
- Storing definitions does not implement every volume indicator.

Required data:

- Completed timestamped OHLC bars
- Source-identified actual traded volume
- Tick counts explicitly identified as an activity proxy

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Source-identified actual traded volume; Tick counts explicitly identified as an activity proxy. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `vwap_reclaim`, `tick_activity_rejection`, `order_flow`, `obv_divergence_reclaim`, `mfi_tick_rebound`, `wyckoff_range_expansion`

Overlapping entry: `ta_volume`. This does not create another committee vote.

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula
- [Fidelity: On Balance Volume (OBV)](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv): Close-signed cumulative volume and divergence; reclaim/confirmation thresholds are local model rules

### 28. Harmonic Patterns

ID: `ta_harmonic_patterns`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Alias of harmonic analysis retained in original order; it produces no extra vote.
- **Quant Trading AI computational definition:** Referenced families include equal-leg, Gartley, Bat, Butterfly and Crab; the current computational model covers equal-leg only, with no executable ratio tables for the other families.
- **Operational checklist:** Each family needs sourced retracement/projection ratios and invalidation.
- **Operational checklist:** Store candidate confluence and final verification separately; test bullish and bearish cases.
- **Quant Trading AI computational definition:** Only equal-leg is currently executable; other families remain a development reference.

Exceptions and limits:

- Do not reuse one family's ratios for another.
- The library does not republish source books or figures.

Required data:

- Completed timestamped OHLC bars

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `harmonic_abcd`, `harmonic_gartley`, `harmonic_bat`, `harmonic_butterfly`

Overlapping entry: `ta_harmonic`. This does not create another committee vote.

Sources and attribution scope:

- [Scott Carney / Harmonic Trader: AB=CD](https://harmonictrader.com/harmonic-patterns/abcd-pattern/): Equal-leg geometry and ratio confluence; Quant Trading AI tolerances are model specific

### 29. Gap Analysis

ID: `ta_gaps`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** A session price gap is open versus prior close; a three-bar gap is a different definition.
- **Operational checklist:** Define session, price basis, expiry and corporate-action treatment before gap detection.
- **Operational checklist:** Treat common, breakaway, continuation and exhaustion gaps as context-dependent hypotheses.
- **Operational checklist:** Define partial/full fill, expiry and invalidation without assuming every gap fills.
- **Quant Trading AI computational definition:** Current first-return execution covers three-bar gaps, not every exchange opening-gap family.

Exceptions and limits:

- A contract-roll or split discontinuity is not an ordinary trading gap.
- Spread can create apparent gaps in a one-sided quote series.

Required data:

- Completed timestamped OHLC bars
- Session, trade-server and time-zone definitions
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Session, trade-server and time-zone definitions; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `fvg_first_return`, `smc_ict_proxy`

Sources and attribution scope:

- [Fidelity: Charting Indicators — definitions and calculations](https://www.fidelity.com/products/atp/pdf/ATPChartingIndicators.pdf): Indicator and swing-pivot definitions; not the source of the session-pivot formula
- [The Inner Circle Trader: Fair Value Gap & Market Structure Shifts](https://www.youtube.com/watch?v=Bkt8B3kLATQ): Author source for gap and structure-shift concepts; local implementation is explicitly defined

### 30. Pivot Points

ID: `ta_pivots`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** In the traditional formula, pivot equals prior-session high, low and close average. — [Fidelity: Charting Platform Indicators Reference Guide, January 2020, pp. 20–21](https://www.fidelity.com/webcontent/ap130058-research-experience-content/23.01/chartGuide/indicators.pdf)
- **Source principle:** First resistance is twice pivot minus prior low; first support is twice pivot minus prior high. — [Fidelity: Charting Platform Indicators Reference Guide, January 2020, pp. 20–21](https://www.fidelity.com/webcontent/ap130058-research-experience-content/23.01/chartGuide/indicators.pdf)
- **Operational checklist:** Second levels add/subtract prior range; other families require separate formulas.
- **Operational checklist:** Use only a completed prior session and specify daily/weekly/monthly reference.
- **Operational checklist:** A calculated pivot differs from a swing pivot; the level alone is not an entry signal.
- **Operational checklist:** Freeze completed-session H, L and C before the trigger bar; do not rebuild the reference from the current day's range.
- **Source principle:** The basic levels use P=(H+L+C)/3, R2=P+(H-L), S2=P-(H-L), with H, L and C from the prior period. — [Fidelity: Charting Platform Indicators Reference Guide, January 2020, pp. 20–21](https://www.fidelity.com/webcontent/ap130058-research-experience-content/23.01/chartGuide/indicators.pdf)

Exceptions and limits:

- Day boundaries and formula family change levels.
- The local model reclaims a completed daily pivot using the terminal D1 opening clock; it does not cover every pivot family or exchange calendar.

Required data:

- Completed timestamped OHLC bars
- Session, trade-server and time-zone definitions

Rule application and review protocol — version 1.0.0

- Reference inputs: Completed timestamped OHLC bars; Session, trade-server and time-zone definitions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Mapped to specific Quant Trading AI models only; mapping does not make all other school rules executable.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Linked models: `classic_pivot_reclaim`

Sources and attribution scope:

- [Fidelity: Charting Platform Indicators Reference Guide, January 2020, pp. 20–21](https://www.fidelity.com/webcontent/ap130058-research-experience-content/23.01/chartGuide/indicators.pdf): Prior-period pivot and support/resistance formulas; local session boundaries are declared separately

## Fundamental analysis — 20 entries

### 1. Quantitative Fundamental Analysis

ID: `fa_quantitative`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Store each ratio's definition, denominator, units and reporting period.
- **Operational checklist:** Analyze profitability, liquidity, leverage, coverage and cash-flow quality rather than one metric.
- **Operational checklist:** Zero, negative and missing values are distinct states that must remain visible.
- **Operational checklist:** Compare like periods and compatible accounting; disclose non-recurring-item adjustments.
- **Operational checklist:** Do not include a report before publication; distinguish original from restated versions.
- **Operational checklist:** A CFD price is not the underlying company's financial statement.
- **Source principle:** Operating margin divides operating income by net revenue; inventory turnover divides cost of sales by average period inventory. — [SEC: Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide)
- **Operational checklist:** Financial debt/equity differs from total liabilities/equity; retain numerator definitions and do not compare them as one ratio.

Exceptions and limits:

- Sector ratios differ; no universal quality threshold is valid for every firm.
- A near-zero denominator can make a multiple uninformative.

Required data:

- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: multiples, nav

Sources and attribution scope:

- [SEC: Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide): Core financial statements; checklists are Quant Trading AI authored
- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring

### 2. Qualitative Fundamental Analysis

ID: `fa_qualitative`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Document business model, revenue sources, customers, suppliers and concentration.
- **Operational checklist:** Review governance, incentives, capital allocation and related-party dealings.
- **Operational checklist:** Separate management claims, verified facts and analyst estimates.
- **Operational checklist:** Turn a competitive-advantage hypothesis into verification indicators, expiry and counter-risks.
- **Operational checklist:** Retain local references and appropriately permitted evidence; a file name does not establish complete automated understanding.
- **Operational checklist:** Retain supporting/counterevidence, source and date for each judgment; later documents do not rewrite historical assessments.

Exceptions and limits:

- Qualitative scores are explained judgments, not financial facts.
- Absent evidence does not imply high quality.

Required data:

- Source-identified local filings and reports
- Issuer identity, instrument type, currency and rights
- Timestamped decision, forecast and revision journal

Rule application and review protocol — version 1.0.0

- Reference inputs: Source-identified local filings and reports; Issuer identity, instrument type, currency and rights; Timestamped decision, forecast and revision journal. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring

### 3. Macroeconomic Analysis

ID: `fa_macro`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Separate activity level, growth and acceleration, and headline/core inflation where available.
- **Operational checklist:** Compare actual values with a documented prior expectation and available prior vintage, not a later revised forecast.
- **Operational checklist:** Policy-rate decisions, expected paths and real funding conditions are different channels; do not impose a fixed price response.
- **Operational checklist:** Store release time, time zone, source delay and revisions.
- **Operational checklist:** A calendar supplies events/available values; it is insufficient for a complete macro model.
- **Operational checklist:** Abstain when required series are missing; operational news blackout is independent of news direction.
- **Source principle:** An economic vintage is the data available at a specified historical date; later revisions do not become earlier knowledge. — [Federal Reserve Bank of St. Louis: ALFRED Help](https://alfred.stlouisfed.org/help)
- **Source principle:** Period growth uses x[t]/x[t-1]-1; year-over-year growth uses the corresponding prior-year period, with seasonal adjustment and annualization declared. — [Federal Reserve Bank of St. Louis: ALFRED Help](https://alfred.stlouisfed.org/help)

Exceptions and limits:

- Market reaction depends on prior pricing, liquidity and context.
- A final revised series is not what was historically known.

Required data:

- Local economic series with their decision-time vintages
- Terminal calendar values and actual publication times
- Session, trade-server and time-zone definitions

Rule application and review protocol — version 1.0.0

- Reference inputs: Local economic series with their decision-time vintages; Terminal calendar values and actual publication times; Session, trade-server and time-zone definitions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [MetaQuotes: CalendarValueHistory](https://www.mql5.com/en/docs/calendar/calendarvaluehistory): Terminal calendar events and trade-server time convention
- [CFA Institute: Capital Flows and the FX Market](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/capital-flows-and-the-fx-market): Exchange-rate regimes, flows and currency-pair definition
- [Federal Reserve Bank of St. Louis: ALFRED Help](https://alfred.stlouisfed.org/help): Economic-data vintages and availability dates; reference does not add external data fetching

### 4. Industry Analysis

ID: `fa_industry`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define industry, product and geographic-market boundaries before comparing firms.
- **Source principle:** Examine rivalry, entrants, substitutes, supplier power and buyer power. — [CFA Institute: Industry Structure and Competitive Strategy](https://rpc.cfainstitute.org/research/financial-analysts-journal/1980/industry-structure-and-competitive-strategy-keys-to-profitability)
- **Operational checklist:** Connect demand cycle, capacity, regulation and technology to sector revenue/margins.
- **Operational checklist:** Select peers with comparable business models, currencies and cycle exposure, not just labels.
- **Operational checklist:** Record premium/discount rationale and risks that falsify the sector thesis.
- **Operational checklist:** Separate demand growth, added supply and share changes; higher industry sales do not ensure every firm's profitability improves.

Exceptions and limits:

- A sector average can hide materially different businesses.
- Survivor-only samples bias comparisons.

Required data:

- Peer data with consistent periods and accounting
- Source-identified local filings and reports
- Local economic series with their decision-time vintages

Rule application and review protocol — version 1.0.0

- Reference inputs: Peer data with consistent periods and accounting; Source-identified local filings and reports; Local economic series with their decision-time vintages. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Industry and Competitive Analysis](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/industry-and-competitive-analysis): Industry and competitive drivers
- [CFA Institute: Industry Structure and Competitive Strategy](https://rpc.cfainstitute.org/research/financial-analysts-journal/1980/industry-structure-and-competitive-strategy-keys-to-profitability): Five competitive forces

### 5. Company Analysis

ID: `fa_company`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Reconcile income statement, balance sheet, cash-flow statement and notes.
- **Operational checklist:** Decompose revenue into volume, price and mix; separate organic growth from acquisitions.
- **Operational checklist:** Compare accounting earnings with operating cash and required sustaining investment.
- **Operational checklist:** Retain debt maturities, interest, diluted shares and contingent liabilities.
- **Operational checklist:** Construct internally consistent margin, working-capital, investment and funding scenarios.
- **Operational checklist:** Reconcile net income and operating cash through noncash items and working capital; differing accounting classifications need explicit adjustments.
- **Operational checklist:** Do not sum four year-to-date reports as separate quarters; derive discrete periods before trailing-twelve-month totals.

Exceptions and limits:

- Adjusted earnings need a bridge to reported figures.
- EPS growth can come from buybacks rather than business growth.

Required data:

- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Source-identified local filings and reports
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Source-identified local filings and reports; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [SEC: Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide): Core financial statements; checklists are Quant Trading AI authored
- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring

### 6. Graham & Dodd / Security Analysis

ID: `fa_graham_dodd`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Base decisions on the asset, balance-sheet resilience and reasonable return rather than price prediction alone.
- **Operational checklist:** Separate market price from a conservative inspectable earnings/asset value range.
- **Operational checklist:** Margin of safety is a price/value gap with estimation uncertainty; no universal mandatory percentage exists.
- **Operational checklist:** Normalize cyclical earnings and review debt, asset quality, impairment and liquidation risk.
- **Operational checklist:** Do not treat an approximate historical Graham formula as a universal valuation law.
- **Operational checklist:** When using relative margin of safety, explicitly define a measure such as (V-P)/V with positive conservative value; its threshold is local, not attributed to Graham.

Exceptions and limits:

- An apparent discount can be a value trap under persistent deterioration.
- Principal protection is an analytical objective, not a guarantee.

Required data:

- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Asset/liability appraisals and liquidation costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Asset/liability appraisals and liquidation costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: nav, dcf, multiples

Sources and attribution scope:

- [CFA Institute: Investment vs. Speculation — Minsky Criteria](https://blogs.cfainstitute.org/blog/2013/03/04/investment-vs-speculation-using-the-minsky-criteria/): Attributes thorough analysis and principal safety to Graham; does not reproduce his books
- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits

### 7. Behavioral Finance

ID: `fa_behavioral`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify overconfidence, confirmation, anchoring, loss aversion and recency in the decision journal.
- **Operational checklist:** Write forecasts and falsifying evidence before outcomes to avoid hindsight rewriting.
- **Operational checklist:** Compare a thesis with an alternative and baseline before accepting one explanation.
- **Operational checklist:** Review parameter/risk-limit changes after wins or losses as separate behavior.
- **Operational checklist:** Bias analysis does not establish market direction; market sentiment needs a separate data sample.
- **Operational checklist:** Compare recorded forecasts with outcomes and base rates, and retain estimation error; do not assess discipline from winners alone.

Exceptions and limits:

- The system does not diagnose a psychological condition from a trade.
- A profit does not prove an unbiased decision.

Required data:

- Timestamped decision, forecast and revision journal
- Local positioning/sentiment file with publication times

Rule application and review protocol — version 1.0.0

- Reference inputs: Timestamped decision, forecast and revision journal; Local positioning/sentiment file with publication times. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Behavioral Finance — Careers and Definition](https://www.cfainstitute.org/insights/articles/behavioral-finance-careers): Decision biases; mitigation procedures are locally authored

### 8. Value Investing

ID: `fa_value`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Estimate intrinsic value with a suitable model and uncertainty range.
- **Operational checklist:** Investigate cheapness: temporary cycle, permanent deterioration or hidden liability.
- **Operational checklist:** Include capital cost and required reinvestment rather than free growth.
- **Operational checklist:** Record possible gap-closing catalysts, horizon and persistence risks without guaranteed timing.
- **Operational checklist:** A low single multiple is not a substitute for cash-flow and balance-sheet analysis.
- **Operational checklist:** Retain conservative value, executable price, dates and claim currency; an issuer valuation gap requires a documented bridge to the broker contract.

Exceptions and limits:

- Liquidation and going-concern values can differ materially.
- Estimated value changes with new facts.

Required data:

- Local financial statements with period and availability time
- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Asset/liability appraisals and liquidation costs

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Asset/liability appraisals and liquidation costs. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: dcf, nav, multiples

Sources and attribution scope:

- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits
- [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation): Matching firm/equity cash flows to the discount rate

### 9. Growth Investing

ID: `fa_growth`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Separate revenue, earnings, cash-flow and diluted-EPS growth.
- **Operational checklist:** Test addressable market, customer retention, unit economics and execution capacity.
- **Operational checklist:** Link growth to reinvestment, funding and shareholder dilution.
- **Operational checklist:** Fade high growth toward a defensible stable state rather than extending it forever.
- **Operational checklist:** Stress value for slower growth, weaker margins and higher discount rates.
- **Operational checklist:** CAGR is (ending/beginning)^(1/years)-1 for a positive base and positive horizon; a loss-to-profit transition is not assigned this rate.

Exceptions and limits:

- Growth does not make every price acceptable.
- Acquisitions can grow revenue without creating value.

Required data:

- Local financial statements with period and availability time
- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: dcf

Sources and attribution scope:

- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring
- [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation): Matching firm/equity cash flows to the discount rate

### 10. Income Investing

ID: `fa_income`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Distinguish equity dividends, bond coupons, fund distributions and return of capital.
- **Operational checklist:** Compare cash income with available cash, debt obligations and required investment.
- **Operational checklist:** Compute current-price yield after supplied taxes/fees where applicable.
- **Operational checklist:** Test distribution cuts, credit, rate and capital-value risks.
- **Operational checklist:** High yields caused by price collapse are not evidence of quality.
- **Operational checklist:** Define trailing yield using cash distributions over a declared period divided by current price; show forward yield, special payouts and return of capital separately.

Exceptions and limits:

- Distributions can change and do not guarantee total return.
- A CFD may reflect cash adjustments without granting share ownership.

Required data:

- Verified cash dividends and distribution policy
- Local financial statements with period and availability time
- Maturity, coupon, seniority and embedded-option terms
- Fund holdings, NAV, prospectus and fees

Rule application and review protocol — version 1.0.0

- Reference inputs: Verified cash dividends and distribution policy; Local financial statements with period and availability time; Maturity, coupon, seniority and embedded-option terms; Fund holdings, NAV, prospectus and fees. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: ddm, bond

Sources and attribution scope:

- [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation): Dividend cash flows and terminal-growth condition
- [Investor.gov: Bonds — FAQs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds): Bondholder cash-flow rights and credit risk
- [SEC: Invest Wisely — Mutual Funds](https://www.sec.gov/files/investor/pubs/inwsmf.htm): Fund prospectus, objectives and expenses

### 11. Growth at a Reasonable Price (GARP)

ID: `fa_garp`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Combine financeable growth with valuation that does not assume perfect execution.
- **Operational checklist:** PEG requires positive earnings, positive growth and explicit growth units.
- **Operational checklist:** Expected growth differs from history; store source, date and horizon.
- **Operational checklist:** Compare profitability, leverage and reinvestment rather than one fixed multiple cutoff.
- **Operational checklist:** Do not treat a particular PEG level as a universal law or direct order.
- **Source principle:** PEG=(P/E)/g%; 10% growth enters as 10, not 0.10, with compatible earnings/growth horizons; low PEG alone does not establish quality. — [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples)

Exceptions and limits:

- Negative growth makes conventional PEG interpretation unsuitable.
- The style overlaps value/growth and does not automatically add independent evidence.

Required data:

- Local financial statements with period and availability time
- Local cash-flow forecasts and assumptions
- Peer data with consistent periods and accounting

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Local cash-flow forecasts and assumptions; Peer data with consistent periods and accounting. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: multiples

Sources and attribution scope:

- [CFA Institute: GARP Investing — Golden or Garbage?](https://rpc.cfainstitute.org/blogs/enterprising-investor/2019/garp-investing-golden-or-garbage): Value/growth overlap and style limits
- [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples): Consistent multiple numerator/denominator and suitable comparables

### 12. Index Investing

ID: `fa_index`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Specify market-cap, equal-weight or factor construction and rebalance rules.
- **Source principle:** Index tracking is a product objective, not guaranteed replication or absence of risk. — [Investor.gov: Index Funds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4)
- **Operational checklist:** Measure tracking difference/error, fees, taxes and execution.
- **Operational checklist:** Review sector/issuer/weight concentration and point-in-time membership changes.
- **Operational checklist:** A broker index contract is not an index fund owning constituents.
- **Operational checklist:** Compare fund returns with a benchmark matching currency, distributions and dates after fees; tracking difference differs from variability of tracking differences.

Exceptions and limits:

- Backtesting today's constituents causes survivorship bias.
- An index may be concentrated despite many constituents.

Required data:

- Point-in-time index membership and weights
- Fund holdings, NAV, prospectus and fees
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Point-in-time index membership and weights; Fund holdings, NAV, prospectus and fees; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [Investor.gov: Index Funds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4): Index tracking, risk and fees

### 13. Fund Investing

ID: `fa_fund`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Review objectives, restrictions, legal structure and verified local prospectus.
- **Operational checklist:** Inspect holdings, leverage, liquidity and portfolio overlap.
- **Operational checklist:** Operating, entry/exit and funding costs affect return through different mechanisms.
- **Operational checklist:** Compare net-of-fee performance with a suitable risk/horizon-matched benchmark.
- **Operational checklist:** For traded/closed-end funds, distinguish market price from NAV and premium/discount.
- **Operational checklist:** Per-unit NAV uses fund assets less liabilities divided by outstanding units at valuation time; exchange price may differ from NAV.

Exceptions and limits:

- Similarly named funds may differ in share class, fees and holdings.
- Past performance alone is not a sufficient selection rule.

Required data:

- Fund holdings, NAV, prospectus and fees
- Source-identified local filings and reports
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Fund holdings, NAV, prospectus and fees; Source-identified local filings and reports; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: nav

Sources and attribution scope:

- [SEC: Invest Wisely — Mutual Funds](https://www.sec.gov/files/investor/pubs/inwsmf.htm): Fund prospectus, objectives and expenses

### 14. Commodity Fundamental Analysis

ID: `fa_commodity`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify commodity, grade, location, quote units and delivery terms.
- **Operational checklist:** Reconcile production, use, imports, exports and inventory by season/region.
- **Source principle:** An upward futures curve is contango and a downward curve backwardation; neither guarantees spot direction. — [CME Group: What Is Contango and Backwardation?](https://www.cmegroup.com/education/courses/introduction-to-precious-metals/what-is-contango-and-backwardation.hideSubnav.educationIframe.html?hideAddThisExt=y&hideFooter=y&hideHeader=y&hideRightRail=y)
- **Operational checklist:** Separate spot moves from roll, financing and storage effects.
- **Operational checklist:** A continuous broker contract needs a documented roll method; it does not replace commodity-balance data.
- **Operational checklist:** Inventory is a stock; production/use are period flows. Match units, location, grade and measurement time before a commodity balance.

Exceptions and limits:

- Delivery locations are not comparable without basis adjustments.
- Expiry changes can distort calculated returns.

Required data:

- Locally verified production, use, inventories and delivery data
- Individual futures contracts, expiries and roll history
- Issuer identity, instrument type, currency and rights
- Local economic series with their decision-time vintages

Rule application and review protocol — version 1.0.0

- Reference inputs: Locally verified production, use, inventories and delivery data; Individual futures contracts, expiries and roll history; Issuer identity, instrument type, currency and rights; Local economic series with their decision-time vintages. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CME Group: What Is Contango and Backwardation?](https://www.cmegroup.com/education/courses/introduction-to-precious-metals/what-is-contango-and-backwardation.hideSubnav.educationIframe.html?hideAddThisExt=y&hideFooter=y&hideHeader=y&hideRightRail=y): Futures-curve shape; not a guaranteed spot-price direction

### 15. Currency Fundamental Analysis

ID: `fa_currency`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify base/quote currencies and the meaning of a price rise before return calculation.
- **Source principle:** Distinguish nominal/real exchange rates and floating/pegged regimes. — [CFA Institute: Capital Flows and the FX Market](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/capital-flows-and-the-fx-market)
- **Operational checklist:** Compare rate, inflation, growth, flow and risk differences between both economies.
- **Operational checklist:** Carry combines financing, price movement and regime risk; it is not guaranteed interest income.
- **Operational checklist:** Verify broker swap, hedging and the currency in which profit is measured.
- **Source principle:** Domestic return is (1+foreign-asset return)*(1+foreign-currency return)-1 when FX is domestic units per foreign unit. — [CFA Institute: Currency Management — An Introduction](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/currency-management-introduction)

Exceptions and limits:

- Rate differentials do not give a fixed short-term direction.
- A peg may constrain moves while creating a different discontinuity risk.

Required data:

- Local economic series with their decision-time vintages
- Terminal calendar values and actual publication times
- Issuer identity, instrument type, currency and rights
- Timestamped yield/discount curves and credit spreads

Rule application and review protocol — version 1.0.0

- Reference inputs: Local economic series with their decision-time vintages; Terminal calendar values and actual publication times; Issuer identity, instrument type, currency and rights; Timestamped yield/discount curves and credit spreads. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Capital Flows and the FX Market](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/capital-flows-and-the-fx-market): Exchange-rate regimes, flows and currency-pair definition
- [CFA Institute: Currency Management — An Introduction](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/currency-management-introduction): Domestic-currency return, hedging and carry

### 16. Bond Analysis

ID: `fa_bond`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define principal, coupon/frequency, maturity, seniority and embedded options.
- **Operational checklist:** Value contractual discounted cash flows; distinguish clean/dirty price and accrued interest.
- **Operational checklist:** Measure rate sensitivity using duration/convexity with approximation limits.
- **Operational checklist:** Analyze debt service, collateral, recovery and credit spreads.
- **Operational checklist:** Yield to maturity depends on holding, payments and reinvestment; it is not always realized return.
- **Source principle:** Modified duration approximates relative price change as minus duration times the decimal yield change; accuracy depends on move size and it does not forecast returns. — [CFA Institute: Yield-Based Bond Duration Measures and Properties](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/yield-based-bond-duration-measures-and-properties)
- **Operational checklist:** Retain settlement date, accrued interest and clean/full price basis; a callable bond needs option treatment beyond a fixed-coupon calculator.

Exceptions and limits:

- Callable bonds require option valuation; simple discounting is insufficient.
- The local bond calculator handles supplied cash flows and does not infer issuer quality.

Required data:

- Maturity, coupon, seniority and embedded-option terms
- Timestamped yield/discount curves and credit spreads
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Maturity, coupon, seniority and embedded-option terms; Timestamped yield/discount curves and credit spreads; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: bond, pv

Sources and attribution scope:

- [Investor.gov: Bonds — FAQs](https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products/bonds): Bondholder cash-flow rights and credit risk
- [CFA Institute: Interest Rate Risk and Return](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/interest-rate-risk-and-return): Duration, reinvestment risk and holding horizon
- [CFA Institute: Yield-Based Bond Duration Measures and Properties](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/yield-based-bond-duration-measures-and-properties): Yield sensitivity and linear-approximation limits; no curve/option engine implementation is claimed

### 17. Equity Analysis

ID: `fa_equity`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Identify class rights, votes, liquidity, diluted shares and claims senior to equity.
- **Operational checklist:** Review profitability, cash quality, debt, growth and reinvestment.
- **Operational checklist:** Reconcile equity and enterprise values through debt, cash and other claims.
- **Operational checklist:** Per-share value needs a share count consistent with cash flows and claims.
- **Operational checklist:** An equity CFD does not automatically provide the same rights or dividend policy.
- **Operational checklist:** Match share class, rights and diluted share count to value; free float for liquidity does not replace outstanding shares in valuation.

Exceptions and limits:

- Corporate actions change price, share count and return.
- Estimated share value is not a guaranteed execution price.

Required data:

- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Splits, distributions, issuance and share-count changes
- Local cash-flow forecasts and assumptions

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Splits, distributions, issuance and share-count changes; Local cash-flow forecasts and assumptions. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: dcf, ddm, multiples, nav

Sources and attribution scope:

- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits
- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring

### 18. Absolute / Intrinsic Valuation

ID: `fa_absolute`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Specify equity, firm, dividend or residual-income cash-flow basis.
- **Source principle:** Match equity flows with cost of equity and firm flows with a suitable capital cost. — [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation)
- **Operational checklist:** Perpetual-growth terminal value needs discount rate greater than growth and economic consistency.
- **Operational checklist:** Retain scenarios and growth/margin/discount sensitivity rather than one value.
- **Operational checklist:** Document forecast date/source; a correct calculator does not make assumptions correct.
- **Source principle:** Per-share residual income uses RI[t]=EPS[t]-r*B[t-1]; value adds current book value to the present value of expected residual income. — [CFA Institute: Residual Income Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation)
- **Operational checklist:** Residual-income valuation is research reference only in this release; DCF/NAV calculators do not implement it by association, and comprehensive-income items need appropriate reconciliation.

Exceptions and limits:

- Negative cash flows or changing leverage require an appropriate model.
- Cash-flow/discount inflation basis and currency must match.

Required data:

- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: dcf, ddm, pv

Sources and attribution scope:

- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits
- [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation): Matching firm/equity cash flows to the discount rate
- [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation): Dividend cash flows and terminal-growth condition
- [CFA Institute: Residual Income Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation): Residual income and equity charge; reference only, with no registered residual-income calculator

### 19. Relative Valuation

ID: `fa_relative`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Select peers with compatible business, growth, risk and accounting.
- **Source principle:** Price multiples use equity measures; enterprise multiples use measures for all capital providers. — [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples)
- **Operational checklist:** Match price date, trailing/forward period and share count.
- **Operational checklist:** Disclose exceptional items, negatives, outliers and sample aggregation.
- **Operational checklist:** Cheapness against an overpriced peer does not establish intrinsic undervaluation.
- **Source principle:** Compute historical EPS from reports available on the price date; restatements released later remain later vintages. — [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples)

Exceptions and limits:

- Conventional P/E does not meaningfully interpret negative earnings.
- A peer discount may reflect quality or risk differences.

Required data:

- Peer data with consistent periods and accounting
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Splits, distributions, issuance and share-count changes

Rule application and review protocol — version 1.0.0

- Reference inputs: Peer data with consistent periods and accounting; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Splits, distributions, issuance and share-count changes. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: multiples

Sources and attribution scope:

- [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples): Consistent multiple numerator/denominator and suitable comparables

### 20. Asset-Based Valuation

ID: `fa_asset_based`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Define going concern or liquidation, asset identity, ownership and restrictions.
- **Operational checklist:** Adjust assets/liabilities to a documented consistent valuation basis.
- **Operational checklist:** Net asset value equals adjusted assets less liabilities and senior claims.
- **Operational checklist:** Include selling costs, tax, timing, discounts and off-balance-sheet claims.
- **Operational checklist:** Per-share value needs consistent shares/rights; book value is not automatically market value.
- **Operational checklist:** Review liens, senior claims and liquidation costs before dividing by shares; do not subtract debt twice when already included in liabilities.

Exceptions and limits:

- Important intangible assets may be absent from books.
- Asset appraisals need source/date and cannot be inferred from a chart.

Required data:

- Asset/liability appraisals and liquidation costs
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Asset/liability appraisals and liquidation costs; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: nav

Sources and attribution scope:

- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits
- [SEC: Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide): Core financial statements; checklists are Quant Trading AI authored

## Fundamental approaches — 8 entries

### 1. Top-Down Approach

ID: `ap_top_down`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Start with macro/risk regime, then sector, then issuer/instrument.
- **Operational checklist:** Link levels through explicit transmission channels and falsifiable forecasts.
- **Operational checklist:** Do not select sectors/firms for narrative fit alone; review data and valuation.
- **Operational checklist:** Keep availability times across all levels and avoid double-counting shared evidence.
- **Operational checklist:** The approach organizes research rather than providing one valuation calculator or trade rule.
- **Operational checklist:** Each transmission channel needs a horizon, availability time and falsifier; macro, sector and company agreement are not three independent observations when derived from one release.

Exceptions and limits:

- A strong economy does not guarantee returns on an expensive stock.
- A broken transmission channel invalidates that part of the thesis.

Required data:

- Local economic series with their decision-time vintages
- Peer data with consistent periods and accounting
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Local economic series with their decision-time vintages; Peer data with consistent periods and accounting; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Industry and Competitive Analysis](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/industry-and-competitive-analysis): Industry and competitive drivers
- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring

### 2. Bottom-Up Approach

ID: `ap_bottom_up`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Start with instrument rights, company economics and balance sheet.
- **Operational checklist:** Build cash-flow, asset or peer models suitable to the company.
- **Operational checklist:** Stress sector, rate and currency dependence even when research starts at company level.
- **Operational checklist:** Compare the result with portfolio risk, liquidity and concentration.
- **Operational checklist:** A stored company thesis does not automatically authorize a broker contract trade.
- **Operational checklist:** Show the bridge from financial fact to assumption to calculation; stress a failed company thesis before attributing valuation results to method accuracy.

Exceptions and limits:

- Independence from macro forecasting does not mean no macro exposure.
- Unverified financial inputs prevent a reliable value estimate.

Required data:

- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights
- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency

Rule application and review protocol — version 1.0.0

- Reference inputs: Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights; Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Sources and attribution scope:

- [CFA Institute: Company Analysis — Past and Present](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present): Business and performance analysis; no endorsement of local scoring
- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits

### 3. Dividend Discount Model (DDM)

ID: `ap_ddm`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Source principle:** Present value sums discounted future dividends and any finite-horizon terminal value. — [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation)
- **Source principle:** Constant-growth value is next-period dividend divided by discount rate minus growth. — [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation)
- **Operational checklist:** Discount rate must exceed growth with consistent period units and currency.
- **Operational checklist:** Multistage growth requires period-specific dividends and sustainable terminal growth.
- **Operational checklist:** Check payouts against capacity; do not substitute last dividend for next dividend without an explicit assumption.
- **Source principle:** Year-n terminal value uses D[n+1]/(r-g) and is discounted from year n; do not substitute D[n] or discount the terminal amount twice. — [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation)

Exceptions and limits:

- Non-paying firms may require cash-flow or residual-income models.
- A discount rate near growth makes the estimate highly sensitive.

Required data:

- Verified cash dividends and distribution policy
- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Verified cash dividends and distribution policy; Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: ddm

Sources and attribution scope:

- [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation): Dividend cash flows and terminal-growth condition

### 4. Discounted Cash Flow (DCF)

ID: `ap_dcf`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** Declare equity or firm cash flows and do not mix bases in one valuation.
- **Source principle:** Discount equity flows at equity cost and firm flows at a rate consistent with capital structure. — [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation)
- **Operational checklist:** Finite-horizon value adds discounted cash flows and terminal value discounted from its terminal date.
- **Operational checklist:** Store growth, margin, reinvestment, tax and currency assumptions.
- **Operational checklist:** Bridge enterprise to equity by adding non-operating assets and subtracting relevant claims.
- **Operational checklist:** Expose horizon/growth/discount sensitivity; calculator output alone is not an execution signal.
- **Source principle:** FCFF=NI+NCC+interest*(1-tax)-fixed investment-working-capital investment; FCFE=NI+NCC-fixed investment-working-capital investment+net borrowing. — [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation)
- **Source principle:** EBITDA and accounting earnings are not free cash flow; omitting investment and working capital does not produce FCFF. — [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation)
- **Operational checklist:** Terminal TV[n]=CF[n+1]/(r-g) is discounted from n; use WACC for firm flows, equity cost for shareholder flows, and a debt/cash bridge without double-counting.

Exceptions and limits:

- A supplied-flow calculator does not automatically forecast future cash flows.
- Terminal multiples and perpetual-growth value are different assumptions.

Required data:

- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: dcf

Sources and attribution scope:

- [CFA Institute: Free Cash Flow Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/free-cash-flow-valuation): Matching firm/equity cash flows to the discount rate

### 5. Relative Valuation / Comparables Approach

ID: `ap_relative`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** This entry links to relative valuation without a duplicate analytical vote.
- **Operational checklist:** Define peer set, date and unsuitable-case exclusions.
- **Operational checklist:** Apply a compatible multiple to a same-period financial measure.
- **Operational checklist:** Show range, dispersion and discount/premium adjustment rationale.
- **Operational checklist:** Comparison estimates relative value rather than intrinsic value or trade success.
- **Operational checklist:** Retain peers, excluded cases/reasons and median/mean weighting; do not remove outliers after observing outcomes.

Exceptions and limits:

- Selecting peers after outcomes undermines testing.
- Assess risk/growth differences before adjusting multiples.

Required data:

- Peer data with consistent periods and accounting
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Peer data with consistent periods and accounting; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: multiples

Overlapping entry: `fa_relative`. This does not create another committee vote.

Sources and attribution scope:

- [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples): Consistent multiple numerator/denominator and suitable comparables

### 6. Asset-Based Valuation Approach

ID: `ap_asset_based`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** This links to asset-based valuation rather than a separate school.
- **Operational checklist:** Inventory assets, liabilities and off-balance-sheet claims with source/date per item.
- **Operational checklist:** Specify going-concern/liquidation and suitable market/replacement values.
- **Operational checklist:** Subtract liabilities, costs and taxes, then match the result to equity claims.
- **Operational checklist:** Stress haircuts and liquidation time; do not use book values without review.
- **Operational checklist:** Separate adjusted asset value from book value and expected sale price from a realizable sale within a declared horizon.

Exceptions and limits:

- Structurally valid imported amounts may still be stale estimates.
- Negative net value is not automatically an arithmetic error.

Required data:

- Asset/liability appraisals and liquidation costs
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Asset/liability appraisals and liquidation costs; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: nav

Overlapping entry: `fa_asset_based`. This does not create another committee vote.

Sources and attribution scope:

- [SEC: Beginners' Guide to Financial Statements](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide): Core financial statements; checklists are Quant Trading AI authored
- [CFA Institute: Equity Valuation — Concepts and Basic Tools](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-concepts-basic-tools): Valuation-model selection and estimated-value limits

### 7. Present Value Models

ID: `ap_present_value`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** A known-time flow is discounted by one plus the period rate raised to the period count.
- **Operational checklist:** Unequal times need year fractions and a documented day-count convention.
- **Operational checklist:** Match nominal/effective rate and compounding frequency to cash-flow times.
- **Operational checklist:** Separate expected/contractual flows and a single rate from a discount curve.
- **Operational checklist:** Sum flows after discounting; financing, currency and inflation belong to consistency assumptions.
- **Operational checklist:** For a fixed rate, PV=sum(CF[t]/(1+r)^t); require positive 1+r and explicit signed flows/times, keeping missing values distinct from zero.

Exceptions and limits:

- Correct discounting does not prove that cash flows will occur.
- Invalid periods/rates are rejected rather than producing fabricated values.

Required data:

- Local cash-flow forecasts and assumptions
- Consistent discount/growth rates, currency and frequency
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Local cash-flow forecasts and assumptions; Consistent discount/growth rates, currency and frequency; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: pv, bond

Sources and attribution scope:

- [CFA Institute: Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation): Dividend cash flows and terminal-growth condition
- [CFA Institute: Interest Rate Risk and Return](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/interest-rate-risk-and-return): Duration, reinvestment risk and holding horizon

### 8. Multiplier / Multiples Models

ID: `ap_multiples`

Principles and review checklist; neither exhaustive school coverage nor execution of every model is claimed.

Rules and review checklist:

- **Operational checklist:** This arithmetic application belongs to relative valuation and remains visible in the original list.
- **Operational checklist:** P/E uses per-share earnings; enterprise multiples use a compatible firm-wide measure.
- **Operational checklist:** Proposed value equals a documented financial measure times a documented selected multiple.
- **Operational checklist:** Use a separate debt/cash/claims/shares bridge when converting to per-share value.
- **Operational checklist:** Store multiple range and selection source; do not fabricate peers from chart prices.
- **Source principle:** Define EV from market equity, debt and relevant claims less eligible cash; do not substitute P/EBITDA for EV/EBITDA. — [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples)

Exceptions and limits:

- Negative measures can make conventional multiples uninterpretable.
- Numerator/denominator must refer to the same claimholders.

Required data:

- Peer data with consistent periods and accounting
- Local financial statements with period and availability time
- Issuer identity, instrument type, currency and rights

Rule application and review protocol — version 1.0.0

- Reference inputs: Peer data with consistent periods and accounting; Local financial statements with period and availability time; Issuer identity, instrument type, currency and rights. Each linked coded model uses its specific input contract.
- Confirmation: retain observation, availability and decision times; exclude data published or pivots confirmed after the decision.
- Rule parameters: retain value, units and source/model version; distinguish source formulas from local tolerances or assumptions.
- Invalidation: declare a testable falsifier and expiry before outcomes; retain unresolved rules and keep missing inputs distinct from zero.
- Learning: attribute outcomes to rule revision, instrument, timeframe and regime; keep failures and compare later periods after costs.
- Development: documented new revision, directional/invalidation tests and later review; reference storage issues no orders, raises no risk and never rewrites code automatically.

Current scope: Stored reference; verified local data and a separate numerical implementation are required before voting or execution. Local calculators evaluate explicit documented inputs; they do not collect financial facts or issue trade orders.

School-level data lists describe the broader reference. Each bounded model has its own input contract; a missing mandatory contract input yields DATA_MISSING and blocks its signal. Labeled proxies do not establish availability of original school data, and reference mapping does not grant execution eligibility automatically.

Available local calculators: multiples

Overlapping entry: `ap_relative`. This does not create another committee vote.

Sources and attribution scope:

- [CFA Institute: Market-Based Valuation — Price and Enterprise Value Multiples](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/market-based-valuation-price-enterprise-value-multiples): Consistent multiple numerator/denominator and suitable comparables


"""English rule contracts for legacy core models lacking structured specs.

These describe the implemented local algorithms, not canonical coverage of a
named school. Keep thresholds synchronized with strategies.py implementations.
"""

CORE_RULE_SPECS = {
    "dow_structure": {
        "rules_en": [
            "Use confirmed swing pivots only; classify bullish structure from the latest two higher highs and higher lows, bearish structure from two lower highs and lower lows.",
            "Trigger only on a fresh completed-bar close through the latest confirmed swing in the classified direction.",
            "The opposite latest swing is the structural invalidation reference; no full Dow theory breadth or volume confirmation is modeled.",
        ],
        "parameters": {"minimum_confirmed_highs": 2, "minimum_confirmed_lows": 2, "entry": "fresh_close_through_latest_swing"},
    },
    "engulfing": {
        "rules_en": [
            "Compare the two latest completed candle bodies; bullish requires a bearish prior body and bullish current body that covers the prior body, with the inverse for bearish.",
            "Require current real-body size to be at least 0.5 ATR; direction alone without a fresh engulfing trigger is not an entry.",
            "Reference invalidation to the outer low/high of the two-candle pair.",
        ],
        "parameters": {"minimum_body_atr": 0.5, "lookback_bars": 2},
    },
    "support_bounce": {
        "rules_en": [
            "Use the latest confirmed swing low/high as support/resistance; require the latest bar extreme to be within 0.25 ATR of that level.",
            "Bullish rejection requires close above support, a higher close than the prior bar, and lower wick greater than 60% of bar range; bearish is the inverse at resistance.",
            "A touch without the completed-bar rejection conditions does not trigger.",
        ],
        "parameters": {"level_tolerance_atr": 0.25, "rejection_wick_range_fraction": 0.6},
    },
    "classic_reversal_patterns": {
        "rules_en": [
            "Build causal alternating confirmed pivots; accept either a double top/bottom or a head-and-shoulders/inverse pattern under the fixed geometry checks in the linked source.",
            "Double patterns require height of at least 2 ATR, pivot separation of 4–50 bars, and peak/trough mismatch no greater than max(0.35 ATR, 10% of pattern height).",
            "Head-and-shoulders requires height at least 2 ATR, head prominence at least 0.75 ATR, shoulder mismatch at most max(0.5 ATR, 20% of height), neckline-end difference at most half the height, and time-width ratio at most 2.5.",
            "Trigger only on a fresh completed close through the fixed or projected neckline; target is the pattern height projected from the neckline.",
        ],
        "parameters": {"minimum_height_atr": 2, "double_pivot_spacing_bars": [4, 50], "max_shoulder_time_ratio": 2.5},
    },
    "geometric_triangle_breakout": {
        "rules_en": [
            "Fit least-squares lines to the latest three confirmed highs and lows; reject missing pivots or excessive residual above 0.35 ATR.",
            "Recognize symmetrical, ascending, or descending geometry with minimum slope 0.03 ATR per bar and flat-line tolerance 0.04 ATR per bar.",
            "Require 8–60 bars of formation, newest pivot no older than 15 bars, current height 30–80% of initial height, and all prior closes inside lines with 0.15 ATR tolerance.",
            "Trigger on a fresh completed close outside the converging boundary; target projects initial triangle height from breakout close.",
        ],
        "parameters": {"touches_per_boundary": 3, "residual_atr": 0.35, "formation_bars": [8, 60], "latest_pivot_age_bars": 15, "contraction_fraction": [0.3, 0.8]},
    },
    "breakout_retest": {
        "rules_en": [
            "Define the range from 20 completed bars before the breakout and retest bars.",
            "Require a completed breakout close beyond the range followed by the next completed bar retesting within 0.15 ATR and closing back beyond the broken boundary.",
            "Use the retest extreme and buffered range boundary as the invalidation structure.",
        ],
        "parameters": {"range_lookback": 20, "retest_tolerance_atr": 0.15, "confirmation_bars": 1},
    },
    "darvas_box": {
        "rules_en": [
            "Build a fixed 20-bar box from the preceding completed bars; the upper boundary is confirmed only when at least three subsequent bars fail to exceed the candidate top.",
            "Trigger on a fresh completed close through the upper boundary or lower box boundary.",
            "The opposite box boundary is the invalidation reference; this is a fixed Darvas-box variant.",
        ],
        "parameters": {"box_lookback": 20, "top_confirmation_bars": 3},
    },
    "ichimoku_cross": {
        "rules_en": [
            "Compute Tenkan midpoint over 9 bars and Kijun midpoint over 26 bars; require a fresh cross between the two on completed bars.",
            "Require close above both causal cloud spans for bullish, or below both for bearish; cloud is calculated from data 26 bars earlier using 9/26/52 periods.",
            "Chikou is deliberately excluded as a predictive input.",
        ],
        "parameters": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "cloud_lag_bars": 26},
    },
    "fib_retracement": {
        "rules_en": [
            "Select the latest confirmed alternating swing pair and require total swing span greater than 2 ATR.",
            "For an upward swing, require a touch of the 61.8% retracement within 0.1 ATR and a fresh close recrossing the 50% recovery level; invert for a downward swing.",
            "The prior swing origin is the invalidation reference; pivot confirmation is causal.",
        ],
        "parameters": {"retracement": 0.618, "recovery": 0.5, "level_tolerance_atr": 0.1, "minimum_swing_atr": 2},
    },
    "ema_cross": {
        "rules_en": [
            "Compute 12-period and 26-period EMAs over completed closes.",
            "Trigger only when the latest completed bar creates a fresh crossover; use the last five-bar low/high as the invalidation reference.",
        ],
        "parameters": {"fast_ema": 12, "slow_ema": 26, "stop_lookback": 5},
    },
    "rsi_rebound": {
        "rules_en": [
            "Compute the project's simple rolling RSI-14, not Wilder-smoothed RSI.",
            "Trigger bullish when RSI crosses back above 30, bearish when it crosses back below 70, using the two latest completed samples.",
            "Use the latest five-bar low/high as invalidation reference.",
        ],
        "parameters": {"rsi_period": 14, "lower_recross": 30, "upper_recross": 70, "method": "simple_rolling_gain_loss"},
    },
    "volatility_breakout": {
        "rules_en": [
            "Calculate 20-close Bollinger mean and population standard deviation from the prior sample, with bands at ±2 standard deviations.",
            "Require current sample standard deviation below 70% of the older 20-close standard deviation and a fresh close outside the corresponding band.",
        ],
        "parameters": {"band_period": 20, "band_deviations": 2, "squeeze_ratio_max": 0.7, "comparison_gap_bars": 20},
    },
    "zscore_reversion": {
        "rules_en": [
            "Estimate mean and standard deviation from the 40 closes preceding both trigger bars; require nonzero dispersion.",
            "Require the means of the first and last 10 training observations to differ by less than one training standard deviation.",
            "Trigger on a fresh recross inward through z-score −2 or +2 and use the pre-trigger sample mean as target when it lies in the trade direction.",
        ],
        "parameters": {"training_closes": 40, "entry_z": 2, "mean_slope_filter": "difference_of_10_bar_means_below_1_sd"},
    },
    "vwap_reclaim": {
        "rules_en": [
            "Use explicit anchor_time when supplied; otherwise use the current UTC-day boundary. Require data to cover the anchor and at least three completed bars after it.",
            "Weight bar typical price (H+L+C)/3 by real_volume only when every anchored bar has positive real volume; otherwise use positive tick_volume and label the result a proxy.",
            "Trigger on a fresh completed close reclaiming the updated weighted mean with matching candle direction.",
            "This is bar-level approximate VWAP, not trade-level VWAP.",
        ],
        "parameters": {"anchor": "explicit_or_UTC_day_boundary", "minimum_bars_after_anchor": 3, "fallback": "tick_volume_proxy"},
    },
    "interasset_confirmation": {
        "rules_en": [
            "Require an explicitly declared different partner symbol and at least 42 exactly time-aligned completed bar pairs; never infer a partner from the symbol name.",
            "Compute paired log-return correlation; require correlation at least 0.7 and partner's latest close-to-close move in the same direction.",
            "Trigger on a fresh breakout through the primary symbol's previous 20-bar high/low.",
            "This is a one-leg confirmation model, not a hedged pair strategy; current engine partner-data mapping may withhold the signal when unavailable.",
        ],
        "parameters": {"aligned_pairs_min": 42, "correlation_min": 0.7, "breakout_lookback": 20},
    },
    "harmonic_abcd": {
        "rules_en": [
            "Use the latest four confirmed alternating pivots to form the equal-leg AB=CD candidate.",
            "Require BC/AB between 0.382 and 0.886, CD/AB between 0.95 and 1.05, and CD/BC between 1.13 and 2.618.",
            "After D is confirmed two bars later, require a fresh break of the confirmation-bar extreme within the next 1–8 bars; D must remain intact and C must remain a valid target.",
            "This single equal-leg variant does not implement the full harmonic family.",
        ],
        "parameters": {"bc_ab": [0.382, 0.886], "cd_ab": [0.95, 1.05], "cd_bc": [1.13, 2.618], "pivot_confirmation_bars": 2, "break_window_bars": [1, 8]},
    },
    "elliott_candidate": {
        "rules_en": [
            "Take the latest three confirmed alternating pivots as a local wave-1, wave-2 hypothesis.",
            "Require wave 1 at least 2 ATR, wave-2 retracement between 0.382 and 0.786, an intact retracement extreme, and a fresh close through the wave-1 extreme.",
            "Trigger age must be 1–16 bars after pivot confirmation; nested degree counts and full Elliott wave structure are not modeled.",
        ],
        "parameters": {"minimum_impulse_atr": 2, "retracement": [0.382, 0.786], "trigger_age_bars": [1, 16]},
    },
    "wyckoff_spring": {
        "rules_en": [
            "Search recent candidate spring/upthrust bars against a preceding 40-bar trading range; range height must be at least 3 ATR and its endpoint drift at most 25% of range height.",
            "Require positive tick counts, a sweep and close back inside the range, subsequent displacement of at least 1 ATR, no later deep range breach, and a retest in the outer 0.25 ATR zone.",
            "Require current tick count no greater than the spring bar's count; use the opposite spring extreme as invalidation and range midpoint as target.",
            "This is a local range/spring proxy, not a full Wyckoff phase or institutional-intent model.",
        ],
        "parameters": {"range_bars": 40, "minimum_range_atr": 3, "minimum_displacement_atr": 1, "retest_zone_atr": 0.25},
    },
    "smc_ict_proxy": {
        "rules_en": [
            "Find a qualifying displacement gap and its first untouched return, no older than the configured 20-bar zone age.",
            "Require a prior 10-bar liquidity sweep at the gap formation before retaining the candidate.",
            "This local OHLC sequence does not observe institutional orders, a full ICT dealing range, session models, or every ICT interpretation.",
        ],
        "parameters": {"prior_sweep_lookback": 10, "zone_max_age_bars": 20, "gap_body_atr": 1, "minimum_gap_atr": 0.1},
    },
    "supply_demand_proxy": {
        "rules_en": [
            "Identify the first untouched return to a locally detected compact base after a displacement of at least 1.5 ATR; cap zone age at 20 bars.",
            "Require a directional close and a 20-period prior EMA filter in the same direction.",
            "This does not observe resting supply/demand orders or order-book imbalance.",
        ],
        "parameters": {"zone_max_age_bars": 20, "base_width_atr_max": 1, "displacement_atr_min": 1.5, "ema_filter": 20},
    },
    "smt_proxy": {
        "rules_en": [
            "Require an explicitly supplied different partner, 42 or more exactly aligned bars, and paired-return correlation of at least 0.7.",
            "Trigger when the primary instrument sweeps and closes back through a prior 20-bar extreme while the partner does not make the matching extreme.",
            "This is a local two-instrument divergence rule; it is not a full SMT/ICT model and needs explicit symbol pairing.",
        ],
        "parameters": {"aligned_pairs_min": 42, "correlation_min": 0.7, "sweep_lookback": 20},
    },
    "seasonality": {
        "rules_en": [
            "Support declared currency pairs only; collect at least three prior complete same-calendar-month daily samples, each with at least 15 bars spanning days 1–24 or wider.",
            "Compute historical monthly returns, mean, sample standard deviation, t-like score, and directional agreement; reject discontinuities above 50%.",
            "Require absolute score at least 2 and at least two-thirds directional agreement, then a fresh 20-bar range breakout in that direction.",
            "This small raw-broker sample does not establish stable seasonal edge or adjusted returns.",
        ],
        "parameters": {"minimum_year_samples": 3, "minimum_daily_bars_per_month": 15, "minimum_agreement": 0.6666667, "minimum_abs_score": 2, "breakout_lookback": 20},
    },
    "gann": {
        "rules_en": [
            "Anchor a volatility-normalized square-root grid to the latest confirmed alternating pivot; shift the square-root coordinate by +0.25 from a low or −0.25 from a high.",
            "Require positive ATR units, intact anchor, 1–32 bars after pivot confirmation, and a fresh completed close across the calculated level.",
            "This is a project-specific price grid, not full Gann time/price theory.",
        ],
        "parameters": {"grid_shift": 0.25, "trigger_age_bars": [1, 32], "unit": "ATR_at_anchor"},
    },
    "order_flow": {
        "rules_en": [
            "Use positive tick counts from the latest 21 completed bars and close-location pressure (2C−H−L)/(H−L).",
            "Require current tick count at least 1.2 times the median of the prior 20 bars, pressure crossing +0.35/-0.35, and a fresh close through the prior five-bar extreme.",
            "This is tick activity plus candle-location proxy only; it is not signed trade volume, exchange tape, or true order flow.",
        ],
        "parameters": {"activity_median_multiple": 1.2, "pressure_cross": 0.35, "breakout_lookback": 5, "tick_sample_bars": 21},
    },
    "four_school_confluence": {
        "rules_en": [
            "Compute a local ICT chain (liquidity sweep, BOS, displacement gap and first return), plus momentum, Elliott geometry, timing, and volume-profile context when actual data is provided.",
            "When actual profile is unavailable, the documented route requires local timing plus available momentum and Elliott context; reject missing or opposing required components.",
            "Require a pre-existing unswept opposing liquidity target and gross reward/risk at least 2:1; a fresh broker quote is required for execution readiness.",
            "The current registry analyzer calls this study without a live quote or supplied profile and explicitly returns advisory WAIT; it must not be treated as an executable signal.",
        ],
        "parameters": {"minimum_history_bars": 40, "minimum_gross_rr": 2, "profile_source": "actual_profile_required_for_profile_route", "current_registry_mode": "advisory_only_no_quote"},
    },
}

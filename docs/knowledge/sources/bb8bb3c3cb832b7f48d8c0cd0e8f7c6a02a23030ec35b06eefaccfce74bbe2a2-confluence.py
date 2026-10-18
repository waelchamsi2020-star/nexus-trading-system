"""Causal, bounded four-school confluence; pure research, never broker I/O.

``evaluate`` consumes completed bars and, for executable eligibility, an actual
quote. It cannot prove a win probability, institutional participation, original
Gann theory, a complete Elliott count, or completion of a daily profit target.

Optional profile schema is deliberately narrow: ``kind=TRADE_VOLUME_AT_PRICE``,
``source_type=EXECUTED_TRANSACTIONS``, ``provenance_verified=True`` (set only by a
trusted adapter), nonempty source/venue, symbol, units, complete=True,
coverage>=0.99, window_start/window_end UTC seconds, and bins of price/volume.
Tick counts, bar-volume redistribution and quoted market depth are rejected.
The validator checks the declaration; only the supplying adapter can establish
provenance. No current OHLC-only broker adapter is upgraded by this module.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING

from .strategies import DataError, atr, causal_pivots, validate_bars
from .timeframes import PERIODS, bar_close_time


_DEFINITION = {
    "id": "four_school_confluence", "version": "1.0.0",
    "name_en": "Four-school structural confluence",
    "name_ar": "تقاطع أربع مدارس مع وقف هيكلي",
    "scope_en": "Bounded computational house definitions; no win-probability or daily-profit guarantee.",
    "scope_ar": "تعريفات حسابية محلية محددة؛ لا تثبت احتمالية نجاح ولا تضمن الربح اليومي.",
    "rules": [
        {"id": "ict_chain", "en": "Confirmed strict five-bar liquidity pivot, sweep/reclaim, later fresh structure break by displacement, three-bar gap, first untouched return; protected sweep pivot stays intact.",
         "ar": "محور سيولة مؤكد بخمس شموع، ثم سحب واستعادة، ثم كسر هيكل لاحق بإزاحة وفجوة ثلاث شموع، ثم أول عودة دون لمس سابق مع سلامة محور السحب المحمي."},
        {"id": "primary", "en": "ICT plus an actual transaction-volume POC inside the gap overrides only time, momentum and bounded Elliott opposition.",
         "ar": "توافق السيولة مع نقطة التحكم لحجم صفقات فعلي داخل الفجوة له الأولوية فقط على تعارض الزمن والزخم ونموذج إليوت المحدد."},
        {"id": "fallback", "en": "Without a qualifying POC, require an 8/16/32/64 +/-1-bar timing window from the latest same-direction confirmed pivot, with available non-opposing momentum and Elliott context.",
         "ar": "عند غياب نقطة تحكم مؤهلة يلزم توقيت ٨ أو ١٦ أو ٣٢ أو ٦٤ شمعة بسماح شمعة من آخر محور مؤكد مناسب، مع توفر سياق الزخم وإليوت وعدم معارضتهما."},
        {"id": "structural_rr", "en": "Stop is one price tick beyond the protected sweep pivot; target is nearest previously confirmed, still-unswept opposite liquidity; exact quote reward must be at least twice quote risk. Never move target to manufacture eligibility.",
         "ar": "الوقف خلف محور السحب المحمي بمقدار خطوة سعر، والهدف أقرب سيولة مقابلة مؤكدة سابقا لم تسحب؛ العائد من سعر التنفيذ لا يقل حسابيا عن ضعفي المخاطرة دون تحريك الهدف لتأهيل الصفقة."},
        {"id": "momentum", "en": "Simple rolling RSI14 at two confirmed same-kind pivots; price divergence needs at least two RSI points. Neutral is an evaluated context, not an invented divergence.",
         "ar": "مؤشر القوة النسبية ١٤ بمتوسط بسيط عند محورين مؤكدين من النوع نفسه؛ الانحراف يلزم فارق نقطتين على الأقل. الحياد سياق مفحوص وليس انحرافا مختلقا."},
        {"id": "elliott", "en": "Four confirmed alternating pivots test a bounded ABC price geometry only, not nesting, alternation, complete Elliott interpretation or wave forecasting.",
         "ar": "أربعة محاور مؤكدة متعاقبة تفحص هندسة تصحيح سعري محددة فقط؛ دون ادعاء اكتمال درجات إليوت والتعاقب أو توقع الموجات."},
    ],
    "parameters": {"pivot_left": 2, "pivot_right": 2, "max_sweep_age": 32,
                   "max_gap_age": 16, "displacement_atr": 1.25,
                   "cycles": [8, 16, 32, 64], "cycle_tolerance": 1,
                   "profile_min_coverage": .99, "value_area_fraction": .70,
                   "rsi_period": 14, "rsi_divergence_points": 2,
                   "min_reward_risk": 2, "max_quote_age_seconds": 60},
    "sources": [
        "https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals",
        "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi",
        "https://www.elliottwave.com/waveopedia/zigzags/",
    ],
    "profile_schema": {
        "kind": "TRADE_VOLUME_AT_PRICE", "source_type": "EXECUTED_TRANSACTIONS",
        "provenance_verified": True, "source": "trusted adapter identifier",
        "venue": "actual venue or broker", "symbol": "same instrument",
        "units": ["contracts", "shares", "base_asset"], "complete": True,
        "coverage": "0.99..1.0", "window_start": "UTC seconds",
        "window_end": "UTC seconds <= analysis time",
        "bins": [{"price": "positive price aligned to tick", "volume": "positive executed volume"}],
    },
    "timing_definition": "HOUSE_DEFINITION_NOT_ORIGINAL_GANN",
    "elliott_definition": "BOUNDED_ABC_GEOMETRY_NOT_COMPLETE_ELLIOTT",
    "volume_scope": "ACTUAL_TRANSACTION_VOLUME_ONLY_NO_INSTITUTIONAL_ATTRIBUTION",
    "execution_scope": "DEMO_ONLY_ENFORCED_BY_CALLER_WITH_BROKER_NEWS_RISK_AND_NET_RR_GATES",
}
_DEFINITION_JSON = json.dumps(_DEFINITION, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
PROTOCOL_REVISION = hashlib.sha256(_DEFINITION_JSON.encode("utf-8")).hexdigest()
# A convenient public value; evaluation always uses the pinned canonical JSON,
# so accidental mutation of this display copy cannot alter active definitions.
PROTOCOL = json.loads(_DEFINITION_JSON)


def definition() -> dict:
    return {**json.loads(_DEFINITION_JSON), "revision": PROTOCOL_REVISION}


_MESSAGES = {
    "INVALID_DATA": ("Invalid completed-bar, tick or analysis data.", "بيانات الشموع المكتملة أو خطوة السعر أو وقت التحليل غير صالحة."),
    "INSUFFICIENT_HISTORY": ("At least forty completed bars are required.", "يلزم أربعون شمعة مكتملة على الأقل."),
    "ICT_CHAIN_INCOMPLETE": ("No fresh linked sweep, structure break, gap and first return.", "لم يكتمل تسلسل حديث مترابط لسحب السيولة وكسر الهيكل والفجوة وأول عودة."),
    "ICT_OPPOSITION": ("Simultaneous opposing ICT setups are not resolved by other schools.", "إعدادا سيولة متعارضان؛ لا تحسمهما المدارس الأخرى."),
    "PROFILE_MISSING": ("Genuine transaction volume at price is unavailable; OHLC and tick counts cannot supply it.", "حجم الصفقات الفعلي عند السعر غير متاح؛ الشموع وعدد التكات لا يوفرانه."),
    "PROFILE_INVALID": ("Transaction profile provenance, coverage, window or bins are invalid.", "مصدر ملف حجم الصفقات أو تغطيته أو نافذته أو مستوياته غير صالح."),
    "POC_OUTSIDE_ZONE": ("The genuine profile POC does not coincide with the ICT entry gap.", "نقطة التحكم للحجم الفعلي لا تقع داخل فجوة دخول السيولة."),
    "TIMING_NOT_ALIGNED": ("No declared house timing window agrees with this setup.", "لا توجد نافذة توقيت محلية معلنة متوافقة مع الإعداد."),
    "MOMENTUM_UNAVAILABLE": ("Confirmed RSI pivot context is unavailable.", "سياق القوة النسبية عند محاور مؤكدة غير متاح."),
    "ELLIOTT_UNAVAILABLE": ("Four confirmed alternating pivots are unavailable for bounded corrective context.", "أربعة محاور مؤكدة متعاقبة غير متاحة لسياق التصحيح المحدد."),
    "MOMENTUM_OPPOSES": ("Confirmed RSI divergence opposes the setup.", "انحراف القوة النسبية المؤكد يعارض الإعداد."),
    "ELLIOTT_OPPOSES": ("The bounded corrective geometry opposes the setup.", "هندسة التصحيح المحددة تعارض الإعداد."),
    "NO_UNSWEPT_TARGET": ("No previously confirmed, unswept opposing liquidity target exists.", "لا يوجد هدف سيولة مقابل مؤكد سابقا ولم يسحب."),
    "QUOTE_INVALID": ("The executable quote is invalid, future or more than sixty seconds old.", "سعر التنفيذ غير صالح أو مستقبلي أو أقدم من ستين ثانية."),
    "QUOTE_OUTSIDE_ZONE": ("Executable quote is outside the original untouched entry gap.", "سعر التنفيذ خارج فجوة الدخول الأصلية."),
    "STRUCTURE_INVALID": ("The protected structure no longer supports a positive stop distance.", "الهيكل المحمي لا يدعم مسافة وقف موجبة."),
    "RR_BELOW_TWO": ("Nearest known liquidity offers less than 1:2 at the actual quote.", "أقرب سيولة معلومة توفر عائدا دون ١:٢ من سعر التنفيذ."),
    "QUOTE_REQUIRED": ("Research confluence exists; an actual validated quote is still required.", "التقاطع البحثي موجود؛ ما زال يلزم سعر تنفيذ فعلي مفحوص."),
}


def _reason(code: str) -> dict:
    en, ar = _MESSAGES[code]
    return {"code": code, "en": en, "ar": ar}


def _finite(value, *, positive=False) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and (value > 0 if positive else True))


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _row(status="WAIT", available=True, direction="NEUTRAL", evidence=None, code=None):
    result = {"status": status, "available": available, "direction": direction,
              "evidence": evidence or {}}
    if code:
        result["reason"] = _reason(code)
    return result


def _alternating(pivots):
    """Discard outside bars with two pivot kinds; collapse consecutive extremes."""
    indices = {}
    for p in pivots:
        indices.setdefault(p["index"], []).append(p)
    result = []
    for index in sorted(indices):
        if len(indices[index]) != 1:
            continue
        p = indices[index][0]
        if result and result[-1]["kind"] == p["kind"]:
            if ((p["kind"] == "HIGH" and p["price"] > result[-1]["price"])
                    or (p["kind"] == "LOW" and p["price"] < result[-1]["price"])):
                result[-1] = p
        else:
            result.append(p)
    return result


def _rsi(values, period=14):
    out = [None] * len(values)
    for i in range(period, len(values)):
        changes = [values[j] - values[j - 1] for j in range(i-period+1, i+1)]
        gains = math.fsum(max(v, 0) for v in changes)
        losses = math.fsum(max(-v, 0) for v in changes)
        out[i] = 50. if gains + losses == 0 else 100. * gains / (gains + losses)
    return out


def _momentum(bars, pivots, tick):
    values = _rsi([b["close"] for b in bars])
    evidence = {"definition": "SIMPLE_ROLLING_RSI14_CONFIRMED_PIVOT_DIVERGENCE",
                "threshold_points": 2, "pairs": []}
    signals = []
    for kind, side in (("LOW", "LONG"), ("HIGH", "SHORT")):
        chosen = [p for p in pivots if p["kind"] == kind and p["index"] + 2 < len(bars)-1
                  and values[p["index"]] is not None]
        if len(chosen) < 2:
            return _row("DATA_MISSING", False, evidence=evidence, code="MOMENTUM_UNAVAILABLE")
        a, b = chosen[-2:]
        price_delta = b["price"] - a["price"]
        rsi_delta = values[b["index"]] - values[a["index"]]
        divergence = ((price_delta <= -tick and rsi_delta >= 2) if side == "LONG"
                      else (price_delta >= tick and rsi_delta <= -2))
        evidence["pairs"].append({"kind": kind, "first": copy.deepcopy(a), "second": copy.deepcopy(b),
                                  "first_rsi": values[a["index"]], "second_rsi": values[b["index"]],
                                  "divergence": divergence})
        if divergence:
            signals.append((b["index"], side))
    direction = max(signals)[1] if signals else "NEUTRAL"
    if len(signals) == 2 and signals[0][0] == signals[1][0]:
        direction = "CONFLICT"
    return _row("CONFIRMED" if signals else "EVALUATED_NEUTRAL", direction=direction, evidence=evidence)


def _elliott(bars, pivots):
    confirmed = [p for p in pivots if p["index"] + 2 < len(bars)-1]
    p = _alternating(confirmed)[-4:]
    evidence = {"definition": "BOUNDED_ABC_GEOMETRY_NOT_COMPLETE_ELLIOTT", "pivots": copy.deepcopy(p),
                "b_over_a_bounds": [.382, .786], "c_over_a_bounds": [.618, 1.618],
                "unverified": ["nested 5-3-5 subwaves", "wave degree", "alternation", "all corrective forms"]}
    if len(p) < 4:
        return _row("DATA_MISSING", False, evidence=evidence, code="ELLIOTT_UNAVAILABLE")
    a, b, c, d = p
    bullish = a["kind"] == "HIGH"
    sign = -1 if bullish else 1
    length_a = sign * (b["price"] - a["price"])
    length_b = -sign * (c["price"] - b["price"])
    length_c = sign * (d["price"] - c["price"])
    geometry = (length_a > 0 and length_b > 0 and length_c > 0
                and .382 <= length_b / length_a <= .786
                and .618 <= length_c / length_a <= 1.618
                and (c["price"] < a["price"] and d["price"] < b["price"] if bullish
                     else c["price"] > a["price"] and d["price"] > b["price"]))
    if length_a > 0:
        evidence.update(b_over_a=length_b / length_a, c_over_a=length_c / length_a)
    evidence["geometry"] = geometry
    # Geometry is contextual, not a fresh entry signal or a unique wave count.
    intact = all(x["low"] > d["price"] if bullish else x["high"] < d["price"]
                 for x in bars[d["index"]+1:])
    evidence["terminal_pivot_intact"] = intact
    direction = ("LONG" if bullish else "SHORT") if geometry and intact else "NEUTRAL"
    return _row("CONTEXT_CONFIRMED" if direction != "NEUTRAL" else "EVALUATED_NEUTRAL",
                direction=direction, evidence=evidence)


def _timing(bars, pivots, side):
    kind = "LOW" if side == "LONG" else "HIGH"
    available = [p for p in pivots if p["kind"] == kind and p["index"] + 2 < len(bars)-1]
    evidence = {"definition": "HOUSE_DEFINITION_NOT_ORIGINAL_GANN", "cycles": [8, 16, 32, 64],
                "tolerance_bars": 1, "bar_elapsed_is_not_forecast": True}
    if not available:
        return _row("DATA_MISSING", False, evidence=evidence, code="TIMING_NOT_ALIGNED")
    anchor = available[-1]
    age = len(bars)-1-anchor["index"]
    cycle = next((v for v in (8, 16, 32, 64) if abs(age-v) <= 1), None)
    evidence.update(anchor=copy.deepcopy(anchor), elapsed_bars=age, matching_cycle=cycle)
    return _row("CONFIRMED" if cycle is not None else "WAIT", direction=side if cycle else "NEUTRAL",
                evidence=evidence, code=None if cycle else "TIMING_NOT_ALIGNED")


def _target(bars, pivots, side, sweep_index, entry):
    """Only liquidity known before sweep, unhit after its confirmation."""
    kind = "HIGH" if side == "LONG" else "LOW"
    candidates = []
    for p in pivots:
        if p["kind"] != kind or p["index"] + 2 >= sweep_index:
            continue
        if not (p["price"] > entry if side == "LONG" else p["price"] < entry):
            continue
        if any(b["high"] >= p["price"] if side == "LONG" else b["low"] <= p["price"]
               for b in bars[p["index"]+3:]):
            continue
        candidates.append(p)
    return min(candidates, key=lambda p: abs(p["price"]-entry)) if candidates else None


def _ict(bars, pivots, tick, timeframe):
    n = len(bars)
    latest = bars[-1]
    setups = []
    for sweep_index in range(max(4, n-1-32), n-4):
        sweep = bars[sweep_index]
        known = [p for p in pivots if p["index"]+2 < sweep_index]
        # Ambiguous outside-bar pivots never become liquidity/structure anchors.
        counts = {}
        for p in known:
            counts[p["index"]] = counts.get(p["index"], 0)+1
        known = [p for p in known if counts[p["index"]] == 1]
        for side, pool_kind, bos_kind in (("LONG", "LOW", "HIGH"), ("SHORT", "HIGH", "LOW")):
            pools = [p for p in known if p["kind"] == pool_kind]
            levels = [p for p in known if p["kind"] == bos_kind]
            if not pools or not levels:
                continue
            pool, level = pools[-1], levels[-1]
            # The first sweep of a known pool, not a reused depleted level.
            if any(b["low"] <= pool["price"] if side == "LONG" else b["high"] >= pool["price"]
                   for b in bars[pool["index"]+3:sweep_index]):
                continue
            crossed = (sweep["low"] <= pool["price"]-tick and sweep["close"] > pool["price"]
                       if side == "LONG" else sweep["high"] >= pool["price"]+tick and sweep["close"] < pool["price"])
            protected = next((p for p in pivots if p["index"] == sweep_index and p["kind"] == pool_kind), None)
            if (not crossed or protected is None or sweep_index+2 >= n-1
                    or sum(p["index"] == sweep_index for p in pivots) != 1):
                continue
            if any(b["low"] <= protected["price"] if side == "LONG" else b["high"] >= protected["price"]
                   for b in bars[sweep_index+1:]):
                continue
            # Opposite side was a live protected swing at the time of sweep.
            if any(b["close"] > level["price"] if side == "LONG" else b["close"] < level["price"]
                   for b in bars[level["index"]+3:sweep_index+1]):
                continue
            for bos_index in range(sweep_index+1, n-2):
                middle = bars[bos_index]
                previous = bars[bos_index-1]
                right = bars[bos_index+1]
                if bos_index+1 >= n-1 or n-1-(bos_index+1) > 16:
                    continue
                fresh_bos = (previous["close"] <= level["price"] < middle["close"] if side == "LONG"
                             else previous["close"] >= level["price"] > middle["close"])
                previously_broken = any(x["close"] > level["price"] if side == "LONG" else x["close"] < level["price"]
                                        for x in bars[sweep_index+1:bos_index])
                prior_atr = atr(bars[:bos_index])
                body = middle["close"]-middle["open"]
                displaced = prior_atr > 0 and (body if side == "LONG" else -body) >= 1.25*prior_atr
                lower, upper = (previous["high"], right["low"]) if side == "LONG" else (right["high"], previous["low"])
                if not fresh_bos or previously_broken or not displaced or upper-lower < tick:
                    continue
                between = bars[bos_index+2:-1]
                touched = any(b["low"] <= upper and b["high"] >= lower for b in between)
                invalidated = any(b["close"] < lower if side == "LONG" else b["close"] > upper
                                  for b in bars[bos_index+2:])
                returned = latest["low"] <= upper and latest["high"] >= lower
                held = (lower <= latest["close"] <= upper and latest["close"] > latest["open"]
                        if side == "LONG" else lower <= latest["close"] <= upper and latest["close"] < latest["open"])
                if touched or invalidated or not returned or not held:
                    continue
                evidence = {"liquidity_pool": copy.deepcopy(pool), "protected_sweep": copy.deepcopy(protected),
                            "sweep_index": sweep_index, "sweep_time": sweep["time"],
                            "bos_reference": copy.deepcopy(level), "bos_index": bos_index,
                            "bos_time": middle["time"], "displacement_body": abs(body), "prior_atr": prior_atr,
                            "gap_lower": lower, "gap_upper": upper, "gap_completed_at": bar_close_time(right["time"], timeframe),
                            "gap_age_bars": n-1-(bos_index+1), "return_index": n-1,
                            "return_time": latest["time"], "first_untouched_return": True,
                            "protected_structure_intact": True,
                            "institutional_intent_asserted": False}
                setups.append({"side": side, "entry_zone": [lower, upper], "evidence": evidence})
                break
    # Latest qualified causal chain wins within one direction; opposing chains
    # remain a conflict instead of a score tie-break or a forced trade.
    if not setups:
        return _row("WAIT", code="ICT_CHAIN_INCOMPLETE"), None
    if len({s["side"] for s in setups}) > 1:
        return _row("CONFLICT", direction="CONFLICT", evidence={"setups": setups}, code="ICT_OPPOSITION"), None
    setup = max(setups, key=lambda s: (s["evidence"]["sweep_index"], s["evidence"]["bos_index"]))
    return _row("CONFIRMED", direction=setup["side"], evidence=copy.deepcopy(setup["evidence"])), setup


def _profile(profile, symbol, bars, as_of, tick, setup, timeframe):
    if profile is None:
        return _row("DATA_MISSING", False, code="PROFILE_MISSING")
    invalid = _row("DATA_ERROR", False, code="PROFILE_INVALID")
    if not isinstance(profile, dict):
        return invalid
    if (profile.get("kind") != "TRADE_VOLUME_AT_PRICE" or profile.get("source_type") != "EXECUTED_TRANSACTIONS"
            or profile.get("provenance_verified") is not True or profile.get("complete") is not True
            or profile.get("symbol") != symbol or profile.get("units") not in ("contracts", "shares", "base_asset")
            or not isinstance(profile.get("source"), str) or not profile["source"].strip()
            or not isinstance(profile.get("venue"), str) or not profile["venue"].strip()
            or not _finite(profile.get("coverage")) or not .99 <= profile["coverage"] <= 1
            or not _finite(profile.get("window_start")) or not _finite(profile.get("window_end"))):
        return invalid
    start, end = profile["window_start"], profile["window_end"]
    if (not 0 <= start < end <= as_of or start > setup["evidence"]["sweep_time"]
            or end < setup["evidence"]["gap_completed_at"]
            or bar_close_time(bars[-1]["time"], timeframe)-end > PERIODS[timeframe]*2):
        return invalid
    bins = profile.get("bins")
    if not isinstance(bins, list) or not 2 <= len(bins) <= 100000:
        return invalid
    clean = []
    last = None
    for b in bins:
        if (not isinstance(b, dict) or not _finite(b.get("price"), positive=True)
                or not _finite(b.get("volume"), positive=True)
                or (last is not None and b["price"] <= last)):
            return invalid
        scale = b["price"] / tick
        if not math.isfinite(scale) or abs(scale-round(scale)) > 1e-6:
            return invalid
        last = b["price"]
        clean.append({"price": b["price"], "volume": b["volume"]})
    try:
        total = math.fsum(b["volume"] for b in clean)
    except (OverflowError, ValueError):
        return invalid
    if not math.isfinite(total) or total <= 0:
        return invalid
    # A tied maximum is ambiguous; no arbitrary bin becomes an alleged POC.
    maximum = max(b["volume"] for b in clean)
    peaks = [i for i, b in enumerate(clean) if b["volume"] == maximum]
    if len(peaks) != 1:
        return invalid
    poc_index = peaks[0]
    left = right = poc_index
    covered = maximum
    while covered < .70*total and (left > 0 or right < len(clean)-1):
        lv = clean[left-1]["volume"] if left > 0 else -1
        rv = clean[right+1]["volume"] if right < len(clean)-1 else -1
        if lv >= rv:
            left -= 1
            covered += clean[left]["volume"]
        else:
            right += 1
            covered += clean[right]["volume"]
    lower, upper = setup["entry_zone"]
    poc = clean[poc_index]["price"]
    aligned = lower <= poc <= upper
    evidence = {"source": profile["source"], "venue": profile["venue"], "units": profile["units"],
                "window_start": start, "window_end": end, "coverage": profile["coverage"],
                "poc": poc, "value_area_low": clean[left]["price"], "value_area_high": clean[right]["price"],
                "value_area_fraction_actual": covered/total, "total_executed_volume": total,
                "profile_hash": _hash(profile), "institutional_identity_asserted": False,
                "adapter_provenance_required": True, "poc_inside_ict_zone": aligned}
    return _row("CONFIRMED" if aligned else "WAIT", direction=setup["side"] if aligned else "NEUTRAL",
                evidence=evidence, code=None if aligned else "POC_OUTSIDE_ZONE")


def _snap(value, tick, upward=False):
    v, t = Decimal(str(value)), Decimal(str(tick))
    return (v/t).to_integral_value(rounding=ROUND_CEILING if upward else ROUND_FLOOR)*t


def evaluate(symbol, tf, bars, as_of, tick_size, profile=None, *, quote=None) -> dict:
    """Return inspectable matrix and an eligible candidate, without side effects.

    ``quote`` is {bid, ask, time}, with current UTC seconds. Without it the
    completed close is explicitly a research reference and execution_ready is
    false. The caller still enforces broker, news, portfolio, size and net-cost
    reward/risk restrictions; matrix eligibility cannot bypass those gates.
    """
    matrix = {"passed": False, "route": None, "ict": _row(),
              "volume_profile": _row("DATA_MISSING", False, code="PROFILE_MISSING"),
              "time": _row(), "momentum": _row(), "elliott": _row()}
    output = {"protocol_id": "four_school_confluence", "protocol_revision": PROTOCOL_REVISION,
              "symbol": symbol, "timeframe": tf, "status": "WAIT", "execution_ready": False,
              "matrix": matrix, "candidate": None, "reason_codes": [], "reasons": []}

    def finish(codes, status="WAIT"):
        output["status"] = status
        output["reason_codes"] = list(dict.fromkeys(codes))
        output["reasons"] = [_reason(code) for code in output["reason_codes"]]
        return output

    try:
        if not isinstance(symbol, str) or not symbol.strip() or not _finite(tick_size, positive=True):
            return finish(["INVALID_DATA"], "DATA_ERROR")
        data = validate_bars(bars, tf, as_of)
        if len(data) < 40:
            return finish(["INSUFFICIENT_HISTORY"], "DATA_MISSING")
        largest_price = max(b["high"] for b in data)
        if largest_price+tick_size == largest_price or largest_price-tick_size == largest_price:
            return finish(["INVALID_DATA"], "DATA_ERROR")
        pivots = causal_pivots(data, as_of=as_of, timeframe=tf)
        matrix["momentum"] = _momentum(data, pivots, tick_size)
        matrix["elliott"] = _elliott(data, pivots)
        matrix["ict"], setup = _ict(data, pivots, tick_size, tf)
        output["data_time"] = bar_close_time(data[-1]["time"], tf)
        output["input_snapshot_hash"] = _hash([{key: b[key] for key in ("time", "open", "high", "low", "close")} for b in data])
        if setup is None:
            return finish(["ICT_OPPOSITION" if matrix["ict"]["status"] == "CONFLICT" else "ICT_CHAIN_INCOMPLETE"])
        side = setup["side"]
        matrix["time"] = _timing(data, pivots, side)
        matrix["volume_profile"] = _profile(profile, symbol, data, as_of, tick_size, setup, tf)
        primary = matrix["volume_profile"]["status"] == "CONFIRMED"
        blockers = []
        if primary:
            matrix["route"] = "ICT_PLUS_ACTUAL_POC"
            matrix["overridden_context"] = [name for name in ("time", "momentum", "elliott")
                                            if not matrix[name]["available"] or matrix[name]["direction"] not in (side, "NEUTRAL")
                                            or (name == "time" and matrix[name]["status"] != "CONFIRMED")]
        else:
            matrix["route"] = "ICT_PLUS_HOUSE_TIMING"
            if matrix["time"]["status"] != "CONFIRMED":
                blockers.append("TIMING_NOT_ALIGNED")
            for name, unavailable, opposed in (("momentum", "MOMENTUM_UNAVAILABLE", "MOMENTUM_OPPOSES"),
                                               ("elliott", "ELLIOTT_UNAVAILABLE", "ELLIOTT_OPPOSES")):
                if not matrix[name]["available"]:
                    blockers.append(unavailable)
                elif matrix[name]["direction"] not in (side, "NEUTRAL"):
                    blockers.append(opposed)
        if blockers:
            return finish(blockers)
        quote_used = quote is not None
        if quote_used:
            if (not isinstance(quote, dict) or not _finite(quote.get("bid"), positive=True)
                    or not _finite(quote.get("ask"), positive=True) or quote["ask"] < quote["bid"]
                    or not _finite(quote.get("time")) or not 0 <= as_of-quote["time"] <= 60):
                return finish(["QUOTE_INVALID"], "DATA_ERROR")
            entry = quote["ask"] if side == "LONG" else quote["bid"]
        else:
            entry = data[-1]["close"]
        lower, upper = setup["entry_zone"]
        if not lower <= entry <= upper:
            return finish(["QUOTE_OUTSIDE_ZONE"])
        protected = setup["evidence"]["protected_sweep"]
        stop_decimal = _snap(protected["price"], tick_size, upward=side == "SHORT")
        stop_decimal += Decimal(str(tick_size)) * (-1 if side == "LONG" else 1)
        target_pivot = _target(data, pivots, side, setup["evidence"]["sweep_index"], entry)
        if target_pivot is None:
            return finish(["NO_UNSWEPT_TARGET"])
        target_decimal = _snap(target_pivot["price"], tick_size, upward=side == "SHORT")
        entry_decimal = Decimal(str(entry))
        risk = (entry_decimal-stop_decimal) if side == "LONG" else (stop_decimal-entry_decimal)
        reward = (target_decimal-entry_decimal) if side == "LONG" else (entry_decimal-target_decimal)
        if stop_decimal <= 0 or risk <= 0 or reward <= 0:
            return finish(["STRUCTURE_INVALID"])
        if reward < 2*risk:
            return finish(["RR_BELOW_TWO"])
        with localcontext() as context:
            context.prec = 40
            rr = reward/risk
        formation = {"symbol": symbol, "timeframe": tf, "side": side, "protocol_revision": PROTOCOL_REVISION,
                     "pool_time": setup["evidence"]["liquidity_pool"]["time"],
                     "sweep_time": setup["evidence"]["sweep_time"], "bos_time": setup["evidence"]["bos_time"],
                     "gap_completed_at": setup["evidence"]["gap_completed_at"],
                     "return_time": setup["evidence"]["return_time"], "entry_zone": setup["entry_zone"],
                     "protected_price": protected["price"], "target_time": target_pivot["time"],
                     "target_price": target_pivot["price"]}
        candidate = {"side": side, "entry": entry, "entry_reference": "ACTUAL_ASK" if quote_used and side == "LONG"
                     else "ACTUAL_BID" if quote_used else "LAST_COMPLETED_CLOSE_RESEARCH_ONLY",
                     "quote_validated": quote_used, "quote_time": quote["time"] if quote_used else None,
                     "stop": float(stop_decimal), "structure_stop": float(stop_decimal),
                     "target": float(target_decimal), "tp1": float(target_decimal),
                     "entry_zone": list(setup["entry_zone"]), "gross_rr": float(rr), "gross_rr_exact": str(rr),
                     "quote_risk_exact": str(risk), "quote_reward_exact": str(reward),
                     "target_policy": "NEAREST_PREEXISTING_UNSWEPT_OPPOSING_LIQUIDITY",
                     "target_evidence": copy.deepcopy(target_pivot), "structural_evidence": copy.deepcopy(setup["evidence"]),
                     "formation": formation, "formation_id": _hash(formation),
                     "data_time": output["data_time"], "input_snapshot_hash": output["input_snapshot_hash"],
                     "protocol_revision": PROTOCOL_REVISION, "execution_ready": quote_used,
                     "net_cost_rr_required_by_caller": True, "win_probability_asserted": False}
        matrix["passed"] = quote_used
        matrix["structural_rr"] = {"passed": True, "gross_rr": float(rr), "min_rr": 2,
                                    "exact_reward": str(reward), "exact_risk": str(risk),
                                    "net_cost_validation_pending": True}
        output["candidate"] = candidate
        output["execution_ready"] = quote_used
        return finish([] if quote_used else ["QUOTE_REQUIRED"], "READY" if quote_used else "RESEARCH_READY")
    except (DataError, ValueError, TypeError, KeyError, OverflowError, ArithmeticError):
        return finish(["INVALID_DATA"], "DATA_ERROR")


"""Explicit OHLC specialists. House definitions, not complete named schools.

All references exclude the trigger bar. No agent has broker authority.
"""
import math
import statistics

from .strategies import _register, _result, _evidence, atr, ema, REGISTRY, AR, PERIODS

SPECS = {}


def specialist(id, ar, en, group, rules, parameters, regimes=("TREND", "RANGE", "MIXED")):
    def decorate(fn):
        _register(id, ar, [en], group, 60)(fn)
        SPECS[id] = dict(name_en=en, rules=rules, parameters=parameters,
                         allowed_regimes=list(regimes), timeframe_scope="all_completed_ohlc")
        return fn
    return decorate


def regime(b):
    """Prior-only 20-return efficiency; volatility ratio uses disjoint windows."""
    prior = b[:-1]
    if len(prior) < 41:
        return {"name": "UNKNOWN", "efficiency": None, "volatility_ratio": None}
    closes = [x["close"] for x in prior[-21:]]
    travel = sum(abs(y-x) for x, y in zip(closes, closes[1:]))
    efficiency = abs(closes[-1]-closes[0])/travel if travel else 0.0
    recent, baseline = atr(prior[-15:]), atr(prior[-41:-15])
    ratio = recent/baseline if baseline > 0 else None
    name = "HIGH_VOLATILITY" if ratio is not None and ratio >= 2 else (
        "TREND" if efficiency >= .45 else "RANGE" if efficiency <= .25 else "MIXED")
    return dict(name=name, efficiency=efficiency, volatility_ratio=ratio)


AR.update({"specialist rule confirmed": "تحققت قاعدة التخصص",
           "specialist trigger not completed": "لم يكتمل شرط دخول التخصص",
           "specialist levels": "مستويات قاعدة التخصص",
           "house definition; not a complete school or profitability claim": "تعريف خوارزمي محدد وليس مدرسة كاملة أو إثباتًا للربحية",
           "market regime outside declared scope": "حالة السوق خارج النطاق المعلن للاستراتيجية",
           "specialist mean target": "هدف المتوسط المحدد للاستراتيجية"})


def signal(b, bull, bear, stop_buy, stop_sell, details, target=None):
    # A contradictory bar is rejected, rather than assigning arbitrary priority.
    side = "BUY" if bull and not bear else "SELL" if bear and not bull else "NEUTRAL"
    active = side != "NEUTRAL"
    targets = ([{"price": target, "method": "specialist mean target", "fraction": 1.0}]
               if active and target is not None else None)
    return _result(side, active, b[-1]["close"], stop_buy if side == "BUY" else stop_sell,
                   [_evidence("specialist_rule", details, b, "specialist levels")],
                   ["specialist rule confirmed"] if active else [],
                   [] if active else ["specialist trigger not completed"],
                   ["house definition; not a complete school or profitability claim"], targets=targets)


def first_return(b, kind):
    """Newest qualifying untouched zone, at most 20 bars old; first touch only."""
    for end in range(len(b)-2, max(20, len(b)-22), -1):
        pre = b[:end-1] if kind == "gap" else b[:end]
        scale = atr(pre)
        if scale <= 0:
            continue
        if kind == "gap":
            a, impulse, z = b[end-2:end+1]
            up = z["low"] > a["high"] and impulse["close"]-impulse["open"] >= scale
            down = z["high"] < a["low"] and impulse["open"]-impulse["close"] >= scale
            lo, hi = (a["high"], z["low"]) if up else (z["high"], a["low"])
        else:
            base, impulse = b[end-1:end+1]
            up = impulse["close"] > base["high"] and impulse["close"]-impulse["open"] >= 1.5*scale
            down = impulse["close"] < base["low"] and impulse["open"]-impulse["close"] >= 1.5*scale
            lo, hi = base["low"], base["high"]
            if hi-lo > scale:
                continue
        if not (up or down) or hi-lo < .1*scale:
            continue
        # Any earlier touch consumes the zone, even if that touch did not reject.
        middle = b[end+1:-1]
        if any(x["low"] <= hi if up else x["high"] >= lo for x in middle):
            continue
        last = b[-1]
        bull = up and lo <= last["low"] <= hi and last["close"] > hi and last["close"] > last["open"]
        bear = down and lo <= last["high"] <= hi and last["close"] < lo and last["close"] < last["open"]
        if bull or bear:
            return signal(b, bull, bear, lo, hi, dict(low=lo, high=hi, formation_time=b[end]["time"], first_touch=True))
    return signal(b, False, False, None, None, {"first_touch": False})


@specialist("classic_pivot_reclaim", "استعادة النقطة المحورية اليومية", "Previous-session classic pivot reclaim", "structure",
            ["P=(H+L+C)/3, R1=2P-L, S1=2P-H, R2=P+(H-L), S2=P-(H-L), from a completed MT5 D1 bar only",
             "Intraday trigger pair shares the declared daily clock; reference closes before both trigger bars and is at most four days old",
             "Fresh directional close through P, inside first resistance/support; structural stop and first level target"],
            {"reference_timeframe": "D1", "max_reference_age_seconds": 345600,
             "entry_definition": "fresh pivot reclaim; no entry merely because price touches a level"})
def classic_pivot_reclaim(b, c):
    from .strategies import PERIODS, bar_close_time, validate_bars, DataError
    if c.get("timeframe") not in PERIODS or PERIODS[c["timeframe"]] >= 86400:
        return _result(missing=["daily pivot reclaim is an intraday model"])
    daily = c.get("daily_bars")
    if not daily:
        return _result(status="DATA_MISSING", missing=["completed MT5 daily reference required for classic pivots"])
    # Walk-forward context may include later history. It never enters this
    # reference; a new daily level must have existed before BOTH trigger bars.
    try:
        eligible = [x for x in daily if bar_close_time(x["time"], "D1") <= b[-2]["time"]]
        refs = validate_bars(eligible, "D1", c["as_of"])
    except (DataError, KeyError, TypeError, ValueError, OverflowError):
        return _result(status="DATA_MISSING", missing=["completed MT5 daily reference required for classic pivots"])
    if not refs:
        return _result(status="DATA_MISSING", missing=["completed MT5 daily reference required for classic pivots"])
    ref, previous, last = refs[-1], b[-2], b[-1]
    close_time = bar_close_time(ref["time"], "D1")
    same_clock_day = int((previous["time"]-ref["time"])/86400) == int((last["time"]-ref["time"])/86400)
    if not same_clock_day or last["time"]-close_time > 345600 or ref["high"] <= ref["low"]:
        return _result(missing=["daily pivot reference or trigger session is outside declared scope"])
    pivot = ref["high"]/3+ref["low"]/3+ref["close"]/3
    r1, s1 = 2*pivot-ref["low"], 2*pivot-ref["high"]
    r2, s2 = pivot+ref["high"]-ref["low"], pivot-ref["high"]+ref["low"]
    if any(not math.isfinite(p) or p <= 0 for p in (pivot, r1, s1, r2, s2)):
        return _result(missing=["classic pivot levels must be finite and positive"])
    bull = previous["close"] <= pivot < last["close"] < r1 and last["close"] > last["open"]
    bear = previous["close"] >= pivot > last["close"] > s1 and last["close"] < last["open"]
    result = signal(b, bull, bear, min(last["low"], s1), max(last["high"], r1),
                    dict(pivot=pivot, resistance_1=r1, support_1=s1,
                         resistance_2=r2, support_2=s2,
                         reference_open=ref["time"], reference_close=close_time,
                         daily_clock="MT5 D1 opening clock; no exchange-session claim"),
                    r1 if bull else s1 if bear else None)
    result["assumptions"].append("Classic pivot formula; reclaim, four-day expiry and exits are house definitions")
    if result["targets"]:
        result["targets"][0]["method"] = "first classic pivot resistance or support"
    return result


REGISTRY["classic_pivot_reclaim"]["data_requirements"] = ["completed_ohlc", "completed_mt5_daily_ohlc"]
SPECS["classic_pivot_reclaim"].update(
    timeframe_scope=[tf for tf, seconds in PERIODS.items() if seconds < 86400],
    rules_ar=["النقطة المحورية متوسط أعلى وأدنى وإغلاق يوم مكتمل من منصة التداول، مع حساب الدعم والمقاومة الكلاسيكيين.",
              "مرجع اليوم متاح قبل شمعتي التفعيل، ولا يزيد عمره على أربعة أيام، والشمعتان في اليوم نفسه وفق ساعة مرجع المنصة.",
              "عبور جديد بالإغلاق للنقطة المحورية داخل أول دعم أو مقاومة؛ وقف بنيوي وهدف عند المستوى الأول."],
    source="https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/pivot-points-resistance-support",
    scope="Classic pivot formula with explicit intraday house trigger; not every pivot variant or a profitability claim")
AR.update({"daily pivot reclaim is an intraday model": "استعادة النقطة المحورية اليومية نموذج للفريمات داخل اليوم فقط",
           "first classic pivot resistance or support": "هدف أول مقاومة أو دعم للنقطة المحورية الكلاسيكية",
           "classic pivot levels must be finite and positive": "يجب أن تكون مستويات النقاط المحورية موجبة ومحدودة",
           "completed MT5 daily reference required for classic pivots": "يلزم مرجع يومي مكتمل من منصة التداول لحساب النقاط المحورية",
           "daily pivot reference or trigger session is outside declared scope": "مرجع النقطة المحورية أو يوم التفعيل خارج النطاق المعلن",
           "Classic pivot formula; reclaim, four-day expiry and exits are house definitions": "معادلة النقطة المحورية كلاسيكية؛ الاستعادة وانتهاء المرجع بعد أربعة أيام والخروج تعريفات محلية"})


@specialist("fvg_first_return", "العودة الأولى للفجوة السعرية", "Three-bar gap first return", "structure",
            ["Directional middle body >= prior ATR; gap >= 0.1 ATR", "First subsequent touch within 20 bars; reject through near edge; no far-edge breach"],
            {"max_age": 20, "body_atr": 1, "min_gap_atr": .1})
def fvg_first_return(b, c):
    return first_return(b, "gap")


@specialist("base_first_return", "العودة الأولى لمنطقة الأساس", "Displacement base first return", "structure",
            ["Base range <= prior ATR; departure body >= 1.5 ATR and closes beyond base", "First return within 20 bars rejects zone without far-edge breach"],
            {"max_age": 20, "base_atr_max": 1, "body_atr": 1.5})
def base_first_return(b, c):
    return first_return(b, "base")


@specialist("donchian_20", "اختراق قناة عشرين شمعة", "20-bar channel breakout", "structure",
            ["Latest close crosses highest high / lowest low of 20 previous bars", "Stop reference is opposite channel boundary"],
            {"lookback": 20}, ("TREND", "MIXED"))
def donchian_20(b, c):
    prior, last = b[-21:-1], b[-1]
    hi, lo = max(x["high"] for x in prior), min(x["low"] for x in prior)
    return signal(b, b[-2]["close"] <= hi < last["close"], b[-2]["close"] >= lo > last["close"], lo, hi, dict(high=hi, low=lo))


@specialist("failed_range_break", "فشل اختراق النطاق", "Failed range breakout", "structure",
            ["Sweep prior 20-bar boundary and close back inside", "Close in inner 60% of bar toward reversal; reject simultaneous two-edge sweeps"],
            {"lookback": 20, "close_fraction": .6}, ("RANGE", "MIXED"))
def failed_range_break(b, c):
    p, x = b[-21:-1], b[-1]
    hi, lo = max(z["high"] for z in p), min(z["low"] for z in p)
    span = x["high"]-x["low"]
    bull = x["low"] < lo < x["close"] < hi and x["high"] <= hi and x["close"]-x["low"] >= .6*span
    bear = x["high"] > hi > x["close"] > lo and x["low"] >= lo and x["high"]-x["close"] >= .6*span
    return signal(b, bull, bear, x["low"], x["high"], dict(high=hi, low=lo))


@specialist("pin_rejection", "رفض الذيل عند حد سعري", "Boundary pin rejection", "candle",
            ["Touch or sweep prior 20-bar extreme and close back inside", "Dominant wick >= 2 bodies and >= 60% of range; opposite wick <= 20%; range >= 0.5 prior ATR"],
            {"lookback": 20, "wick_body": 2, "wick_range": .6, "opposite_wick": .2})
def pin_rejection(b, c):
    x, p = b[-1], b[-21:-1]
    span, body = x["high"]-x["low"], abs(x["close"]-x["open"])
    lower, upper = min(x["open"], x["close"])-x["low"], x["high"]-max(x["open"], x["close"])
    hi, lo = max(z["high"] for z in p), min(z["low"] for z in p)
    valid = span >= .5*atr(b[:-1]) and span > 0
    bull = valid and lower >= max(2*body, .6*span) and upper <= .2*span and x["low"] <= lo < x["close"]
    bear = valid and upper >= max(2*body, .6*span) and lower <= .2*span and x["high"] >= hi > x["close"]
    return signal(b, bull, bear, x["low"], x["high"], dict(low=lo, high=hi, lower_wick=lower, upper_wick=upper))


@specialist("inside_bar_break", "اختراق الشمعة الداخلية", "Inside bar breakout", "candle",
            ["Previous bar strictly inside mother bar", "Latest close crosses mother boundary in prior EMA20 direction"], {"ema": 20})
def inside_bar_break(b, c):
    mother, inside, x = b[-3:]
    center = ema([z["close"] for z in b[:-1]], 20)[-1]
    valid = inside["high"] < mother["high"] and inside["low"] > mother["low"]
    return signal(b, valid and x["close"] > mother["high"] and inside["close"] > center,
                  valid and x["close"] < mother["low"] and inside["close"] < center,
                  mother["low"], mother["high"], dict(low=mother["low"], high=mother["high"], mean=center))


@specialist("band_reentry", "العودة داخل النطاق الإحصائي", "Two-deviation band reentry", "statistical",
            ["Fixed mean and population deviation from 20 bars preceding both trigger bars", "Previous close outside 2 deviations; current close reenters but has not reached mean"],
            {"lookback": 20, "deviations": 2}, ("RANGE", "MIXED"))
def band_reentry(b, c):
    values = [x["close"] for x in b[-22:-2]]
    mean, sd = statistics.fmean(values), statistics.pstdev(values)
    hi, lo = mean+2*sd, mean-2*sd
    previous, now = b[-2]["close"], b[-1]["close"]
    return signal(b, sd > 0 and previous < lo <= now < mean, sd > 0 and previous > hi >= now > mean,
                  min(x["low"] for x in b[-2:]), max(x["high"] for x in b[-2:]), dict(mean=mean, high=hi, low=lo), mean)


@specialist("atr_channel_break", "اختراق قناة التقلب", "ATR channel breakout", "volatility",
            ["Fixed prior EMA20 +/- 2 prior ATR14", "Fresh close through channel in matching EMA direction"],
            {"ema": 20, "atr": 14, "multiplier": 2}, ("TREND", "MIXED"))
def atr_channel_break(b, c):
    means = ema([x["close"] for x in b[:-1]], 20)
    center, width = means[-1], 2*atr(b[:-1])
    hi, lo = center+width, center-width
    return signal(b, means[-1] > means[-2] and b[-2]["close"] <= hi < b[-1]["close"],
                  means[-1] < means[-2] and b[-2]["close"] >= lo > b[-1]["close"], center, center, dict(mean=center, high=hi, low=lo))


@specialist("momentum_acceleration", "تسارع الزخم السعري", "Normalized momentum acceleration", "momentum",
            ["20-bar price change freshly crosses +/- 2 prior ATR", "Sign agrees with prior EMA20 slope"],
            {"lookback": 20, "threshold_atr": 2, "ema": 20}, ("TREND", "MIXED"))
def momentum_acceleration(b, c):
    scale = atr(b[:-1])
    if scale <= 0:
        return signal(b, False, False, None, None, {"scale": scale})
    previous, current = (b[-2]["close"]-b[-22]["close"])/scale, (b[-1]["close"]-b[-21]["close"])/scale
    means = ema([x["close"] for x in b[:-1]], 20)
    return signal(b, previous <= 2 < current and means[-1] > means[-2], previous >= -2 > current and means[-1] < means[-2],
                  min(x["low"] for x in b[-5:]), max(x["high"] for x in b[-5:]), dict(previous=previous, current=current))


@specialist("utc_opening_range", "اختراق نطاق بداية اليوم العالمي", "UTC first-hour range breakout", "structure",
            ["Exact continuous first UTC hour available on M1/M2/M3/M4/M5/M6/M10/M12/M15/M20/M30", "Fresh close beyond first-hour range on same UTC day; explicitly not exchange opening hours"],
            {"start_utc_hour": 0, "range_minutes": 60})
def utc_opening_range(b, c):
    from .strategies import PERIODS
    step = PERIODS[c["timeframe"]]
    day = int(b[-1]["time"]//86400)*86400
    window = [x for x in b if day <= x["time"] < day+3600]
    expected = list(range(day, day+3600, step)) if step <= 1800 and 3600 % step == 0 else []
    if not expected or [x["time"] for x in window] != expected or b[-2]["time"] < day+3600:
        return signal(b, False, False, None, None, {"anchor_time": day, "complete": False})
    hi, lo = max(x["high"] for x in window), min(x["low"] for x in window)
    return signal(b, b[-2]["close"] <= hi < b[-1]["close"], b[-2]["close"] >= lo > b[-1]["close"],
                  lo, hi, dict(high=hi, low=lo, anchor_time=day))


@specialist("regression_reentry", "عودة إلى قناة الانحدار", "Regression residual reentry", "statistical",
            ["OLS on 30 closes preceding both trigger bars; population residual deviation", "Previous residual outside 2 deviations; latest residual recross inside toward projected center"],
            {"lookback": 30, "deviations": 2}, ("RANGE", "MIXED"))
def regression_reentry(b, c):
    values = [x["close"] for x in b[-32:-2]]
    n, mean = len(values), statistics.fmean(values)
    center = (n-1)/2
    slope = sum((i-center)*(y-mean) for i, y in enumerate(values))/sum((i-center)**2 for i in range(n))
    fitted = [mean+slope*(i-center) for i in range(n)]
    sd = (sum((a-z)**2 for a, z in zip(values, fitted))/n)**.5
    prev_center, now_center = mean+slope*(n-center), mean+slope*(n+1-center)
    prev, now = b[-2]["close"]-prev_center, b[-1]["close"]-now_center
    return signal(b, sd > 1e-12 and prev < -2*sd <= now < 0, sd > 1e-12 and prev > 2*sd >= now > 0,
                  min(x["low"] for x in b[-2:]), max(x["high"] for x in b[-2:]), dict(mean=now_center, slope=slope, deviation=sd), now_center)


@specialist("tick_activity_rejection", "رفض سعري مع نشاط التكات التقريبي", "Bar tick-activity rejection proxy", "volume",
            ["Bar tick count >= 1.5 times median of prior 20 bars; every sample must have positive tick count",
             "Reject prior 10-bar boundary; directional body; close in outer 20%; range >= 0.5 prior ATR",
             "OHLC close-location pressure is a proxy, never signed trades, real delta, footprint or depth"],
            {"volume_lookback": 20, "activity_multiplier": 1.5, "boundary_lookback": 10, "close_fraction": .8})
def tick_activity_rejection(b, c):
    x=b[-1]
    volumes=[z.get("tick_volume",0) for z in b[-21:]]
    if any(v<=0 for v in volumes):
        return _result(status="DATA_MISSING",missing=["positive bar tick counts required for local activity proxy"])
    baseline=statistics.median(volumes[:-1])
    span=x["high"]-x["low"]
    location=(x["close"]-x["low"])/span if span>0 else .5
    lo=min(z["low"] for z in b[-11:-1]); hi=max(z["high"] for z in b[-11:-1])
    active=volumes[-1]>=1.5*baseline and span>=.5*atr(b[:-1]) and span>0
    bull=active and x["low"]<=lo<x["close"] and x["high"]<=hi and location>=.8 and x["close"]>x["open"]
    bear=active and x["high"]>=hi>x["close"] and x["low"]>=lo and location<=.2 and x["close"]<x["open"]
    result=signal(b,bull,bear,x["low"],x["high"],dict(tick_count=volumes[-1],baseline=baseline,
                  activity_ratio=volumes[-1]/baseline,close_location=location,pressure_proxy=(2*location-1)*volumes[-1]))
    result["assumptions"].append("Bar tick activity and close-location proxy; not real order flow or signed volume")
    return result


REGISTRY["tick_activity_rejection"]["data_requirements"]=["completed_ohlc","positive_tick_volume"]
AR.update({"positive bar tick counts required for local activity proxy":"يلزم عدد تكات موجب لكل شمعة لحساب مؤشر النشاط المحلي",
           "Bar tick activity and close-location proxy; not real order flow or signed volume":"نشاط تكات الشموع وموقع الإغلاق مؤشر تقريبي؛ لا يمثل تدفق أوامر أو حجم صفقات محدد الاتجاه"})


def _prior_five_bar_pivots(b, lookback=60):
    """Strict five-bar pivots whose second right bar precedes the trigger.

    Every five-bar formation fits inside the fixed prior window. An outside
    bar that qualifies as both a high and low is excluded: OHLC cannot order
    its extremes. Indices refer to the supplied chronological series.
    """
    offset = max(0, len(b)-lookback-1)
    prior = b[offset:-1]
    pivots = []
    for i in range(2, len(prior)-2):
        neighbors = prior[i-2:i] + prior[i+1:i+3]
        high = all(prior[i]["high"] > x["high"] for x in neighbors)
        low = all(prior[i]["low"] < x["low"] for x in neighbors)
        if high == low:
            continue
        kind, key = ("HIGH", "high") if high else ("LOW", "low")
        pivots.append(dict(kind=kind, price=prior[i][key], index=offset+i,
                           time=prior[i]["time"], confirmation_bar_time=prior[i+2]["time"]))
    return pivots


@specialist("fractal_5_breakout", "اختراق فراكتال خماسي مؤكد", "Confirmed five-bar fractal breakout", "structure",
            ["Fixed 60 bars preceding the trigger; every strict pivot has two lower highs / higher lows on each side, with both right bars already closed before the trigger; ties and dual high/low pivot bars excluded",
             "Use the newest confirmed high and newest confirmed low; require high > low and a fresh completed close above the high / below the low from the previous close",
             "Trigger must remain strictly inside the opposite structural boundary; bars crossing both boundaries are rejected; structural stop reference is the newest opposite pivot",
             "House definition of five-bar breakout only; no Alligator filter or complete Bill Williams trading system"],
            {"lookback": 60, "left_bars": 2, "right_closed_bars": 2, "strict_pivots": True})
def fractal_5_breakout(b, c):
    if len(b) < 61:
        return _result(status="DATA_MISSING", missing=["61 completed bars required for bounded fractal breakout"])
    pivots = _prior_five_bar_pivots(b)
    highs = [p for p in pivots if p["kind"] == "HIGH"]
    lows = [p for p in pivots if p["kind"] == "LOW"]
    if not highs or not lows:
        return signal(b, False, False, None, None, dict(lookback=60, confirmed_high=None, confirmed_low=None))
    high, low, previous, last = highs[-1], lows[-1], b[-2], b[-1]
    valid = high["price"] > low["price"]
    bull = valid and previous["close"] <= high["price"] < last["close"] and last["low"] > low["price"]
    bear = valid and previous["close"] >= low["price"] > last["close"] and last["high"] < high["price"]
    return signal(b, bull, bear, low["price"], high["price"],
                  dict(lookback=60, confirmed_high=high, confirmed_low=low,
                       previous_close=previous["close"], reference_precedes_trigger=True,
                       dual_boundary_cross=last["high"] >= high["price"] and last["low"] <= low["price"]))


OBV_TICK_ASSUMPTION = "Close-signed tick-count OBV is a candle-volume proxy; not traded-volume OBV, signed trades or real order flow"
AR.update({"61 completed bars required for bounded fractal breakout": "يلزم 61 شمعة مكتملة لنموذج اختراق الفراكتال المحدود",
           "61 completed bars required for bounded OBV proxy": "يلزم 61 شمعة مكتملة لنموذج OBV التقريبي المحدود",
           "bounded OBV cumulative value must be finite": "قيمة OBV التراكمية يجب أن تكون محدودة",
           "positive finite tick counts required for every bounded OBV bar": "يلزم عدد تكات موجب ومحدود لكل شمعة ضمن نافذة OBV",
           "bounded OBV cumulative value must be finite": "يجب أن تكون القيمة التراكمية لمؤشر OBV المحدود منتهية",
           OBV_TICK_ASSUMPTION: "OBV المحسوب من اتجاه الإغلاق وعدد التكات بديل حجمي تقريبي للشموع؛ ليس حجم صفقات أو صفقات محددة الاتجاه أو تدفق أوامر فعلي"})


@specialist("obv_divergence_reclaim", "اختلاف OBV التقريبي واستعادة المستوى", "Tick-count OBV divergence and price reclaim proxy", "volume",
            ["Fixed 60 completed bars preceding the trigger plus the trigger; positive finite MT5 tick_volume on every bar; never substitute real_volume or silently fill missing activity",
             "Start OBV at zero at the window's first bar; add / subtract the current bar tick count when close rises / falls versus the preceding close; unchanged closes add zero",
             "Newest two strict confirmed five-bar lows: lower price low with strictly higher OBV; bearish mirror is higher price high with strictly lower OBV; dual high/low pivots and ties excluded",
             "Pivot separation <= 30 bars; trigger occurs 1..8 bars after the second right confirmation bar, which must precede the trigger",
             "Fresh completed close reclaims the maximum intervening high for BUY / minimum intervening low for SELL; latest divergence pivot remains unbroken through trigger and supplies the structural stop; opposing simultaneous triggers abstain",
             "House divergence, confirmation, expiry and reclaim definition; tick-count candle-volume proxy, not actual order flow or the complete OBV theory"],
            {"lookback": 60, "left_bars": 2, "right_closed_bars": 2,
             "max_pivot_separation": 30, "max_confirmation_age": 8, "volume_source": "tick_volume"})
def obv_divergence_reclaim(b, c):
    if len(b) < 61:
        return _result(status="DATA_MISSING", missing=["61 completed bars required for bounded OBV proxy"],
                       assumptions=[OBV_TICK_ASSUMPTION])
    offset = len(b)-61
    window = b[offset:]
    volumes = [x.get("tick_volume") for x in window]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in volumes):
        return _result(status="DATA_MISSING", missing=["positive finite tick counts required for every bounded OBV bar"],
                       assumptions=[OBV_TICK_ASSUMPTION])
    obv = [0.0]
    for previous, current, volume in zip(window, window[1:], volumes[1:]):
        change = volume if current["close"] > previous["close"] else -volume if current["close"] < previous["close"] else 0
        obv.append(obv[-1]+change)
    if any(not math.isfinite(value) for value in obv):
        return _result(status="DATA_INVALID", missing=["bounded OBV cumulative value must be finite"],
                       assumptions=[OBV_TICK_ASSUMPTION])
    pivots = _prior_five_bar_pivots(b)
    details = dict(lookback=60, volume_source="tick_volume", volume_units="tick_count",
                   obv_origin_time=window[0]["time"], obv_current=obv[-1],
                   reference_precedes_trigger=True, bullish_setup=None, bearish_setup=None)
    setups = {}
    for kind in ("LOW", "HIGH"):
        selected = [p for p in pivots if p["kind"] == kind]
        if len(selected) < 2:
            continue
        first, second = selected[-2:]
        distance = second["index"]-first["index"]
        age = len(b)-1-(second["index"]+2)
        first_obv, second_obv = obv[first["index"]-offset], obv[second["index"]-offset]
        bullish = kind == "LOW"
        divergence = (second["price"] < first["price"] and second_obv > first_obv if bullish else
                      second["price"] > first["price"] and second_obv < first_obv)
        between = b[first["index"]+1:second["index"]]
        level = max(x["high"] for x in between) if bullish else min(x["low"] for x in between)
        intact = all(x["low"] >= second["price"] if bullish else x["high"] <= second["price"]
                     for x in b[second["index"]+1:])
        crossed = b[-2]["close"] <= level < b[-1]["close"] if bullish else b[-2]["close"] >= level > b[-1]["close"]
        setup = dict(first_pivot=first, second_pivot=second, first_obv=first_obv, second_obv=second_obv,
                     divergence=divergence, pivot_separation=distance, confirmation_age=age,
                     reclaim_level=level, pivot_intact=intact)
        details["bullish_setup" if bullish else "bearish_setup"] = setup
        setups[kind] = (divergence and distance <= 30 and 1 <= age <= 8 and intact and crossed, second["price"])
    bull, stop_buy = setups.get("LOW", (False, None))
    bear, stop_sell = setups.get("HIGH", (False, None))
    result = signal(b, bull, bear, stop_buy, stop_sell, details)
    result["assumptions"].append(OBV_TICK_ASSUMPTION)
    return result


for _new_id in ("fractal_5_breakout", "obv_divergence_reclaim"):
    REGISTRY[_new_id]["min_bars"] = 61
    SPECS[_new_id]["rules_en"] = list(SPECS[_new_id]["rules"])
REGISTRY["obv_divergence_reclaim"]["data_requirements"] = ["completed_ohlc", "positive_tick_volume"]
SPECS["fractal_5_breakout"].update(
    source="https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals",
    scope="House strict five-bar breakout, fixed window and stop; not the complete Bill Williams system")
SPECS["obv_divergence_reclaim"].update(
    source="https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/OBV",
    volume_source_reference="https://www.mql5.com/en/docs/constants/structures/mqlrates",
    scope="House tick-count candle-volume divergence/reclaim proxy; not actual order flow or complete OBV theory")


RULES_AR = {
    "fractal_5_breakout": ["نافذة ثابتة من ستين شمعة قبل شمعة التفعيل؛ محور خماسي صارم بقمتين أدنى أو قاعين أعلى على كل جانب، مع اكتمال الشمعتين اللاحقتين قبل التفعيل؛ التعادل والمحور المزدوج مستبعدان.",
                           "أحدث قمة وأحدث قاع مؤكدين، مع القمة أعلى من القاع؛ يعبر الإغلاق المكتمل حديثًا القمة للشراء أو القاع للبيع مقارنة بالإغلاق السابق.",
                           "تبقى شمعة التفعيل داخل الحد البنيوي المقابل بصورة صارمة؛ تجاوز الحدين مرفوض، ومرجع الوقف أحدث محور مقابل.",
                           "تعريف محلي محدد للاختراق الخماسي؛ لا يتضمن فلتر التمساح ولا نظام بيل ويليامز الكامل."],
    "obv_divergence_reclaim": ["ستون شمعة مكتملة قبل التفعيل مع شمعة التفعيل؛ عدد تكات MT5 موجب ومحدود لكل شمعة، دون استبداله بحجم فعلي أو تعويض القيم المفقودة.",
                               "يبدأ OBV بصفر عند أول شمعة؛ يضاف أو يطرح عدد تكات الشمعة وفق ارتفاع الإغلاق أو انخفاضه عن السابق، والتعادل لا يغير القيمة.",
                               "أحدث قاعين خماسيين مؤكدين: قاع سعري أدنى مع OBV أعلى بصورة صارمة؛ للبيع قمة سعرية أعلى مع OBV أدنى؛ يستبعد التعادل والمحاور المزدوجة.",
                               "المسافة بين المحورين لا تتجاوز ثلاثين شمعة؛ التفعيل بعد شمعة تأكيد المحور الثاني بواحدة إلى ثماني شموع، والتأكيد يسبق شمعة التفعيل.",
                               "إغلاق جديد فوق أعلى قمة بين القاعين للشراء أو أسفل أدنى قاع بين القمتين للبيع؛ يبقى المحور الأخير دون كسر حتى التفعيل وهو مرجع الوقف؛ التفعيل المتعارض يمتنع.",
                               "الاختلاف والتأكيد والعمر والاستعادة قواعد محلية؛ الحجم بديل تقريبي لشموع التكات وليس تدفق أوامر فعليًا أو نظرية OBV كاملة."],
    "tick_activity_rejection": ["عدد تكات الشمعة لا يقل عن مرة ونصف وسيط العشرين شمعة السابقة، مع أعداد موجبة لكل العينة.",
                               "رفض حد العشر شموع السابقة بجسم اتجاهي وإغلاق في طرف عشرين بالمئة من الشمعة.",
                               "ضغط الإغلاق مؤشر حسابي تقريبي وليس دلتا فعلية أو بصمة أوامر أو عمق سوق."],
    "fvg_first_return": ["جسم الشمعة الوسطى لا يقل عن نطاق التقلب السابق والفجوة لا تقل عن عُشره.", "أول ملامسة خلال عشرين شمعة، ثم إغلاق خارج الحافة القريبة دون تجاوز الحافة البعيدة."],
    "base_first_return": ["عرض الأساس لا يزيد على نطاق التقلب، وجسم الاندفاع لا يقل عن ضعفه مرة ونصف مع إغلاق خارج الأساس.", "أول عودة خلال عشرين شمعة ترفض المنطقة دون اختراق طرفها البعيد."],
    "donchian_20": ["إغلاق جديد خلف أعلى قمة أو أدنى قاع للعشرين شمعة السابقة.", "مرجع الوقف هو الطرف المقابل للقناة."],
    "failed_range_break": ["تجاوز طرف نطاق العشرين شمعة السابقة ثم إغلاق داخل النطاق.", "الإغلاق ضمن ستين بالمئة من الشمعة باتجاه العودة؛ تجاوز الطرفين معًا مرفوض."],
    "pin_rejection": ["ملامسة أو تجاوز الحد السعري للعشرين شمعة السابقة والإغلاق داخله.", "الذيل الرئيسي ضعف الجسم على الأقل وستون بالمئة من الشمعة، والذيل المقابل لا يتجاوز عشرين بالمئة."],
    "inside_bar_break": ["الشمعة السابقة تقع بالكامل داخل الشمعة الأم.", "إغلاق جديد خارج حد الشمعة الأم في اتجاه المتوسط الأسي السابق لعشرين شمعة."],
    "band_reentry": ["متوسط وانحراف معياري من عشرين شمعة قبل شمعتي الدخول.", "الإغلاق السابق خارج انحرافين معياريين والحالي يعود داخلهما قبل الوصول للمتوسط."],
    "atr_channel_break": ["قناة ثابتة حول المتوسط الأسي السابق بعرض ضعفي نطاق التقلب.", "اختراق جديد بالإغلاق في اتجاه ميل المتوسط."],
    "momentum_acceleration": ["تغير السعر خلال عشرين شمعة يعبر حديثًا عتبة ضعفي نطاق التقلب السابق.", "اتجاه العبور يوافق ميل المتوسط الأسي السابق."],
    "utc_opening_range": ["توفر كل شموع الساعة الأولى من اليوم بالتوقيت العالمي دون فجوات.", "إغلاق جديد خارج هذا النطاق في اليوم نفسه؛ هذا ليس توقيت افتتاح بورصة بعينها."],
    "regression_reentry": ["انحدار خطي على ثلاثين إغلاقًا قبل شمعتي الدخول مع انحراف البواقي.", "عودة الباقي السعري من خارج انحرافين إلى داخلهما باتجاه المركز المتوقع."],
}
for _id, _rules in RULES_AR.items():
    SPECS[_id]["rules_ar"] = _rules
SPECS["utc_opening_range"]["timeframe_scope"] = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30"]


def install_contracts():
    for id, meta in REGISTRY.items():
        spec = SPECS.get(id, {})
        if id == "harmonic_abcd":
            spec = {"rules": ["Four confirmed alternating pivots; BC/AB 0.382..0.886; CD/AB 0.95..1.05; CD/BC 1.13..2.618",
                              "Fresh break of two-bar D confirmation level within eight bars; D intact; target C not passed"],
                    "rules_ar": ["أربعة محاور مؤكدة؛ تصحيح الضلع الثاني بين 38.2 و88.6 بالمئة، وتشابه الضلعين ضمن خمسة بالمئة.",
                                 "اختراق مستوى تأكيد النقطة الرابعة خلال ثماني شموع مع بقائها سليمة وهدف عند النقطة الثالثة."],
                    "source": "https://harmonictrader.com/harmonic-patterns/abcd-pattern/",
                    "scope": "Equal-leg pattern; custom tolerance, entry, expiry and exit, not the complete harmonic school"}
        meta["contract"] = {
            "schema_version": 1, "rule_id": id, "rule_version": meta["version"],
            "data_requirements": list(meta["data_requirements"]), "minimum_bars": meta["min_bars"],
            "completed_bars_only": True, "evidence_group": meta["evidence_group"],
            "coverage": meta["coverage"], "school_complete": False,
            "definition": spec or {"implementation": "nexus.strategies."+meta["strategy"],
                                    "scope": "existing versioned algorithm; see exported exact rule source"},
            "missing_data_policy": "abstain", "direct_broker_authority": False,
            "promotion_policy": "versioned code change plus tests; never automatic self-modification",
            "data_policy": "MT5_ONLY",
            "external_model_api_required": False,
            "price_plan": "closed-bar entry zone +/- 0.15 ATR; structural stop buffered 0.1 ATR; default 2R or explicit model target",
            "portfolio_authority": "independent shared daily risk; no agent may alter limits",
            "executable_specialists": {"smc_ict_proxy": ["fvg_first_return"],
                                       "supply_demand_proxy": ["base_first_return"],
                                       "order_flow": ["tick_activity_rejection"]}.get(id, []),
        }


install_contracts()

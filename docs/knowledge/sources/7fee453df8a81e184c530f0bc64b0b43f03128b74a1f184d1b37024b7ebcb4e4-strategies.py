"""Causal, inspectable technical research. No strategy can call a broker.

These are explicit computational definitions, not claims to replicate every
interpretation of the named schools. Scores measure rule coverage, not win odds.
"""
from __future__ import annotations

import hashlib
import copy
import json
import math
import statistics
import time
from collections.abc import Callable, Mapping

from .timeframes import PERIODS as PERIODS, bar_close_time, month_start
REGISTRY: dict[str, dict] = {}

# The English rule keys remain visible for reproducibility; every common
# user-facing explanation receives an Arabic description first.
AR = {
    "four confirmed alternating harmonic pivots": "يلزم أربعة محاور هارمونيك متعاقبة ومؤكدة",
    "equal-leg ratios outside declared bounds": "نسب الأضلاع خارج الحدود المحددة للنموذج",
    "fresh break after D confirmation within eight bars": "يلزم اختراق جديد بعد تأكيد النقطة الرابعة خلال ثماني شموع",
    "confirmed equal-leg geometry": "هندسة أضلاع متساوية مؤكدة",
    "fresh post-confirmation break": "اختراق جديد بعد تأكيد النموذج",
    "unbroken D and fresh confirmation break before C target": "يلزم بقاء النقطة الرابعة سليمة واختراق جديد قبل بلوغ هدف النقطة الثالثة",
    "harmonic C pivot target": "هدف المحور الثالث للنموذج",
    "Equal-leg model only; not all harmonic patterns; entry confirmation and tolerances are house rules": "نموذج الأضلاع المتساوية فقط؛ تأكيد الدخول والسماحات قواعد خاصة بهذه النسخة ولا تغطي كل الهارمونيك",
    "wait for a complete entry setup": "انتظار اكتمال شروط الدخول",
    "wait or opposing confirmed setup": "الانتظار، أو إعداد مؤكد في الاتجاه الآخر",
    "completed close beyond the analysis level": "إغلاق شمعة مكتملة خلف مستوى إبطال التحليل",
    "declared rule on the latest completed bar; quote must remain inside zone": "تحققت القاعدة على آخر شمعة مكتملة؛ يجب أن يبقى السعر الحالي داخل منطقة الدخول",
    "structure with 0.1 ATR buffer and >=0.6 ATR risk": "وقف خلف البنية مع هامش 0.1 ATR ومسافة مخاطرة لا تقل عن 0.6 ATR",
    "2 * proposed stop distance": "هدف يساوي ضعفي مسافة الوقف المقترح",
    "pre-trigger sample mean": "متوسط عينة سابقة لشموع تفعيل الدخول",
    "two confirmed highs and lows": "يلزم وجود قمتين وقاعين مؤكدين",
    "confirmed structure": "بنية قمم وقيعان مؤكدة",
    "fresh close through confirmed swing": "يلزم اختراق جديد بالإغلاق لقمة أو قاع مؤكد",
    "engulfing body": "جسم شمعة ابتلاعية",
    "body >= 0.5 ATR and engulfing": "يلزم ابتلاع جسم الشمعة السابقة بحجم لا يقل عن نصف ATR",
    "engulfing body / ATR": "حجم الجسم الابتلاعي مقارنة بالتقلب ATR",
    "support": "دعم مؤكد", "resistance": "مقاومة مؤكدة",
    "touch and close rejection": "ملامسة المستوى وإغلاق يدل على الرفض",
    "confirmed level rejection": "يلزم رفض مؤكد عند مستوى الدعم أو المقاومة",
    "prior range top": "سقف النطاق السابق", "prior range bottom": "قاع النطاق السابق",
    "close breakout": "اختراق بإغلاق مكتمل", "subsequent retest holds": "إعادة اختبار لاحقة حافظت على المستوى",
    "breakout followed by retest": "يلزم اختراق يعقبه إعادة اختبار ناجحة",
    "three closes confirm top": "سقف الصندوق تأكد بثلاث شموع لاحقة",
    "box confirmed": "صندوق مؤكد", "fresh box breakout": "يلزم اختراق جديد للصندوق",
    "cloud calculated 26 completed bars earlier": "سحابة الوقت الحالي محسوبة قبل 26 شمعة مكتملة",
    "Tenkan/Kijun directional ordering": "ترتيب خطي تنكان وكيجون يحدد السياق الاتجاهي",
    "fresh cross outside causal cloud": "تقاطع جديد خارج السحابة المحسوبة دون بيانات مستقبلية",
    "fresh cross and cloud filter": "يلزم تقاطع جديد وتحقق فلتر السحابة",
    "confirmed alternating swing pair": "يلزم قمة وقاع متعاقبان ومؤكدان",
    "0.618 pullback": "مستوى تصحيح 61.8%", "0.5 recovery trigger": "تفعيل استعادة مستوى تصحيح 50%",
    "confirmed swing": "موجة سعرية مؤكدة", "pullback recovery": "استعادة المستوى بعد التصحيح",
    "0.618 touch and fresh 0.5 recovery": "يلزم لمس تصحيح 61.8% ثم استعادة جديدة لمستوى 50%",
    "EMA directional ordering": "ترتيب المتوسطين يعطي السياق الاتجاهي",
    "fresh EMA crossover": "يلزم تقاطع جديد للمتوسطين EMA12 وEMA26",
    "fresh threshold recovery": "استعادة جديدة لعتبة الزخم", "RSI recross 30 or 70": "يلزم عبور RSI عائداً عبر 30 أو 70",
    "simple RSI14": "مؤشر RSI14 بمتوسط بسيط",
    "prior-only bands": "نطاقات محسوبة من البيانات السابقة فقط",
    "contraction": "انكماش التقلب", "contraction then fresh outside-band close": "يلزم انكماش التقلب ثم إغلاق جديد خارج النطاق",
    "nonzero dispersion": "يلزم تشتت سعري موجب", "stable mean": "استقرار نسبي للمتوسط",
    "fresh zscore recross with valid mean target": "يلزم عودة درجة Z عبر العتبة وهدف متوسط صالح في اتجاه الصفقة",
    "mean estimated before both trigger bars": "المتوسط مقدر قبل شموع تفعيل الدخول",
    "at least three completed bars after anchor": "يلزم ثلاث شموع مكتملة على الأقل بعد نقطة التثبيت",
    "positive weights for each anchored bar": "يلزم وزن حجم موجب لكل شمعة بعد التثبيت",
    "bar VWAP": "متوسط مرجح بحجم شموع الوسيط", "tick-weighted typical-price proxy": "بديل تقريبي للسعر النموذجي المرجح بعدد التكات",
    "fresh weighted-mean reclaim": "استعادة جديدة للمتوسط المرجح", "fresh reclaim": "يلزم عبور جديد للمتوسط المرجح",
    "Tick volume is activity count, not centralized traded volume": "عدد التكات يقيس النشاط ولا يمثل حجم تداول مركزي",
    "Tick-weighted mean is a proxy, not genuine transaction VWAP": "المتوسط المرجح بالتكات بديل تقريبي وليس VWAP للصفقات الفعلية",
    "Bar typical-price approximation, not trade-level VWAP": "تقدير باستخدام السعر النموذجي للشمعة، وليس أسعار كل الصفقات",
    "Real volume is venue/broker supplied, not asserted centralized": "الحجم الفعلي إن توفر مصدره الوسيط أو منصة التداول ولا يفترض أنه مركزي",
    "identified partner and completed aligned bars": "يلزم أصل مقابل محدد وبيانات مكتملة متزامنة",
    "42 exactly time-aligned bars": "يلزم 42 شمعة متطابقة زمنياً بين الأصلين",
    "40 prior log-return pairs": "ارتباط 40 زوجاً من العوائد اللوغاريتمية السابقة",
    "return correlation >= 0.7": "ارتباط العوائد لا يقل عن 0.7",
    "fresh breakout with partner direction": "يلزم اختراق جديد متوافق مع اتجاه الأصل المقابل",
    "AB=CD candidate ratio": "نسبة مرشحة لتشابه AB مع CD",
    "full harmonic ratio taxonomy, alternation resolution, and independently validated trigger": "تعريفات نسب الهارمونيك الكاملة وحسم التعاقب واختبار قاعدة دخول مستقلة غير مكتملة",
    "nonunique counts": "ترقيم موجي غير فريد مع بدائل محتملة",
    "complete nesting/alternation rules and validated execution trigger": "قواعد درجات الموجات والتعاقب وقاعدة الدخول المختبرة غير مكتملة",
    "phase uncertainty": "عدم يقين في مرحلة وايكوف",
    "phase A-E formal inference and reliable traded-volume confirmation": "تعريف مراحل وايكوف A-E وتأكيدها بحجم صفقات موثوق غير مكتمل",
    "OHLC FVG proxy": "فجوة ثلاث شموع كبديل تقريبي لعدم التوازن",
    "formal session model, order-block lifecycle and independently validated liquidity trigger": "نموذج الجلسات ودورة كتل الأوامر وقاعدة السيولة المختبرة غير مكتملة",
    "prior candle base proxy": "شمعة سابقة كمنطقة أساس تقريبية",
    "zone freshness/lifecycle and retest execution validation": "عمر منطقة العرض والطلب وإبطالها واختبار الدخول عند العودة غير مكتمل",
    "partner-specific swing synchronization, divergence lifecycle and execution validation": "مزامنة القمم بين الأصلين ودورة اختلاف SMT واختبار الدخول غير مكتملة",
    "multiple years, adjusted contract history and calendar bucket OOS validation": "يلزم تاريخ عدة سنوات معدل للعقود واختبار موسمية خارج العينة",
    "300 intraday bars cannot establish seasonality": "300 شمعة داخل اليوم لا تكفي لإثبات الموسمية",
    "declared price/time normalization, square-nine rules and validated execution definition": "تعريف تطبيع السعر والزمن ومربع التسعة وقواعد التنفيذ غير منفذ",
    "signed trades and reliable historical depth/venue data": "بيانات اتجاه الصفقات وعمق السوق التاريخي الموثوق غير متاحة",
    "MT5 OHLC/tick counts cannot produce real delta or footprint": "شموع MT5 وعدد التكات لا تنتج دلتا أو بصمة أوامر فعلية",
    "last completed bar is stale": "آخر شمعة مكتملة قديمة",
    "nonzero tradable range": "يلزم نطاق سعري موجب قابل للتداول",
    "positive target in trade direction": "يلزم هدف موجب صالح في اتجاه الصفقة",
    "execution prices must be finite and positive": "يجب أن تكون أسعار التنفيذ موجبة ومحدودة",
    "zero ATR": "قيمة ATR صفرية",
    "insufficient history": "تاريخ البيانات غير كافٍ",
    "broker completed OHLC": "شموع مكتملة من الوسيط",
    "synthetic completed OHLC": "شموع صناعية مكتملة للاختبار فقط",
    "completed OHLC with undeclared provenance": "شموع مكتملة بمصدر غير موثق",
    "history does not cover the declared anchor boundary": "التاريخ لا يغطي بداية مرساة الحساب المعلنة",
    "Fixed 20-bar Darvas variant; not every discretionary box interpretation": "تعريف دارفاس محدد بصندوق 20 شمعة ولا يمثل جميع القراءات التقديرية",
    "Chikou drawn retrospectively is not used as predictive input": "رسم شيكو إلى الماضي لا يستخدم كبيانات تنبؤية",
    "Simple rolling gain/loss RSI; deliberately not Wilder smoothing": "RSI بمتوسط ربح وخسارة بسيط متحرك وليس تنعيم وايلدر",
    "No stationarity or Gaussian distribution claim": "لا يفترض ثبات التوزيع أو كونه طبيعياً",
    "Correlation is unstable and not causal; single-leg confirmation, not a hedged pair strategy": "الارتباط متغير ولا يثبت السببية؛ تأكيد لأصل واحد وليس استراتيجية تحوط مزدوجة",
    "AB=CD resemblance is descriptive; not a completed Gartley/Bat/Butterfly signal": "تشابه AB=CD وصفي ولا يثبت اكتمال نموذج غارتلي أو بات أو باترفلاي",
    "Counts are alternatives; no unique Elliott interpretation or future wave is asserted": "ترقيم إليوت بدائل غير فريدة ولا يؤكد موجة مستقبلية",
    "A sweep/reclaim is not proof of accumulation or institutional intent": "كسر النطاق واستعادته لا يثبت التجميع أو نية مؤسسة",
    "Three-bar gap does not identify actual orders or institutional order flow": "فجوة ثلاث شموع لا تكشف الأوامر الفعلية أو التدفق المؤسسي",
    "OHLC base is not observed supply or demand orders": "منطقة أساس شمعة ليست أوامر عرض وطلب مرصودة",
    "No SMT direction inferred from a missing partner": "لا يستنتج اتجاه SMT عند غياب بيانات الأصل المقابل",
    "unsupported timeframe": "الفريم غير مدعوم",
    "invalid analysis time": "وقت التحليل غير صالح",
    "missing or nonfinite OHLC/time": "سعر أو وقت مفقود أو غير محدود",
    "bars must have unique ascending UTC times": "يجب أن تكون أوقات الشموع UTC متزايدة ودون تكرار",
    "unfinished or future bar": "شمعة غير مكتملة أو من المستقبل",
    "invalid OHLC geometry": "علاقة أسعار الفتح والإغلاق والقمة والقاع غير صحيحة",
    "invalid volume/spread": "بيانات الحجم أو السبريد غير صالحة",
    "confirmed double-top or double-bottom geometry": "هندسة مؤكدة لنموذج القمتين أو القاعين",
    "confirmed head-and-shoulders geometry": "هندسة مؤكدة لنموذج الرأس والكتفين",
    "fresh completed close through the neckline": "إغلاق مكتمل جديد عبر خط العنق",
    "confirmed classical reversal geometry": "يلزم نموذج انعكاسي كلاسيكي مؤكد وفق الحدود الرقمية المعلنة",
    "neckline break on the latest completed bar": "يلزم كسر خط العنق على آخر شمعة مكتملة",
    "classical reversal geometry": "هندسة نموذج انعكاسي كلاسيكي",
    "pattern height projected from neckline": "إسقاط ارتفاع النموذج من خط العنق",
    "three confirmed highs and three confirmed lows": "يلزم ثلاث قمم وثلاثة قيعان مؤكدة",
    "converging triangle geometry": "هندسة مثلث متقارب مؤكدة",
    "fresh completed close outside triangle": "إغلاق مكتمل جديد خارج حدود المثلث",
    "confirmed converging triangle": "يلزم مثلث متقارب بخطين صالحين من قمم وقيعان مؤكدة",
    "triangle breakout on the latest completed bar": "يلزم كسر المثلث على آخر شمعة مكتملة",
    "triangle height projected from breakout close": "إسقاط ارتفاع المثلث من إغلاق الاختراق",
    "Regression lines describe confirmed OHLC pivots; they do not imply exact discretionary trendlines": "خطوط الانحدار تصف قمم وقيعان OHLC مؤكدة ولا تدعي مطابقة خطوط الاتجاه التقديرية",
    "Pattern names describe explicit OHLC geometry, not a forecast guarantee": "أسماء النماذج تصف هندسة OHLC معلنة ولا تضمن التنبؤ",
}


def arabic(text: str) -> str:
    translated = AR.get(text)
    return f"{translated} ({text})" if translated else text


class DataError(ValueError):
    pass


def validate_bars(bars: list[dict], timeframe: str, as_of: float) -> list[dict]:
    """Reject, rather than silently trim, unfinished/future/malformed bars."""
    if isinstance(as_of, bool) or not isinstance(as_of, (int, float)) or not math.isfinite(as_of):
        raise DataError("invalid analysis time")
    if timeframe not in PERIODS:
        raise DataError("unsupported timeframe")
    if not isinstance(bars, (list, tuple)):
        raise DataError("missing or nonfinite OHLC/time")
    previous = None
    result = []
    for raw in bars:
        if not isinstance(raw, Mapping):
            raise DataError("missing or nonfinite OHLC/time")
        b = dict(raw)
        for key in ("time", "open", "high", "low", "close"):
            if key not in b or isinstance(b[key], bool) or not isinstance(b[key], (int, float)) or not math.isfinite(b[key]):
                raise DataError("missing or nonfinite OHLC/time")
        if b["time"] < 0 or (previous is not None and b["time"] <= previous):
            raise DataError("bars must have unique ascending UTC times")
        try:
            closing_time = bar_close_time(b["time"], timeframe)
        except (ValueError, OverflowError, OSError) as exc:
            raise DataError("missing or nonfinite OHLC/time") from exc
        if not math.isfinite(closing_time) or closing_time > as_of:
            raise DataError("unfinished or future bar")
        if b["low"] <= 0 or b["high"] < max(b["open"], b["close"], b["low"]) or b["low"] > min(b["open"], b["close"]):
            raise DataError("invalid OHLC geometry")
        for key in ("tick_volume", "real_volume", "spread"):
            value = b.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise DataError("invalid volume/spread")
            b[key] = value
        previous = b["time"]
        result.append(b)
    return result


def causal_pivots(bars: list[dict], left: int = 2, right: int = 2,
                  as_of: float | None = None, timeframe: str = "H1") -> list[dict]:
    """A pivot at i only exists after i+right has CLOSED; ties are excluded."""
    if left < 1 or right < 1:
        raise ValueError("pivot confirmation needs positive left/right")
    as_of = time.time() if as_of is None else as_of
    data = validate_bars(bars, timeframe, as_of)
    result = []
    for i in range(left, len(data) - right):
        neighbors = data[i-left:i] + data[i+1:i+right+1]
        for kind, key, compare in (("HIGH", "high", max), ("LOW", "low", min)):
            extreme = compare(b[key] for b in neighbors)
            if (kind == "HIGH" and data[i][key] > extreme) or (kind == "LOW" and data[i][key] < extreme):
                result.append({"kind": kind, "price": data[i][key], "index": i,
                               "time": data[i]["time"], "confirmed_at": bar_close_time(data[i+right]["time"],timeframe)})
    return sorted(result, key=lambda x: (x["time"], x["kind"]))


def atr(bars: list[dict], period: int = 14) -> float:
    if len(bars) < 2:
        return 0.0
    # The arithmetic mean uses only the trailing period, including its
    # preceding close. Avoid calculating discarded true ranges on long books.
    start = max(1, len(bars)-period) if period > 0 else 1
    tr = [max(bars[i]["high"]-bars[i]["low"], abs(bars[i]["high"]-bars[i-1]["close"]),
              abs(bars[i]["low"]-bars[i-1]["close"])) for i in range(start,len(bars))]
    return statistics.fmean(tr[-period:])


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    out = [values[0]]
    alpha = 2 / (period + 1)
    for value in values[1:]:
        out.append(out[-1] + alpha * (value-out[-1]))
    return out


def rsi(values: list[float], period: int = 14) -> float:
    changes = [b-a for a, b in zip(values, values[1:])][-period:]
    gains = sum(max(c, 0) for c in changes)
    losses = sum(max(-c, 0) for c in changes)
    return 100 * gains/(gains+losses) if gains+losses else 50.0


def _chart_features(symbol: str, timeframe: str, bars: list[dict], data_kind: str) -> dict | None:
    """Freeze eight causal features from 41 already validated completed bars.

    No missing activity, zero range or unstable scale is filled or substituted.
    Features describe price and tick activity; they do not assert order flow.
    Their original decision snapshot is the only input eligible for learning.
    """
    if len(bars) < 41:
        return None
    sample = bars[-41:]
    try:
        closes = [bar["close"] for bar in sample]
        scale = atr(sample[:-1])
        recent = atr(sample[-15:])
        baseline = atr(sample[-41:-15])
        width = sample[-1]["high"] - sample[-1]["low"]
        ticks = [bar["tick_volume"] for bar in sample[-21:]]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                   and math.isfinite(value) and value > 0
                   for value in (scale, recent, baseline, width, *ticks)):
            return None
        travel = math.fsum(abs(right-left) for left, right in zip(closes[-21:-1], closes[-20:]))
        values = {
            "return_1_atr": (closes[-1]-closes[-2])/scale,
            "return_5_atr": (closes[-1]-closes[-6])/scale,
            "ema_gap_atr": (closes[-1]-ema(closes[:-1], 20)[-1])/scale,
            "rsi_centered": (rsi(closes)-50)/50,
            "close_location": 2*(closes[-1]-sample[-1]["low"])/width-1,
            "efficiency_20": abs(closes[-1]-closes[-21])/travel if travel else 0.,
            "volatility_ratio_log": math.log(recent)-math.log(baseline),
            "tick_activity_log": math.log(ticks[-1])-math.log(statistics.median(ticks[:-1])),
        }
        if any(not math.isfinite(value) or abs(value) > 20 for value in values.values()):
            return None
        # A one-unit efficiency is mathematical; tolerate only round-off.
        if values["efficiency_20"] > 1 + 1e-12:
            return None
        values["efficiency_20"] = min(1., values["efficiency_20"])
        def fingerprint(value):
            payload = json.dumps(value, sort_keys=True, ensure_ascii=False,
                                 allow_nan=False, separators=(',', ':')).encode()
            return hashlib.sha256(payload).hexdigest()
        snapshot = [{key: bar[key] for key in ("time", "open", "high", "low", "close", "tick_volume")}
                    for bar in sample]
        feature = {
            "schema": 1, "feature_version": "ohlc-v1",
            "source": ("completed_mt5_ohlc" if data_kind in ("broker", "broker_verified") else
                       "synthetic_completed_ohlc" if data_kind in ("synthetic", "simulation") else
                       "completed_ohlc_undeclared"),
            "symbol": symbol, "timeframe": timeframe,
            "data_time": bar_close_time(sample[-1]["time"], timeframe),
            "input_snapshot_hash": fingerprint(snapshot), "values": values,
        }
        return {**feature, "feature_hash": fingerprint(feature)}
    except (ArithmeticError, ValueError, KeyError, TypeError):
        return None


def _register(id: str, school: str, indicators: list[str], group: str,
              minimum: int = 60, coverage: str = "IMPLEMENTED", requirements: list[str] | None = None):
    def wrapper(fn: Callable):
        REGISTRY[id] = {"id": id, "school": school, "strategy": fn.__name__, "version": "1.0.0",
                        "indicators": indicators, "evidence_group": group, "min_bars": minimum,
                        "coverage": coverage, "data_requirements": requirements or ["completed_ohlc"],
                        "analyzer": fn, "news_requirements": ["calendar"],
                        "agent_type": "local_deterministic_research_agent",
                        "authority": "research_only_no_broker_access",
                        "input_contract": "completed chronological bars; no unfinished or future bar",
                        "output_contract": "inspectable evidence card; committee and risk remain authoritative"}
        return fn
    return wrapper


def registry_manifest() -> list[dict]:
    if 'four_school_confluence' in REGISTRY:
        from .confluence_registry import refresh_contract
        refresh_contract()
    return [{k: v for k, v in meta.items() if k != "analyzer"} for meta in REGISTRY.values()]


def _evidence(kind: str, value, bars: list[dict], label: str, **extra) -> dict:
    return {"kind": kind, "value": value, "time": bars[-1]["time"], "label": arabic(label), **extra}


def _result(side="NEUTRAL", triggered=False, level=None, invalidation=None,
            evidence=None, met=None, missing=None, assumptions=None, status=None, targets=None):
    return dict(direction=side, triggered=triggered, level=level, invalidation=invalidation,
                evidence=evidence or [], met=met or [], missing=missing or [],
                assumptions=assumptions or [], status=status, targets=targets)


def _alternating_pivots(pivots: list[dict]) -> list[dict]:
    """Return an unambiguous causal zig-zag from already-confirmed pivots.

    An outside bar can be both a high and low pivot.  Its order cannot be
    inferred from OHLC, so that bar is excluded instead of inventing a path.
    Consecutive pivots of one kind collapse to the more extreme observation.
    """
    by_index: dict[int, list[dict]] = {}
    for pivot in pivots:
        by_index.setdefault(pivot["index"], []).append(pivot)
    ordered = [group[0] for _, group in sorted(by_index.items()) if len(group) == 1]
    result: list[dict] = []
    for pivot in ordered:
        if not result or result[-1]["kind"] != pivot["kind"]:
            result.append(pivot)
            continue
        more_extreme = (pivot["price"] > result[-1]["price"] if pivot["kind"] == "HIGH"
                        else pivot["price"] < result[-1]["price"])
        if more_extreme:
            result[-1] = pivot
    return result


def _line_through(first: dict, second: dict, index: int) -> float:
    distance = second["index"] - first["index"]
    if distance <= 0:
        raise ValueError("line anchors must have ascending indices")
    slope = (second["price"] - first["price"]) / distance
    return first["price"] + slope * (index - first["index"])


def _linear_fit(points: list[dict]) -> tuple[float, float, float]:
    """Least-squares price/index line and its largest absolute residual."""
    center_x = statistics.fmean(p["index"] for p in points)
    center_y = statistics.fmean(p["price"] for p in points)
    denominator = sum((p["index"] - center_x) ** 2 for p in points)
    if denominator <= 0:
        raise ValueError("line fit needs distinct pivot indices")
    slope = sum((p["index"] - center_x) * (p["price"] - center_y) for p in points) / denominator
    intercept = center_y - slope * center_x
    residual = max(abs(p["price"] - (intercept + slope * p["index"])) for p in points)
    return slope, intercept, residual


def _double_reversal(swings: list[dict], volatility: float) -> dict | None:
    if len(swings) < 3:
        return None
    first, middle, last = swings[-3:]
    if [p["kind"] for p in (first, middle, last)] not in (["HIGH", "LOW", "HIGH"], ["LOW", "HIGH", "LOW"]):
        return None
    bearish = first["kind"] == "HIGH"
    boundary = statistics.fmean((first["price"], last["price"]))
    height = boundary - middle["price"] if bearish else middle["price"] - boundary
    tolerance = max(.35 * volatility, .1 * height)
    separation = last["index"] - first["index"]
    if height < 2 * volatility or abs(first["price"] - last["price"]) > tolerance or not 4 <= separation <= 50:
        return None
    neckline = middle["price"]
    return {
        "name": "double_top" if bearish else "double_bottom",
        "side": "SELL" if bearish else "BUY",
        "pivots": [first, middle, last],
        "neckline_previous": neckline,
        "neckline_now": neckline,
        "invalidation": max(first["price"], last["price"]) if bearish else min(first["price"], last["price"]),
        "target": neckline - height if bearish else neckline + height,
        "height": height,
        "tolerance": tolerance,
        "geometry_rule": "confirmed double-top or double-bottom geometry",
    }


def _head_shoulders(swings: list[dict], volatility: float, previous_index: int,
                    current_index: int) -> dict | None:
    if len(swings) < 5:
        return None
    shoulder_a, neck_a, head, neck_b, shoulder_b = swings[-5:]
    kinds = [p["kind"] for p in (shoulder_a, neck_a, head, neck_b, shoulder_b)]
    if kinds not in (["HIGH", "LOW", "HIGH", "LOW", "HIGH"],
                     ["LOW", "HIGH", "LOW", "HIGH", "LOW"]):
        return None
    bearish = shoulder_a["kind"] == "HIGH"
    neckline_at_head = _line_through(neck_a, neck_b, head["index"])
    height = head["price"] - neckline_at_head if bearish else neckline_at_head - head["price"]
    shoulder_difference = abs(shoulder_a["price"] - shoulder_b["price"])
    left_width = head["index"] - shoulder_a["index"]
    right_width = shoulder_b["index"] - head["index"]
    balanced_time = left_width > 0 and right_width > 0 and max(left_width, right_width) / min(left_width, right_width) <= 2.5
    head_prominent = (head["price"] - max(shoulder_a["price"], shoulder_b["price"]) >= .75 * volatility
                      if bearish else
                      min(shoulder_a["price"], shoulder_b["price"]) - head["price"] >= .75 * volatility)
    shoulders_match = shoulder_difference <= max(.5 * volatility, .2 * height)
    neckline_reasonable = abs(neck_b["price"] - neck_a["price"]) <= .5 * height
    if height < 2 * volatility or not (balanced_time and head_prominent and shoulders_match and neckline_reasonable):
        return None
    neckline_previous = _line_through(neck_a, neck_b, previous_index)
    neckline_now = _line_through(neck_a, neck_b, current_index)
    return {
        "name": "head_and_shoulders" if bearish else "inverse_head_and_shoulders",
        "side": "SELL" if bearish else "BUY",
        "pivots": [shoulder_a, neck_a, head, neck_b, shoulder_b],
        "neckline_previous": neckline_previous,
        "neckline_now": neckline_now,
        "invalidation": head["price"],
        "target": neckline_now - height if bearish else neckline_now + height,
        "height": height,
        "shoulder_difference": shoulder_difference,
        "geometry_rule": "confirmed head-and-shoulders geometry",
    }


@_register("dow_structure", "داو والتحليل الكلاسيكي", ["confirmed pivots"], "structure", 40)
def dow_structure(b, c):
    p = c["pivots"]
    highs = [x for x in p if x["kind"] == "HIGH"]
    lows = [x for x in p if x["kind"] == "LOW"]
    if len(highs) < 2 or len(lows) < 2:
        return _result(missing=["two confirmed highs and lows"])
    up = highs[-1]["price"] > highs[-2]["price"] and lows[-1]["price"] > lows[-2]["price"]
    down = highs[-1]["price"] < highs[-2]["price"] and lows[-1]["price"] < lows[-2]["price"]
    side = "BUY" if up else "SELL" if down else "NEUTRAL"
    level = highs[-1]["price"] if up else lows[-1]["price"] if down else None
    triggered = (up and b[-2]["close"] <= level < b[-1]["close"]) or (down and b[-2]["close"] >= level > b[-1]["close"])
    return _result(side, triggered, level, lows[-1]["price"] if up else highs[-1]["price"] if down else None,
                   evidence=highs[-2:]+lows[-2:], met=["confirmed structure"] if side != "NEUTRAL" else [],
                   missing=[] if triggered else ["fresh close through confirmed swing"])


@_register("engulfing", "حركة السعر والشموع", ["body engulfing"], "candle", 20)
def engulfing(b, c):
    prev, now = b[-2:]
    bull = prev["close"] < prev["open"] and now["close"] > now["open"] and now["open"] <= prev["close"] and now["close"] >= prev["open"]
    bear = prev["close"] > prev["open"] and now["close"] < now["open"] and now["open"] >= prev["close"] and now["close"] <= prev["open"]
    size = abs(now["close"]-now["open"])
    valid = size >= .5*c["atr"] and (bull or bear)
    side = "BUY" if bull else "SELL" if bear else "NEUTRAL"
    return _result(side, valid, now["close"], min(prev["low"], now["low"]) if bull else max(prev["high"], now["high"]),
                   [_evidence("candle", size, b, "engulfing body / ATR", ratio=size/max(c["atr"], 1e-12))],
                   ["engulfing body"] if side != "NEUTRAL" else [], [] if valid else ["body >= 0.5 ATR and engulfing"])


@_register("support_bounce", "الدعم والمقاومة", ["confirmed pivots", "rejection wick"], "structure", 40)
def support_bounce(b, c):
    last, prev, tolerance = b[-1], b[-2], .25*c["atr"]
    lows = [p for p in c["pivots"] if p["kind"] == "LOW"]
    highs = [p for p in c["pivots"] if p["kind"] == "HIGH"]
    support = lows[-1]["price"] if lows else None
    resistance = highs[-1]["price"] if highs else None
    bull = support is not None and last["close"] > support and abs(last["low"]-support) <= tolerance and last["close"] > prev["close"] and last["close"]-last["low"] > .6*(last["high"]-last["low"])
    bear = resistance is not None and last["close"] < resistance and abs(last["high"]-resistance) <= tolerance and last["close"] < prev["close"] and last["high"]-last["close"] > .6*(last["high"]-last["low"])
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear,
                   support if bull else resistance, support if bull else resistance,
                   [_evidence("horizontal_level", support, b, "support"), _evidence("horizontal_level", resistance, b, "resistance")],
                   ["touch and close rejection"] if bull or bear else [], [] if bull or bear else ["confirmed level rejection"])


REGISTRY["support_bounce"]["version"] = "1.1.0"


@_register("classic_reversal_patterns", "الأنماط الانعكاسية الكلاسيكية",
           ["confirmed pivots", "double top/bottom", "head and shoulders", "neckline close"],
           "structure", 60)
def classic_reversal_patterns(b, c):
    swings = _alternating_pivots(c["pivots"])
    pattern = _head_shoulders(swings, c["atr"], len(b)-2, len(b)-1)
    if pattern is None:
        pattern = _double_reversal(swings, c["atr"])
    if pattern is None:
        return _result(
            evidence=[_evidence("reversal_pattern_scan", {"confirmed_swings": swings[-5:]}, b,
                                "classical reversal geometry")],
            missing=["confirmed classical reversal geometry"],
            assumptions=["Pattern names describe explicit OHLC geometry, not a forecast guarantee"],
        )
    side = pattern["side"]
    previous_close, current_close = b[-2]["close"], b[-1]["close"]
    triggered = (previous_close <= pattern["neckline_previous"] and current_close > pattern["neckline_now"]
                 if side == "BUY" else
                 previous_close >= pattern["neckline_previous"] and current_close < pattern["neckline_now"])
    details = {key: value for key, value in pattern.items() if key not in ("pivots", "geometry_rule")}
    details["last_pivot_confirmed_at"] = max(p["confirmed_at"] for p in pattern["pivots"])
    return _result(
        side, triggered, pattern["neckline_now"], pattern["invalidation"],
        [_evidence("reversal_pattern", details, b, "classical reversal geometry"), *pattern["pivots"]],
        [pattern["geometry_rule"]] + (["fresh completed close through the neckline"] if triggered else []),
        [] if triggered else ["neckline break on the latest completed bar"],
        ["Pattern names describe explicit OHLC geometry, not a forecast guarantee"],
        targets=[{"price": pattern["target"], "method": "pattern height projected from neckline", "fraction": 1.0}]
        if triggered else None,
    )


@_register("geometric_triangle_breakout", "الأنماط الهندسية",
           ["confirmed pivots", "least-squares trendlines", "converging triangle", "fresh close breakout"],
           "structure", 60)
def geometric_triangle_breakout(b, c):
    swings = _alternating_pivots(c["pivots"])
    highs = [p for p in swings if p["kind"] == "HIGH"][-3:]
    lows = [p for p in swings if p["kind"] == "LOW"][-3:]
    if len(highs) < 3 or len(lows) < 3:
        return _result(missing=["three confirmed highs and three confirmed lows"])
    high_slope, high_intercept, high_residual = _linear_fit(highs)
    low_slope, low_intercept, low_residual = _linear_fit(lows)
    start_index = min(highs[0]["index"], lows[0]["index"])
    previous_index, current_index = len(b)-2, len(b)-1
    upper_start = high_intercept + high_slope * start_index
    lower_start = low_intercept + low_slope * start_index
    upper_previous = high_intercept + high_slope * previous_index
    lower_previous = low_intercept + low_slope * previous_index
    upper_now = high_intercept + high_slope * current_index
    lower_now = low_intercept + low_slope * current_index
    initial_height, current_height = upper_start-lower_start, upper_now-lower_now
    minimum_slope, flat_slope = .03*c["atr"], .04*c["atr"]
    symmetric = high_slope < -minimum_slope and low_slope > minimum_slope
    ascending = abs(high_slope) <= flat_slope and low_slope > minimum_slope
    descending = high_slope < -minimum_slope and abs(low_slope) <= flat_slope
    pattern_type = ("symmetrical_triangle" if symmetric else "ascending_triangle" if ascending else
                    "descending_triangle" if descending else None)
    span = max(highs[-1]["index"], lows[-1]["index"]) - start_index
    recent = current_index-max(highs[-1]["index"], lows[-1]["index"]) <= 15
    residual_ok = max(high_residual, low_residual) <= .35*c["atr"]
    converging = (pattern_type is not None and 8 <= span <= 60 and recent and residual_ok and
                  initial_height > 0 and .3*c["atr"] <= current_height <= .8*initial_height)
    prior_closes_inside = converging and all(
        low_intercept+low_slope*i-.15*c["atr"] <= b[i]["close"] <=
        high_intercept+high_slope*i+.15*c["atr"]
        for i in range(start_index, current_index)
    )
    bull = prior_closes_inside and b[-2]["close"] <= upper_previous and b[-1]["close"] > upper_now
    bear = prior_closes_inside and b[-2]["close"] >= lower_previous and b[-1]["close"] < lower_now
    side = "BUY" if bull else "SELL" if bear else "NEUTRAL"
    triggered = bull or bear
    geometry = {
        "pattern": pattern_type,
        "upper_slope_per_bar": high_slope,
        "lower_slope_per_bar": low_slope,
        "upper_residual": high_residual,
        "lower_residual": low_residual,
        "initial_height": initial_height,
        "current_height": current_height,
        "upper_now": upper_now,
        "lower_now": lower_now,
        "latest_pivot_confirmed_at": max(p["confirmed_at"] for p in highs+lows),
        "prior_closes_inside": prior_closes_inside,
    }
    target = b[-1]["close"]+initial_height if bull else b[-1]["close"]-initial_height if bear else None
    return _result(
        side, triggered, upper_now if bull else lower_now if bear else None,
        lower_now if bull else upper_now if bear else None,
        [_evidence("geometric_pattern", geometry, b, "converging triangle geometry"), *highs, *lows],
        (["converging triangle geometry"] if converging and prior_closes_inside else []) +
        (["fresh completed close outside triangle"] if triggered else []),
        ([] if triggered else ["triangle breakout on the latest completed bar"])
        if converging and prior_closes_inside else ["confirmed converging triangle"],
        ["Regression lines describe confirmed OHLC pivots; they do not imply exact discretionary trendlines"],
        targets=[{"price": target, "method": "triangle height projected from breakout close", "fraction": 1.0}]
        if triggered else None,
    )


@_register("breakout_retest", "الاختراق وإعادة الاختبار", ["20 bar range"], "structure", 30)
def breakout_retest(b, c):
    history, breakout, retest = b[-23:-2], b[-2], b[-1]
    top, bottom = max(x["high"] for x in history), min(x["low"] for x in history)
    bull = breakout["close"] > top and retest["low"] <= top+.15*c["atr"] and retest["close"] > top
    bear = breakout["close"] < bottom and retest["high"] >= bottom-.15*c["atr"] and retest["close"] < bottom
    level = top if bull else bottom if bear else None
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, level,
                   min(retest["low"], top-.25*c["atr"]) if bull else max(retest["high"], bottom+.25*c["atr"]),
                   [_evidence("horizontal_level", top, b, "prior range top"), _evidence("horizontal_level", bottom, b, "prior range bottom")],
                   ["close breakout", "subsequent retest holds"] if bull or bear else [], [] if bull or bear else ["breakout followed by retest"])


@_register("darvas_box", "Darvas Box", ["confirmed 20 bar box"], "structure", 35)
def darvas_box(b, c):
    window = b[-21:-1]
    top = max(x["high"] for x in window)
    bottom = min(x["low"] for x in window)
    top_index = next(i for i, x in enumerate(window) if x["high"] == top)
    confirmed = top_index <= len(window)-4 and all(x["high"] < top for x in window[top_index+1:])
    bull = confirmed and b[-2]["close"] <= top < b[-1]["close"]
    bear = confirmed and b[-2]["close"] >= bottom > b[-1]["close"]
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, top if bull else bottom,
                   bottom if bull else top, [_evidence("box", {"top": top, "bottom": bottom}, b, "three closes confirm top")],
                   ["box confirmed"] if confirmed else [], [] if bull or bear else ["fresh box breakout"],
                   ["Fixed 20-bar Darvas variant; not every discretionary box interpretation"])


def _mid(b, n):
    return (max(x["high"] for x in b[-n:])+min(x["low"] for x in b[-n:]))/2


@_register("ichimoku_cross", "إيشيموكو", ["Tenkan 9", "Kijun 26", "Senkou 52 lagged 26"], "trend", 80)
def ichimoku_cross(b, c):
    tenkan, kijun = _mid(b, 9), _mid(b, 26)
    previous_tenkan, previous_kijun = _mid(b[:-1], 9), _mid(b[:-1], 26)
    historical = b[:-26]
    span_a, span_b = (_mid(historical, 9)+_mid(historical, 26))/2, _mid(historical, 52)
    bull = previous_tenkan <= previous_kijun and tenkan > kijun and b[-1]["close"] > max(span_a, span_b)
    bear = previous_tenkan >= previous_kijun and tenkan < kijun and b[-1]["close"] < min(span_a, span_b)
    return _result("BUY" if tenkan > kijun else "SELL" if tenkan < kijun else "NEUTRAL", bull or bear, kijun, kijun,
                   [_evidence("ichimoku", {"tenkan": tenkan, "kijun": kijun, "current_cloud_a": span_a, "current_cloud_b": span_b,
                               "cloud_origin_time": historical[-1]["time"]}, b, "cloud calculated 26 completed bars earlier")],
                   (["Tenkan/Kijun directional ordering"] if tenkan != kijun else []) + (["fresh cross outside causal cloud"] if bull or bear else []), [] if bull or bear else ["fresh cross and cloud filter"],
                   ["Chikou drawn retrospectively is not used as predictive input"])


@_register("fib_retracement", "فيبوناتشي", ["confirmed swing", "0.618 retracement"], "structure", 60)
def fib_retracement(b, c):
    p = _alternating_pivots(c["pivots"])
    pair = None
    for a, z in zip(p, p[1:]):
        if a["kind"] != z["kind"] and z["confirmed_at"] <= b[-1]["time"]:
            pair = a, z
    if not pair:
        return _result(missing=["confirmed alternating swing pair"])
    a, z = pair
    bull_swing = a["kind"] == "LOW" and z["kind"] == "HIGH"
    span = abs(z["price"]-a["price"])
    level = z["price"]-.618*span if bull_swing else z["price"]+.618*span
    recovery = z["price"]-.5*span if bull_swing else z["price"]+.5*span
    touched = b[-1]["low"] <= level+.1*c["atr"] if bull_swing else b[-1]["high"] >= level-.1*c["atr"]
    valid = span > 2*c["atr"] and touched and (b[-2]["close"] <= recovery < b[-1]["close"] if bull_swing else b[-2]["close"] >= recovery > b[-1]["close"])
    return _result("BUY" if bull_swing else "SELL", valid, recovery, a["price"],
                   [a, z, _evidence("horizontal_level", level, b, "0.618 pullback"), _evidence("horizontal_level", recovery, b, "0.5 recovery trigger")],
                   ["confirmed swing"] + (["pullback recovery"] if valid else []), [] if valid else ["0.618 touch and fresh 0.5 recovery"])


REGISTRY["fib_retracement"]["version"] = "1.1.0"


@_register("ema_cross", "اتباع الاتجاه", ["EMA 12", "EMA 26", "ATR 14"], "trend", 60)
def ema_cross(b, c):
    closes = [x["close"] for x in b]
    fast, slow = ema(closes, 12), ema(closes, 26)
    bull = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
    bear = fast[-2] >= slow[-2] and fast[-1] < slow[-1]
    return _result("BUY" if fast[-1] > slow[-1] else "SELL" if fast[-1] < slow[-1] else "NEUTRAL", bull or bear, closes[-1],
                   min(x["low"] for x in b[-5:]) if fast[-1] > slow[-1] else max(x["high"] for x in b[-5:]),
                   [_evidence("line", fast[-1], b, "EMA12"), _evidence("line", slow[-1], b, "EMA26")],
                   (["EMA directional ordering"] if fast[-1] != slow[-1] else []) + (["fresh EMA crossover"] if bull or bear else []), [] if bull or bear else ["fresh EMA crossover"])


@_register("rsi_rebound", "مؤشرات الزخم", ["simple RSI 14"], "momentum", 30)
def rsi_rebound(b, c):
    closes = [x["close"] for x in b]
    before, now = rsi(closes[:-1]), rsi(closes)
    bull, bear = before <= 30 < now, before >= 70 > now
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, closes[-1],
                   min(x["low"] for x in b[-5:]) if bull else max(x["high"] for x in b[-5:]),
                   [_evidence("oscillator", {"previous": before, "current": now}, b, "simple RSI14")],
                   ["fresh threshold recovery"] if bull or bear else [], [] if bull or bear else ["RSI recross 30 or 70"],
                   ["Simple rolling gain/loss RSI; deliberately not Wilder smoothing"])


@_register("volatility_breakout", "مؤشرات التقلب", ["Bollinger 20/2", "bandwidth contraction"], "volatility", 65)
def volatility_breakout(b, c):
    closes = [x["close"] for x in b]
    prev = closes[-21:-1]
    mean, sd = statistics.fmean(prev), statistics.pstdev(prev)
    old = statistics.pstdev(closes[-61:-41])
    squeeze = sd < .7*old and sd > 0
    bull = squeeze and closes[-2] <= mean+2*sd < closes[-1]
    bear = squeeze and closes[-2] >= mean-2*sd > closes[-1]
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, mean+2*sd if bull else mean-2*sd, mean,
                   [_evidence("bands", {"mean": mean, "upper": mean+2*sd, "lower": mean-2*sd, "sd": sd, "historical_sd": old}, b, "prior-only bands")],
                   ["contraction"] if squeeze else [], [] if bull or bear else ["contraction then fresh outside-band close"])


@_register("zscore_reversion", "العودة إلى المتوسط والتحليل الإحصائي", ["rolling zscore 40", "mean slope filter"], "statistical", 65)
def zscore_reversion(b, c):
    closes = [x["close"] for x in b]
    training = closes[-42:-2]
    mean, sd = statistics.fmean(training), statistics.pstdev(training)
    if sd <= 0:
        return _result(missing=["nonzero dispersion"])
    before, now = (closes[-2]-mean)/sd, (closes[-1]-mean)/sd
    stable = abs(statistics.fmean(training[-10:])-statistics.fmean(training[:10])) < sd
    bull, bear = stable and before <= -2 < now, stable and before >= 2 > now
    side = "BUY" if bull else "SELL" if bear else "NEUTRAL"
    target = mean if (bull and mean > closes[-1]) or (bear and mean < closes[-1]) else None
    return _result(side, bool((bull or bear) and target), closes[-1],
                   min(x["low"] for x in b[-5:]) if bull else max(x["high"] for x in b[-5:]),
                   [_evidence("zscore", {"mean": mean, "sd": sd, "before": before, "current": now, "stable": stable}, b, "mean estimated before both trigger bars")],
                   ["stable mean"] if stable else [], [] if target else ["fresh zscore recross with valid mean target"],
                   ["No stationarity or Gaussian distribution claim"], targets=[{"price": target, "method": "pre-trigger sample mean", "fraction": 1.0}] if target else None)


@_register("vwap_reclaim", "VWAP وAnchored VWAP", ["typical-price weighted mean", "explicit anchor"], "volume", 30,
           requirements=["completed_ohlc", "bar_real_volume_or_labeled_tick_proxy", "explicit_anchor"])
def vwap_reclaim(b, c):
    anchor = c.get("anchor_time", (b[-1]["time"]//86400)*86400)
    if b[0]["time"] > anchor:
        return _result(status="DATA_MISSING", missing=["history does not cover the declared anchor boundary"])
    anchored = [x for x in b if x["time"] >= anchor]
    if len(anchored) < 3:
        return _result(status="DATA_MISSING", missing=["at least three completed bars after anchor"])
    real = all(x["real_volume"] > 0 for x in anchored)
    key = "real_volume" if real else "tick_volume"
    if any(x[key] <= 0 for x in anchored):
        return _result(status="DATA_MISSING", missing=["positive weights for each anchored bar"])
    def weighted(items):
        return sum(((x["high"]+x["low"]+x["close"])/3)*x[key] for x in items)/sum(x[key] for x in items)
    previous, current = weighted(anchored[:-1]), weighted(anchored)
    bull = b[-2]["close"] <= previous and b[-1]["close"] > current and b[-1]["close"] > b[-1]["open"]
    bear = b[-2]["close"] >= previous and b[-1]["close"] < current and b[-1]["close"] < b[-1]["open"]
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, current, current,
                   [_evidence("weighted_mean", current, b, "bar VWAP" if real else "tick-weighted typical-price proxy", anchor_time=anchor, weight_source=key)],
                   ["fresh weighted-mean reclaim"] if bull or bear else [], [] if bull or bear else ["fresh reclaim"],
                   ["Bar typical-price approximation, not trade-level VWAP", "Real volume is venue/broker supplied, not asserted centralized"] if real else
                   ["Tick volume is activity count, not centralized traded volume", "Tick-weighted mean is a proxy, not genuine transaction VWAP"])


@_register("interasset_confirmation", "العلاقات بين الأصول", ["return correlation 40", "20 bar breakout"], "interasset", 65, "PARTIAL",
           requirements=["completed_ohlc", "explicit_partner_symbol", "aligned_partner_ohlc"])
def interasset_confirmation(b, c):
    # The rule is computationally defined, but the application has no explicit
    # broker-symbol partner mapping yet.  Never guess one from a symbol name or
    # allow the primary instrument to confirm itself.
    partner_symbol = c.get("partner_symbol")
    if not isinstance(partner_symbol, str) or not partner_symbol.strip() or partner_symbol == c.get("symbol"):
        return _result(status="DATA_MISSING", missing=["identified partner and completed aligned bars"])
    partner = c.get("partner_bars")
    if not partner:
        return _result(status="DATA_MISSING", missing=["identified partner and completed aligned bars"])
    try:
        partner = validate_bars(partner, c["timeframe"], c["as_of"])
    except DataError as exc:
        return _result(status="DATA_MISSING", missing=[str(exc)])
    lookup = {x["time"]: x for x in partner}
    paired = [(x, lookup[x["time"]]) for x in b if x["time"] in lookup]
    if len(paired) < 42 or paired[-1][0]["time"] != b[-1]["time"]:
        return _result(status="DATA_MISSING", missing=["42 exactly time-aligned bars"])
    prior = paired[-42:-1]
    x = [math.log(z[0]["close"]/a[0]["close"]) for a, z in zip(prior, prior[1:])]
    y = [math.log(z[1]["close"]/a[1]["close"]) for a, z in zip(prior, prior[1:])]
    sx, sy = statistics.pstdev(x), statistics.pstdev(y)
    corr = sum((a-statistics.fmean(x))*(z-statistics.fmean(y)) for a, z in zip(x, y))/(len(x)*sx*sy) if sx*sy else 0.0
    partner_move = paired[-1][1]["close"]-paired[-2][1]["close"]
    top, bottom = max(z["high"] for z in b[-21:-1]), min(z["low"] for z in b[-21:-1])
    bull = corr >= .7 and partner_move > 0 and b[-2]["close"] <= top < b[-1]["close"]
    bear = corr >= .7 and partner_move < 0 and b[-2]["close"] >= bottom > b[-1]["close"]
    return _result("BUY" if bull else "SELL" if bear else "NEUTRAL", bull or bear, top if bull else bottom,
                   bottom if bull else top, [_evidence("correlation", corr, b, "40 prior log-return pairs", partner=partner_symbol, partner_change=partner_move)],
                   ["return correlation >= 0.7"] if corr >= .7 else [], [] if bull or bear else ["fresh breakout with partner direction"],
                   ["Correlation is unstable and not causal; single-leg confirmation, not a hedged pair strategy"])


@_register("harmonic_abcd", "الهارمونيك: نموذج الأضلاع المتساوية", ["confirmed alternating pivots", "AB/CD ratio"], "structure", 60)
def harmonic_abcd(b, c):
    p = _alternating_pivots(c["pivots"])[-4:]
    assumptions = ["Equal-leg model only; not all harmonic patterns; entry confirmation and tolerances are house rules"]
    if len(p) < 4:
        return _result(missing=["four confirmed alternating harmonic pivots"], assumptions=assumptions)
    a, base, turn, end = p
    bull = [x["kind"] for x in p] == ["HIGH", "LOW", "HIGH", "LOW"]
    sign = 1 if bull else -1
    ab = sign*(a["price"]-base["price"])
    bc = sign*(turn["price"]-base["price"])
    cd = sign*(turn["price"]-end["price"])
    ratios = {"retracement": bc/ab if ab > 0 else None, "equality": cd/ab if ab > 0 else None,
              "projection": cd/bc if bc > 0 else None}
    geometry = (ab > 0 and bc > 0 and cd > 0 and .382 <= bc/ab <= .886
                and .95 <= cd/ab <= 1.05 and 1.13 <= cd/bc <= 2.618)
    evidence = [_evidence("pattern_candidate", ratios, b, "AB=CD candidate ratio"), *p]
    if not geometry:
        return _result(evidence=evidence, missing=["equal-leg ratios outside declared bounds"], assumptions=assumptions)
    # The D pivot is not known until two subsequent bars have closed. The
    # confirmation level is frozen from those bars, not the trigger candle.
    confirmed_index = end["index"]+2
    if not confirmed_index < len(b)-1 <= confirmed_index+8:
        return _result(evidence=evidence, missing=["fresh break after D confirmation within eight bars"], assumptions=assumptions)
    confirmation = b[end["index"]+1:confirmed_index+1]
    level = max(x["high"] for x in confirmation) if bull else min(x["low"] for x in confirmation)
    breached = any(x["low"] < end["price"] if bull else x["high"] > end["price"] for x in b[end["index"]+1:])
    crossed = b[-2]["close"] <= level < b[-1]["close"] if bull else b[-2]["close"] >= level > b[-1]["close"]
    target_valid = b[-1]["close"] < turn["price"] if bull else b[-1]["close"] > turn["price"]
    active = not breached and crossed and target_valid
    return _result("BUY" if bull else "SELL", active, level, end["price"], evidence,
                   ["confirmed equal-leg geometry"]+(["fresh post-confirmation break"] if active else []),
                   [] if active else ["unbroken D and fresh confirmation break before C target"], assumptions,
                   targets=[{"price": turn["price"], "method": "harmonic C pivot target", "fraction": 1.0}] if active else None)


REGISTRY["harmonic_abcd"]["version"] = "2.0.0"


@_register("elliott_candidate", "موجات إليوت", ["confirmed pivots", "alternative wave counts"], "structure", 60, "PARTIAL")
def elliott_candidate(b, c):
    swings = _alternating_pivots(c["pivots"])[-12:]
    counts = []
    for start in range(max(0, len(swings)-5)):
        p = swings[start:start+6]
        if len(p) != 6:
            continue
        sign = 1 if p[0]["kind"] == "LOW" else -1
        x = [sign*v["price"] for v in p]
        wave1, wave3, wave5 = x[1]-x[0], x[3]-x[2], x[5]-x[4]
        rules = {"wave2_above_origin": x[0] < x[2] < x[1],
                 "wave3_beyond_wave1": x[3] > x[1],
                 "wave4_no_overlap": x[1] < x[4] < x[3],
                 "wave3_not_shortest": min(wave1, wave3, wave5) > 0 and wave3 >= min(wave1, wave5),
                 "nontruncated_wave5": x[5] > x[3]}
        counts.append({"direction": "BUY" if sign == 1 else "SELL", "pivots": p, "rules": rules,
                       "geometry_valid": all(rules.values()), "confirmed_at": p[-1]["confirmed_at"]})
    return _result(evidence=[_evidence("wave_candidates", {"candidates": counts, "valid_counts": sum(x["geometry_valid"] for x in counts),
                                 "nested_structure_verified": False}, b, "nonunique counts")],
                   missing=["complete nesting/alternation rules and validated execution trigger"],
                   assumptions=["Counts are alternatives; no unique Elliott interpretation or future wave is asserted"])


REGISTRY["elliott_candidate"]["version"] = "1.1.0"


@_register("wyckoff_spring", "وايكوف", ["range", "spring proxy"], "structure", 60, "PARTIAL")
def wyckoff_spring(b, c):
    bottom, top = min(x["low"] for x in b[-41:-1]), max(x["high"] for x in b[-41:-1])
    spring = b[-1]["low"] < bottom < b[-1]["close"]
    return _result(evidence=[_evidence("range", {"bottom": bottom, "top": top, "spring_proxy": spring,
                                 "alternatives": ["accumulation candidate", "redistribution candidate", "ordinary range"]}, b, "phase uncertainty")],
                   missing=["phase A-E formal inference and reliable traded-volume confirmation"],
                   assumptions=["A sweep/reclaim is not proof of accumulation or institutional intent"])


@_register("smc_ict_proxy", "SMC وICT والسيولة", ["three-bar gap", "sweep", "structure"], "structure", 60, "PARTIAL")
def smc_ict_proxy(b, c):
    a, mid, z = b[-3:]
    bullish_gap, bearish_gap = a["high"] < z["low"], a["low"] > z["high"]
    return _result(evidence=[_evidence("imbalance_proxy", {"bullish_gap": bullish_gap, "bearish_gap": bearish_gap,
                                "bull_zone": [a["high"], z["low"]] if bullish_gap else None,
                                "bear_zone": [z["high"], a["low"]] if bearish_gap else None}, b, "OHLC FVG proxy")],
                   missing=["formal session model, order-block lifecycle and independently validated liquidity trigger"],
                   assumptions=["Three-bar gap does not identify actual orders or institutional order flow"])


@_register("supply_demand_proxy", "العرض والطلب", ["displacement base proxy"], "structure", 60, "PARTIAL")
def supply_demand_proxy(b, c):
    base, impulse = b[-2:]
    displacement = abs(impulse["close"]-impulse["open"]) > 1.5*c["atr"]
    return _result(evidence=[_evidence("zone_candidate", {"low": base["low"], "high": base["high"], "displacement": displacement}, b, "prior candle base proxy")],
                   missing=["zone freshness/lifecycle and retest execution validation"], assumptions=["OHLC base is not observed supply or demand orders"])


@_register("smt_proxy", "SMT", ["paired swing divergence"], "interasset", 60, "PARTIAL", ["completed_ohlc", "aligned_partner_ohlc"])
def smt_proxy(b, c):
    return _result(missing=["partner-specific swing synchronization, divergence lifecycle and execution validation"],
                   assumptions=["No SMT direction inferred from a missing partner"])


@_register("seasonality", "الموسمية", ["calendar-conditioned returns"], "statistical", 60, "PARTIAL", ["multi_year_adjusted_history"])
def seasonality(b, c):
    return _result(missing=["multiple years, adjusted contract history and calendar bucket OOS validation"],
                   assumptions=["300 intraday bars cannot establish seasonality"])


@_register("gann", "جان ومربع التسعة والدورات الزمنية", [], "time_geometry", 1, "UNIMPLEMENTED")
def gann(b, c):
    return _result(missing=["declared price/time normalization, square-nine rules and validated execution definition"])


@_register("order_flow", "تدفق الأوامر", [], "order_flow", 1, "UNIMPLEMENTED", ["signed_trades", "historical_depth"])
def order_flow(b, c):
    return _result(missing=["signed trades and reliable historical depth/venue data"],
                   assumptions=["MT5 OHLC/tick counts cannot produce real delta or footprint"])


def analyze_strategy(strategy_id: str, symbol: str, timeframe: str, bars: list[dict],
                     as_of: float | None = None, context: dict | None = None, *, _shared=None) -> dict:
    try:
        as_of = time.time() if as_of is None else float("nan") if isinstance(as_of, bool) else float(as_of)
    except (TypeError, ValueError, OverflowError):
        as_of = float("nan")
    meta = REGISTRY[strategy_id]
    data_kind = (context or {}).get("data_kind", "unverified")
    source_label = ("broker completed OHLC" if data_kind in ("broker", "broker_verified") else
                    "synthetic completed OHLC" if data_kind in ("synthetic", "simulation") else
                    "completed OHLC with undeclared provenance")
    card = {k: v for k, v in meta.items() if k != "analyzer"}
    card.update(strategy_id=strategy_id, registry_id=strategy_id, symbol=symbol, timeframe=timeframe, direction="NEUTRAL", status="WAIT", quality="UNKNOWN",
                scenario=arabic("wait for a complete entry setup"), evidence=[], conditions_met=[], conditions_missing=[],
                entry=None, invalidation=None, stop=None, targets=[], alternative=arabic("wait or opposing confirmed setup"),
                data_time=None, valid_at=as_of if math.isfinite(as_of) else None, expires_at=as_of if math.isfinite(as_of) else 0,
                assumptions=[], sources=[arabic(source_label)], data_kind=data_kind,
                gaps=[], score=0.0, score_formula="100 × عدد الشروط المتحققة ÷ إجمالي الشروط؛ صفر عند غياب الشروط. هذه درجة تحقق القواعد وليست احتمال نجاح",
                execution_plan=None, actionable=False)
    try:
        # analyze_all owns a validated snapshot. Give each model detached rows;
        # standalone calls still validate their raw input in full.
        b = ([dict(row) for row in _shared['validated_bars']] if _shared is not None
             else validate_bars(bars, timeframe, as_of))
    except DataError as exc:
        card.update(status="DATA_INVALID", gaps=[arabic(str(exc))], conditions_missing=[arabic(str(exc))])
        return card
    if b:
        card["data_time"] = bar_close_time(b[-1]["time"],timeframe)
        card["expires_at"] = bar_close_time(card["data_time"],timeframe)
    identity = f"{strategy_id}:{meta['version']}:{symbol}:{timeframe}:{card['data_time']}"
    card["id"] = hashlib.sha256(identity.encode()).hexdigest()[:32]
    if meta["coverage"] == "UNIMPLEMENTED":
        result = meta["analyzer"](b, {})
        card.update(status="UNIMPLEMENTED", conditions_missing=[arabic(x) for x in result["missing"]], gaps=[arabic(x) for x in result["missing"]], assumptions=[arabic(x) for x in result["assumptions"]])
        return card
    if len(b) < meta["min_bars"]:
        card.update(status="DATA_MISSING", conditions_missing=[f"يلزم {meta['min_bars']} شمعة مكتملة؛ المتاح {len(b)}"], gaps=[arabic("insufficient history")])
        return card
    if as_of >= card["expires_at"]:
        card.update(status="STALE", conditions_missing=[arabic("last completed bar is stale")], quality="STALE")
        return card
    a = _shared['atr'] if _shared is not None else atr(b)
    if a <= 0:
        card.update(status="DATA_INVALID", gaps=[arabic("zero ATR")], conditions_missing=[arabic("nonzero tradable range")])
        return card
    card["chart_features"] = copy.deepcopy(_shared['chart_features']) if _shared is not None else _chart_features(symbol, timeframe, b, data_kind)
    c = dict(context or {})
    c.update(atr=a, pivots=[dict(p) for p in _shared['pivots']] if _shared is not None else causal_pivots(b, as_of=as_of, timeframe=timeframe), timeframe=timeframe, as_of=as_of,
             symbol=symbol)
    result = meta["analyzer"](b, c)
    market_regime = copy.deepcopy(_shared['regime']) if _shared is not None else specialists.regime(b)
    card["market_regime"] = market_regime
    scope = specialists.SPECS.get(strategy_id)
    if scope and market_regime["name"] not in scope["allowed_regimes"]:
        result = _result(missing=["market regime outside declared scope"],
                         evidence=result["evidence"], assumptions=result["assumptions"])
    card.update(direction=result["direction"], evidence=result["evidence"], conditions_met=[arabic(x) for x in result["met"]],
                conditions_missing=[arabic(x) for x in result["missing"]], assumptions=[arabic(x) for x in result["assumptions"]], quality="VALIDATED_OHLC",
                status=result["status"] or ("PARTIAL" if meta["coverage"] == "PARTIAL" else "READY" if result["triggered"] else "WAIT"))
    denominator = len(result["met"])+len(result["missing"])
    card["score"] = round(100*len(result["met"])/denominator, 2) if denominator else 0.0
    card["gaps"] = [arabic(x) for x in result["missing"]]
    if result["direction"] in ("BUY", "SELL"):
        card["scenario"] = ("شراء" if result["direction"] == "BUY" else "بيع") + " عند تحقق قاعدة الدخول المعلنة على شمعة مكتملة فقط"
    if result["invalidation"] is not None and result["direction"] in ("BUY", "SELL"):
        card["invalidation"] = {"price": result["invalidation"], "condition": arabic("completed close beyond the analysis level"),
                                "evaluation": "completed_bar_close"}
    def blocked_price_plan(reason):
        missing = [arabic(reason)]
        count = len(card["conditions_met"])
        card.update(status="WAIT", conditions_missing=missing, gaps=missing,
                    score=round(100*count/(count+len(missing)), 2))
        return card
    if card["status"] == "READY" and meta["coverage"] == "IMPLEMENTED":
        side, entry = result["direction"], b[-1]["close"]
        structural = result["invalidation"]
        stop = min(structural if structural is not None else entry-a, entry-.5*a)-.1*a if side == "BUY" else max(structural if structural is not None else entry+a, entry+.5*a)+.1*a
        risk = abs(entry-stop)
        targets = result["targets"] or [{"price": entry+2*risk if side == "BUY" else entry-2*risk, "method": "2 * proposed stop distance", "method_code": "DEFAULT_STRUCTURAL_2R", "fraction": 1.0}]
        if any(isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0
               for price in (entry, stop, risk, *(target["price"] for target in targets))):
            return blocked_price_plan("execution prices must be finite and positive")
        if any(x["price"] <= 0 or (x["price"] <= entry if side == "BUY" else x["price"] >= entry) for x in targets):
            return blocked_price_plan("positive target in trade direction")
        card.update(entry={"price": entry, "zone": [entry-.15*a, entry+.15*a], "triggered": True,
                           "trigger": arabic("declared rule on the latest completed bar; quote must remain inside zone"),
                           "signal_bar_time": b[-1]["time"]}, stop={"price": stop, "method": arabic("structure with 0.1 ATR buffer and >=0.6 ATR risk")},
                    targets=targets, actionable=True, execution_plan={"take_profit": "FULL", "partial_targets": [], "max_hold_bars": 12,
                                "timeframe": timeframe, "break_even_at_r": None, "allow_addition": False,
                                "invalidation": card["invalidation"], "stop_may_only_tighten": True})
        for target in card["targets"]:
            target["method"] = arabic(target["method"])
    return card


def analyze_all(symbol: str, timeframe: str, bars: list[dict], as_of: float | None = None,
                context: dict | None = None) -> list[dict]:
    # Validate the raw snapshot once, then isolate every model's rows/evidence.
    # Invalid snapshots retain the same per-card error reporting as standalone.
    now = time.time() if as_of is None else as_of
    shared = None
    try:
        data = validate_bars(bars, timeframe, now)
        if data:
            shared = {'validated_bars': data, 'atr': atr(data), 'pivots': causal_pivots(data, as_of=now, timeframe=timeframe),
                      'chart_features': _chart_features(symbol, timeframe, data, (context or {}).get('data_kind', 'unverified')),
                      'regime': specialists.regime(data)}
    except DataError:
        pass
    return [analyze_strategy(id, symbol, timeframe, bars, now, context, _shared=shared) for id in REGISTRY]


# Import after all shared primitives exist; registration is deterministic.
from . import specialists
from . import local_models
from . import confluence_registry

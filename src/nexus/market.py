"""Resource bounded all-symbol universe scan with truthful completion counters."""
import math
import time

from .broker import TIMEFRAMES as TIMEFRAMES  # noqa: PLC0414 -- Explicit public re-export or deterministic side-effect model registration; removing it breaks compatibility.
from .broker import BrokerError
from .timeframes import bar_close_time


def classify(info):
    path = (info.get("path", "") + " " + info.get("description", "")).lower()
    calc = info.get("trade_calc_mode")
    base, profit = info.get("currency_base", ""), info.get("currency_profit", "")
    if base in ("XAU", "XAG", "XPT", "XPD") or any(x in path for x in ("metal", "gold", "silver")):
        return "metals"
    if any(x in path for x in ("energy", "oil", "gas", "crude")):
        return "energy"
    if calc in (0, 5) and base and profit:
        return "forex"
    if any(x in path for x in ("index", "indice", "indices")) or calc == 3:
        return "indices"
    if calc in (32, 38) or any(x in path for x in ("stock", "share", "equities")):
        return "stocks"
    # Official MT5 ENUM_SYMBOL_CALC_MODE: 1/33 are futures; 2/4 are
    # CFDs, 34/36 are options. Expiry alone must not relabel options.
    if calc in (1, 33) or (info.get("expiration_time", 0) and calc not in (34, 36)):
        return "futures"
    if "crypto" in path:
        return "crypto"
    return "other"


def validate_bars(bars, timeframe, now):
    reasons=[]
    if len(bars)<100:
        reasons.append("تاريخ أقل من 100 شمعة مكتملة")
    last=-1
    for b in bars:
        try:
            values=[float(b[k]) for k in ("time","open","high","low","close")]
            if not all(math.isfinite(v) for v in values) or min(values[1:])<=0:
                raise ValueError()
            if b["time"]<=last or bar_close_time(b["time"],timeframe)>now:
                reasons.append("ترتيب زمني غير صالح أو شمعة مستقبلية/غير مكتملة"); break
            if b["low"]>min(b["open"],b["close"]) or b["high"]<max(b["open"],b["close"]) or b["low"]>b["high"]:
                reasons.append("OHLC غير صالح"); break
            last=b["time"]
        except (KeyError,TypeError,ValueError):
            reasons.append("حقول أسعار مفقودة أو غير صالحة"); break
    return reasons


def spread_filter_required(settings, account, simulation=False):
    """Legacy compatibility hook: spread is never an independent exclusion.

    Spread remains part of the executable quote and monetary cost/risk
    calculations. This hook controls only the old scanner's warning label; it
    must not reintroduce an ATR-, session-, or account-dependent spread veto.
    """
    del settings, account, simulation
    return False


class UniverseScanner:
    def __init__(self, broker, clock=time.time):
        self.broker,self.clock=broker,clock
        self.spread_filter=True
        self.rows={}; self.queue=[]; self.started=0; self.finished=0; self.cycle=0

    def configure_spread_warning(self, enabled):
        """Change the display warning without invalidating measured eligibility."""
        self.spread_filter=bool(enabled)
        if not self.spread_filter:
            for row in self.rows.values():
                row["warnings"] = []
                row["spread_filter_enforced"] = False
                row["spread_rejection_enabled"] = False

    def begin(self):
        symbols=self.broker.symbols()
        self.started=self.clock(); self.finished=0; self.cycle+=1
        self.queue=list(symbols)
        self.rows={s["name"]:{"symbol":s["name"],"name":s["name"],"category":classify(s),"checked":False,
            "eligible":False,"status":"PENDING","reasons":["لم يُفحص في هذه الدورة"],"warnings":[],"last_scan":None,"spec":s} for s in symbols}

    def step(self, limit=12):
        for _ in range(min(limit,len(self.queue))):
            info=self.queue.pop(0); name=info["name"]; row=self.rows[name]; reasons=[]; warnings=[]; now=self.clock()
            try:
                if info.get("custom"):
                    reasons.append("رمز اصطناعي في MT5؛ غير معتمد للتنفيذ")
                if info.get("trade_mode") not in (1,2,4):
                    reasons.append("الدخول الجديد غير مسموح لهذا العقد")
                if info.get("expiration_time",0) and info["expiration_time"]<=now+3600:
                    reasons.append("العقد منتهي أو قريب الانتهاء")
                if info.get("start_time",0)>now:
                    reasons.append("العقد لم يبدأ")
                for key in ("point","trade_tick_size","volume_min","volume_max","volume_step","trade_contract_size"):
                    if not isinstance(info.get(key), (float,int)) or not math.isfinite(info[key]) or info[key]<=0:
                        reasons.append("خصائص عقد ناقصة: "+key)
                if not reasons:
                    self.broker.select(name)
                    tick=self.broker.tick(name); session=self.broker.session(name)
                    row.update(tick=tick,session=session,bid=tick["bid"],ask=tick["ask"],spread=tick["ask"]-tick["bid"])
                    if not session.get("known"):
                        reasons.append(session.get("reason","جلسات غير معروفة"))
                    elif not session.get("open"):
                        reasons.append("السوق مغلق حسب جلسة الوسيط")
                    if not 0<tick["bid"]<=tick["ask"] or now-tick["time"]>60 or tick["time"]>now+5:
                        reasons.append("الأسعار مفقودة أو قديمة أو غير سليمة")
                    bars=self.broker.bars(name,"H1",120)
                    reasons+=validate_bars(bars,"H1",now)
                    row["history_count"]=len(bars)
                    if bars:
                        row["data_time"]=bars[-1]["time"]+3600
                        ranges=[b["high"]-b["low"] for b in bars[-14:]]
                        atr=sum(ranges)/len(ranges)
                        if self.spread_filter and (atr<=0 or row["spread"]>atr*.20):
                            warnings.append("السبريد مقاس للعرض؛ لا يُرفض منفردًا وتدخل تكلفته الفعلية في حساب المخاطرة")
                        row["liquidity_score"]=max(0.,1-row["spread"]/atr) if atr>0 else 0.
            except (BrokerError,ValueError,KeyError,TypeError) as exc:
                reasons.append(str(exc))
            row["spread_filter_enforced"]=False
            row["spread_rejection_enabled"]=False
            row["warnings"]=warnings
            row.update(checked=True,eligible=not reasons,status="ELIGIBLE" if not reasons else "EXCLUDED",
                       reasons=reasons,last_scan=now)
        if not self.queue and not self.finished:
            self.finished=self.clock()
        return self.snapshot()

    def snapshot(self):
        rows=list(self.rows.values()); checked=sum(r["checked"] for r in rows); eligible=sum(r["eligible"] for r in rows)
        return {"discovered": len(rows),"checked": checked,"eligible": eligible,"excluded": checked-eligible,
            "complete": bool(self.finished),"cycle_started": self.started,"cycle_finished": self.finished,"cycle": self.cycle,"rows": rows}

    def candidates(self, limit=12):
        return sorted((r for r in self.rows.values() if r["eligible"]),key=lambda r:r.get("liquidity_score",0),reverse=True)[:limit]

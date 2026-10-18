"""Bounded MT5-only models replacing broad research placeholders.

IMPLEMENTED refers to the explicit algorithm below, never an entire school.
All model outputs still pass through the same committee and risk authority.
"""
import math
import statistics
from datetime import UTC, datetime

from . import strategies as st
from .specialists import first_return, signal


def wait(b, reason="local model conditions incomplete", details=None, missing=False):
    return st._result(status="DATA_MISSING" if missing else None, missing=[reason],
                      evidence=[st._evidence("local_model", details or {}, b, "local model evidence")])


def aligned(b,c):
    name=c.get("partner_symbol")
    if not name or name==c.get("symbol") or not c.get("partner_bars"):
        return None
    try:
        p=st.validate_bars([x for x in c["partner_bars"] if st.bar_close_time(x["time"],c["timeframe"])<=c["as_of"]],c["timeframe"],c["as_of"])
    except (st.DataError,KeyError,TypeError):return None
    lookup={x["time"]:x for x in p}
    pairs=[(x,lookup[x["time"]]) for x in b if x["time"] in lookup]
    if len(pairs)<42 or pairs[-1][0]["time"]!=b[-1]["time"]:return None
    return pairs


def correlation(pairs):
    return st.paired_log_correlation(pairs)


def interasset(b,c):
    pairs=aligned(b,c)
    if pairs is None:return wait(b,"aligned declared MT5 partner required",missing=True)
    # The old complete arithmetic is retained; its previous missing wiring is
    # now supplied by Engine's declared metadata mapping.
    return st.interasset_confirmation(b,{**c,"partner_bars":[p[1] for p in pairs]})


def smt(b,c):
    pairs=aligned(b,c)
    if pairs is None:return wait(b,"aligned declared MT5 partner required",missing=True)
    own=[p[0] for p in pairs];partner=[p[1] for p in pairs]
    x,y=own[-1],partner[-1]
    lo=min(z["low"] for z in own[-21:-1]);hi=max(z["high"] for z in own[-21:-1])
    plo=min(z["low"] for z in partner[-21:-1]);phi=max(z["high"] for z in partner[-21:-1])
    corr=correlation(pairs)
    bull=corr>=.7 and x["low"]<lo<x["close"] and y["low"]>=plo and x["close"]>own[-2]["close"]
    bear=corr>=.7 and x["high"]>hi>x["close"] and y["high"]<=phi and x["close"]<own[-2]["close"]
    return signal(b,bull,bear,x["low"],x["high"],{"partner": c["partner_symbol"],"correlation": corr,"low": lo,"high": hi})


def wave12(b,c):
    p=st._alternating_pivots(c["pivots"])[-3:]
    if len(p)<3:return wait(b)
    a,peak,retrace=p;bull=a["kind"]=="LOW";sign=1 if bull else -1
    wave=sign*(peak["price"]-a["price"])
    pullback=sign*(peak["price"]-retrace["price"])
    geometry=wave>=2*c["atr"] and .382<=pullback/wave<=.786 if wave>0 else False
    age=len(b)-1-(retrace["index"]+2)
    intact=all(x["low"]>=retrace["price"] if bull else x["high"]<=retrace["price"] for x in b[retrace["index"]+1:])
    trigger=(b[-2]["close"]<=peak["price"]<b[-1]["close"] if bull else b[-2]["close"]>=peak["price"]>b[-1]["close"])
    active=geometry and 1<=age<=16 and intact and trigger
    result=signal(b,active and bull,active and not bull,retrace["price"],retrace["price"],
                  {"pivots": p,"retracement": pullback/wave if wave>0 else None,"age": age})
    result["assumptions"].append("Local wave 1-2 hypothesis; nested Elliott counts and future wave completion are not asserted")
    return result


def spring_test(b,c):
    for index in range(len(b)-3,len(b)-9,-1):
        prior=b[index-40:index];spring=b[index];post=b[index+1:-1];x=b[-1]
        if len(prior)!=40 or not post:continue
        lo=min(z["low"] for z in prior);hi=max(z["high"] for z in prior);scale=st.atr(prior)
        if scale<=0 or hi-lo<3*scale or abs(prior[-1]["close"]-prior[0]["close"])>.25*(hi-lo):continue
        if min(x.get("tick_volume",0),spring.get("tick_volume",0))<=0:continue
        light=x["tick_volume"]<=spring["tick_volume"]
        bull=(spring["low"]<lo<spring["close"]<hi and max(z["close"] for z in post)>lo+scale
              and all(z["low"]>lo+.25*scale for z in post) and lo<=x["low"]<=lo+.25*scale
              and x["close"]>b[-2]["close"] and x["close"]<(lo+hi)/2 and light)
        bear=(spring["high"]>hi>spring["close"]>lo and min(z["close"] for z in post)<hi-scale
              and all(z["high"]<hi-.25*scale for z in post) and hi-.25*scale<=x["high"]<=hi
              and x["close"]<b[-2]["close"] and x["close"]>(lo+hi)/2 and light)
        if bull or bear:
            result=signal(b,bull,bear,spring["low"],spring["high"],{"low": lo,"high": hi,"spring_time": spring["time"]}, (lo+hi)/2)
            result["assumptions"].append("Range spring/test with tick-count proxy; no full Wyckoff phase or institutional intent inference")
            return result
    return wait(b)


def liquidity_gap(b,c):
    result=first_return(b,"gap")
    if not result["triggered"]:return result
    details=result["evidence"][0]["value"]
    end=next(i for i,x in enumerate(b) if x["time"]==details["formation_time"])
    sweep=b[end-2];prior=b[end-12:end-2]
    if len(prior)!=10:return wait(b)
    lo=min(x["low"] for x in prior);hi=max(x["high"] for x in prior)
    valid=(sweep["low"]<lo<sweep["close"] if result["direction"]=="BUY" else sweep["high"]>hi>sweep["close"])
    if not valid:return wait(b,"prior sweep required for local liquidity model",details)
    result["assumptions"].append("Local sweep plus gap return; no institutional orders or full ICT interpretation")
    return result


def supply_zone(b,c):
    result=first_return(b,"base")
    if not result["triggered"]:return result
    mean=st.ema([x["close"] for x in b[:-1]],20)[-1]
    if (result["direction"]=="BUY" and b[-1]["close"]<=mean) or (result["direction"]=="SELL" and b[-1]["close"]>=mean):
        return wait(b)
    result["assumptions"].append("First-return OHLC zone with prior EMA filter; not observed supply or demand orders")
    return result


def root_grid(b,c):
    p=st._alternating_pivots(c["pivots"])
    if not p:return wait(b)
    anchor=p[-1];bull=anchor["kind"]=="LOW";unit=st.atr(b[:anchor["index"]+1])
    if unit<=0:return wait(b)
    root=math.sqrt(anchor["price"]/unit);shift=root+(.25 if bull else -.25)
    if shift<=0:return wait(b)
    level=unit*shift*shift
    age=len(b)-1-(anchor["index"]+2)
    intact=all(x["low"]>=anchor["price"] if bull else x["high"]<=anchor["price"] for x in b[anchor["index"]+1:])
    cross=b[-2]["close"]<=level<b[-1]["close"] if bull else b[-2]["close"]>=level>b[-1]["close"]
    active=1<=age<=32 and intact and cross
    result=signal(b,active and bull,active and not bull,anchor["price"],anchor["price"],{"level": level,"unit": unit,"anchor": anchor,"age": age})
    result["assumptions"].append("Volatility-normalized square-root grid is a house model; not complete Gann theory or a natural time cycle")
    return result


def activity_flow(b,c):
    sample=b[-21:];volumes=[x.get("tick_volume",0) for x in sample]
    if any(v<=0 for v in volumes):return wait(b,"positive bar tick counts required for local activity proxy",missing=True)
    def pressure(x):
        span=x["high"]-x["low"]
        return (2*x["close"]-x["high"]-x["low"])/span if span>0 else 0.
    x=b[-1];previous,current=pressure(b[-2]),pressure(x)
    active=volumes[-1]>=1.2*statistics.median(volumes[:-1])
    hi=max(z["high"] for z in b[-6:-1]);lo=min(z["low"] for z in b[-6:-1])
    result=signal(b,active and previous<=.35<current and x["close"]>hi,
                  active and previous>=-.35>current and x["close"]<lo,lo,hi,
                  {"previous": previous,"current": current,"activity_ratio": volumes[-1]/statistics.median(volumes[:-1])})
    result["assumptions"].append("Bar tick activity and close-location proxy; not real order flow or signed volume")
    return result


def monthly_bias(b,c):
    info=c.get("symbol_info",{});base=info.get("currency_base","");quote=info.get("currency_profit","")
    currencies={"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD","ZAR","MXN","HKD","SGD","NOK","SEK","PLN","TRY","CNH"}
    if base not in currencies or quote not in currencies or base==quote:
        return wait(b,"local monthly model supports declared currency pairs only",missing=True)
    daily=c.get("daily_bars",[])
    try:daily=st.validate_bars([x for x in daily if x["time"]+86400<=c["as_of"]],"D1",c["as_of"])
    except (st.DataError,KeyError,TypeError):return wait(b,"completed multi-year MT5 daily history required",missing=True)
    now=datetime.fromtimestamp(c["as_of"],UTC)
    groups={}
    for x in daily:
        d=datetime.fromtimestamp(x["time"],UTC)
        if d.month==now.month and d.year<now.year:groups.setdefault(d.year,[]).append(x)
    returns=[]
    for group in groups.values():
        first=datetime.fromtimestamp(group[0]["time"],UTC);last=datetime.fromtimestamp(group[-1]["time"],UTC)
        if len(group)>=15 and first.day<=7 and last.day>=24:
            value=group[-1]["close"]/group[0]["open"]-1
            if abs(value)>.5:return wait(b,"historical discontinuity in local monthly sample",missing=True)
            returns.append(value)
    if len(returns)<3:return wait(b,"three complete earlier same-month samples required",missing=True)
    mean=statistics.fmean(returns);sd=statistics.stdev(returns)
    score=mean/(sd/math.sqrt(len(returns))) if sd>0 else 0.
    agreement=sum(x*mean>0 for x in returns)/len(returns)
    hi=max(x["high"] for x in b[-21:-1]);lo=min(x["low"] for x in b[-21:-1])
    result=signal(b,score>=2 and agreement>=2/3 and b[-2]["close"]<=hi<b[-1]["close"],
                  score<=-2 and agreement>=2/3 and b[-2]["close"]>=lo>b[-1]["close"],lo,hi,
                  {"sample_count": len(returns),"mean": mean,"score": score,"agreement": agreement,"month": now.month})
    result["assumptions"].append("Raw broker FX monthly sample; no adjusted futures history, stationarity or seasonal profitability claim")
    return result


MODELS={
    "interasset_confirmation":(interasset,"تأكيد أصل مقابل محدد","Declared paired-asset confirmation",["completed_ohlc","explicit_partner_symbol","aligned_partner_ohlc"],"interasset"),
    "smt_proxy":(smt,"اختلاف نطاق أصلين: نموذج محلي","Paired range divergence: local model",["completed_ohlc","explicit_partner_symbol","aligned_partner_ohlc"],"interasset"),
    "elliott_candidate":(wave12,"إليوت: فرضية موجتين محلية","Elliott: local wave 1-2 hypothesis",["completed_ohlc"],"structure"),
    "wyckoff_spring":(spring_test,"وايكوف: نموذج كسر واختبار محلي","Wyckoff: local spring-test model",["completed_ohlc","positive_tick_volume"],"structure"),
    "smc_ict_proxy":(liquidity_gap,"السيولة: سحب مستوى وعودة فجوة","Liquidity: sweep and gap return",["completed_ohlc"],"structure"),
    "supply_demand_proxy":(supply_zone,"العرض والطلب: عودة منطقة محلية","Supply/demand: local zone return",["completed_ohlc"],"structure"),
    "gann":(root_grid,"جان: شبكة جذر سعر معيارية","Gann: normalized price-root grid",["completed_ohlc"],"structure"),
    "order_flow":(activity_flow,"تدفق النشاط: تقريب من شموع التكات","Activity flow: bar-tick approximation",["completed_ohlc","positive_tick_volume"],"volume"),
    "seasonality":(monthly_bias,"موسمية العملات: نموذج شهري محلي","FX seasonality: local monthly model",["completed_ohlc","broker_daily_history"],"statistical"),
}

# Exact bounded rules exposed in both languages, alongside the executable source.
RULES = {
    "interasset_confirmation": ("Prior 40-return correlation at least 0.7; new 20-bar breakout confirmed by the declared paired asset.", "ارتباط أربعين عائدًا سابقًا لا يقل عن 0.7، مع كسر جديد لنطاق عشرين شمعة يؤكده الأصل المقابل المحدد."),
    "smt_proxy": ("Correlation at least 0.7; one asset sweeps its prior 20-bar boundary and returns while its declared partner does not sweep.", "ارتباط لا يقل عن 0.7؛ يسحب أصل حد عشرين شمعة ويعود داخله دون أن يسحب الأصل المقابل حده."),
    "elliott_candidate": ("Three confirmed alternating pivots; first leg at least 2 ATR, retracement 0.382–0.786, fresh first-leg break within 16 bars with retracement intact.", "ثلاثة محاور مؤكدة متناوبة؛ الضلع الأول ضعفا نطاق التقلب على الأقل والتصحيح بين 38.2 و78.6 بالمئة، ثم كسر جديد خلال ست عشرة شمعة مع سلامة قاع أو قمة التصحيح."),
    "wyckoff_spring": ("40-bar sideways range; boundary sweep, departure, then lighter tick-count retest within eight bars; target range midpoint.", "نطاق جانبي لأربعين شمعة؛ سحب حد ثم ابتعاد وإعادة اختبار بعدد تكات أقل خلال ثماني شموع، والهدف منتصف النطاق."),
    "smc_ict_proxy": ("Sweep of a prior 10-bar boundary before a displacement gap; first valid gap return within 20 bars.", "سحب حد عشر شموع قبل فجوة اندفاع؛ أول عودة صالحة للفجوة خلال عشرين شمعة."),
    "supply_demand_proxy": ("First return to an unbroken displacement base within 20 bars, aligned with the prior 20-bar EMA.", "أول عودة إلى أساس اندفاع غير مكسور خلال عشرين شمعة، في اتجاه المتوسط الأسي السابق لعشرين شمعة."),
    "gann": ("House rule: ATR-normalized square-root level shifted by 0.25 from a confirmed pivot; fresh cross within 32 bars with anchor intact.", "قاعدة خاصة: مستوى جذر سعر معياري بنطاق التقلب وإزاحة ربع وحدة من محور مؤكد؛ عبور جديد خلال اثنتين وثلاثين شمعة مع سلامة المحور."),
    "order_flow": ("Bar tick count at least 1.2 times the prior median; close-location pressure crosses ±0.35 and breaks a five-bar boundary. No signed trade volume or depth.", "عدد تكات لا يقل عن 1.2 من الوسيط السابق؛ ضغط موقع الإغلاق يعبر موجب أو سالب 0.35 مع كسر حد خمس شموع. لا يستخدم حجم صفقات محدد الاتجاه أو عمق سوق."),
    "seasonality": ("Declared FX only; at least three completed prior same-month samples from MT5 D1, absolute t-score at least 2, direction agreement at least two thirds, fresh 20-bar break.", "أزواج العملات المعلنة فقط؛ ثلاث عينات شهرية سابقة مكتملة على الأقل من يوميات المنصة، ودرجة إحصائية مطلقة لا تقل عن اثنتين واتفاق ثلثي العينات مع كسر جديد لنطاق عشرين شمعة."),
}
SCOPE_EN = "Bounded local model; not the complete original school. Data availability and entry conditions are checked separately."
SCOPE_AR = "نموذج محلي محدد القواعد؛ لا يمثل المدرسة الأصلية بكاملها. يجري فحص توفر البيانات وشروط الدخول بشكل منفصل."


def install():
    for id,(fn,ar,en,needs,family) in MODELS.items():
        meta=st.REGISTRY[id]
        version = "3.0.1" if id in ("interasset_confirmation", "smt_proxy") else "3.0.0"
        meta.update(analyzer=fn,school=ar,version=version,coverage="IMPLEMENTED",min_bars=65,
                    data_requirements=needs,evidence_group=family)
        meta["contract"].update(rule_version=version,coverage="IMPLEMENTED",minimum_bars=65,
                               data_requirements=needs,evidence_group=family,school_complete=False,
                               definition={"name_en":en,"implementation":"nexus.local_models."+fn.__name__,
                                           "scope":SCOPE_EN,"scope_ar":SCOPE_AR,
                                           "rules":[RULES[id][0]],"rules_ar":[RULES[id][1]],
                                           "rules_source":"local_models.py"})
        meta["contract"]["executable_specialists"]=[]
    translations={
        "local model conditions incomplete":"لم تكتمل شروط النموذج المحلي",
        "local model evidence":"أدلة النموذج المحلي",
        "aligned declared MT5 partner required":"يلزم أصل مقابل محدد وبيانات منصة متزامنة",
        "prior sweep required for local liquidity model":"يلزم سحب مستوى سابق قبل نموذج السيولة المحلي",
        "local monthly model supports declared currency pairs only":"النموذج الشهري المحلي مخصص لأزواج العملات المعلنة فقط",
        "completed multi-year MT5 daily history required":"يلزم تاريخ يومي مكتمل متعدد السنوات من المنصة",
        "historical discontinuity in local monthly sample":"انقطاع سعري كبير في العينة الشهرية المحلية",
        "three complete earlier same-month samples required":"يلزم ثلاث عينات مكتملة سابقة للشهر نفسه",
        "Local wave 1-2 hypothesis; nested Elliott counts and future wave completion are not asserted":"فرضية موجتين محلية؛ لا تؤكد ترقيم إليوت المتداخل أو اكتمال موجة مستقبلية",
        "Range spring/test with tick-count proxy; no full Wyckoff phase or institutional intent inference":"كسر نطاق واختباره مع مؤشر تكات تقريبي؛ لا يثبت مراحل وايكوف الكاملة أو نية المؤسسات",
        "Local sweep plus gap return; no institutional orders or full ICT interpretation":"سحب مستوى وعودة فجوة محليان؛ لا يمثلان أوامر مؤسسات أو تفسيرًا كاملًا للمدرسة",
        "First-return OHLC zone with prior EMA filter; not observed supply or demand orders":"عودة أولى لمنطقة شموع مع فلتر متوسط سابق؛ ليست أوامر عرض وطلب مرصودة",
        "Volatility-normalized square-root grid is a house model; not complete Gann theory or a natural time cycle":"شبكة جذر السعر المعيارية نموذج خاص؛ ليست نظرية جان الكاملة أو دورة زمنية طبيعية",
        "Raw broker FX monthly sample; no adjusted futures history, stationarity or seasonal profitability claim":"عينة شهرية خام للعملات من الوسيط؛ لا تفترض تاريخ عقود معدلًا أو ثباتًا أو ربحية موسمية",
    }
    st.AR.update(translations)


install()

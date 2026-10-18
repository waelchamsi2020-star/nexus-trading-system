"""Additional versioned chart hypotheses, registered with complete local contracts.

Each model is a specific executable hypothesis, not an entire analytical school.
All inputs pass strategies.validate_bars; all plans, risk and sends remain shared.
"""
import copy
import math
import statistics
from . import strategies as st
from . import indicators as ind
from .specialists import signal, SPECS

MODEL_IDS = []
MT5_OSC = 'https://www.metatrader5.com/en/terminal/help/indicators/oscillators'
HOUSE_SCOPE_AR = 'قاعدة تنفيذ محلية موثقة؛ لا تمثل جميع تفسيرات المدرسة ولا تثبت ربحيتها.'


def model(id, ar, en, family, rules_ar, rules_en, parameters, minimum=65,
          needs=None, source=None, regimes=('TREND', 'RANGE', 'MIXED')):
    def decorate(fn):
        st._register(id, ar, list(parameters.get('indicators', [])), family, minimum)(fn)
        meta = st.REGISTRY[id]
        meta['data_requirements'] = needs or ['completed_ohlc']
        definition = dict(name_en=en, rules=rules_en, rules_en=rules_en, rules_ar=rules_ar,
                          parameters=parameters, allowed_regimes=list(regimes),
                          timeframe_scope='all_completed_ohlc', implementation='nexus.extended_models.'+fn.__name__,
                          rules_source='extended_models.py', scope_ar=HOUSE_SCOPE_AR,
                          scope='Explicit house interpretation; not complete school coverage or profitability evidence')
        if source:
            definition['source'] = source
        SPECS[id] = definition
        contract = copy.deepcopy(st.REGISTRY['ema_cross']['contract'])
        contract.update(rule_id=id, rule_version=meta['version'], minimum_bars=minimum,
                        coverage='IMPLEMENTED', data_requirements=meta['data_requirements'],
                        evidence_group=family, definition=definition, executable_specialists=[])
        meta['contract'] = contract
        MODEL_IDS.append(id)
        return fn
    return decorate


def _stops(b, n=5):
    return min(x['low'] for x in b[-n:]), max(x['high'] for x in b[-n:])


def _rebound(b, values, lower, upper, details=None):
    previous, current = values[-2:]
    if previous is None or current is None:
        return st._result(status='DATA_MISSING', missing=['indicator warm-up incomplete'])
    lo, hi = _stops(b)
    return signal(b, previous <= lower < current and b[-1]['close'] > b[-2]['close'],
                  previous >= upper > current and b[-1]['close'] < b[-2]['close'], lo, hi,
                  dict(previous=previous, current=current, lower=lower, upper=upper, **(details or {})))


@model('stochastic_rebound', 'الاستوكاستيك: عودة زخم مؤكدة', 'Stochastic SMA rebound', 'momentum',
       ['خام أربعة عشر شمعة؛ خط رئيسي بمتوسط ثلاث قيم وخط إشارة بمتوسط ثلاث قيم أخرى.',
        'عبور الخط الرئيسي صعوداً فوق عشرين وهو أعلى من الإشارة مع إغلاق صاعد؛ عكسه عند ثمانين للبيع.',
        'مرجع الوقف أدنى أو أعلى خمس شموع؛ لا يكفي وجود المؤشر في منطقة تشبع.'],
       ['Raw K(14), slow K=SMA(raw,3), D=SMA(K,3); flat raw=50.',
        'K crosses above 20 with K>D and rising close; inverse below 80 with K<D.',
        'Five-bar structural stop reference; no entry on an overbought/oversold label alone.'],
       {'indicators': ['stochastic_sma'], 'period': 14, 'slowing': 3, 'signal': 3, 'levels': [20, 80]}, source=MT5_OSC)
def stochastic_rebound(b, c):
    values = ind.stochastic(b); k = values['k']; d = values['d']; lo, hi = _stops(b)
    return signal(b, k[-2] <= 20 < k[-1] and k[-1] > d[-1] and b[-1]['close'] > b[-2]['close'],
                  k[-2] >= 80 > k[-1] and k[-1] < d[-1] and b[-1]['close'] < b[-2]['close'], lo, hi,
                  dict(k_previous=k[-2], k=k[-1], d=d[-1], variant='SMA_of_raw_ratios'))


@model('rsi_wilder_rebound', 'القوة النسبية: عودة بتنعيم وايلدر', 'Wilder RSI rebound', 'momentum',
       ['متوسط وايلدر لأرباح وخسائر أربع عشرة حركة مع بذرة حسابية أولية؛ التعادل المحايد خمسون.',
        'عبور صاعد جديد لثلاثين مع ارتفاع الإغلاق، أو عبور هابط لسبعين مع انخفاضه؛ وقف بنيوي من خمس شموع.'],
       ['Wilder means of 14 gains/losses, arithmetic seeds; flat RSI=50.',
        'Fresh cross above 30 with rising close or below 70 with falling close; five-bar structural stop.'],
       {'indicators': ['rsi_wilder'], 'period': 14, 'levels': [30, 70]}, source=MT5_OSC+'/rsi')
def rsi_wilder_rebound(b, c):
    return _rebound(b, ind.rsi_wilder([x['close'] for x in b]), 30, 70)


@model('macd_signal_cross', 'تقاطع الماكد: تأكيد اتجاه', 'MACD EMA-signal cross', 'momentum',
       ['فرق متوسطين أسيين اثنتي عشرة وست وعشرين شمعة؛ إشارة أسية لتسع قيم وبذور حسابية.',
        'تقاطع صاعد جديد للماكد مع الإشارة فوق الصفر وفي اتجاه متوسط عشرين السابق؛ العكس للبيع.'],
       ['MACD=EMA12-EMA26; signal=EMA9(MACD), arithmetic seeds; explicit EMA-signal variant.',
        'Fresh upward signal cross with MACD>0 and close above prior EMA20; inverse for sell.'],
       {'indicators': ['macd_ema_signal', 'ema_sma_seed'], 'fast': 12, 'slow': 26, 'signal': 9},
       source=MT5_OSC+'/macd', regimes=('TREND', 'MIXED'))
def macd_signal_cross(b, c):
    closes = [x['close'] for x in b]; values = ind.macd(closes); a = values['line']; s = values['signal']
    mean = ind.ema(closes[:-1], 20)[-1]; lo, hi = _stops(b)
    return signal(b, a[-2] <= s[-2] and a[-1] > s[-1] and a[-1] > 0 and closes[-1] > mean,
                  a[-2] >= s[-2] and a[-1] < s[-1] and a[-1] < 0 and closes[-1] < mean, lo, hi,
                  dict(macd=a[-1], signal=s[-1], previous_macd=a[-2], previous_signal=s[-2], prior_ema=mean))


@model('adx_di_cross', 'الحركة الاتجاهية: تقاطع مؤكد', 'Wilder ADX directional cross', 'trend',
       ['حركة موجبة وسالبة متنافيتان؛ التعادل صفر، وتنعيم وايلدر لأربع عشرة قيمة.',
        'تقاطع اتجاهي جديد مع مؤشر قوة لا يقل عن خمس وعشرين ولا ينخفض، وإغلاق في اتجاه متوسط عشرين السابق.'],
       ['Exclusive directional movement, ties zero; Wilder(14) smoothing with arithmetic seeds.',
        'Fresh DI cross; ADX>=25 and nondecreasing; close on the corresponding side of prior EMA20.'],
       {'indicators': ['adx_wilder', 'ema_sma_seed'], 'period': 14, 'strength_floor': 25},
       source='https://www.metatrader5.com/en/terminal/help/indicators/trend_indicators/admiw', regimes=('TREND', 'MIXED'))
def adx_di_cross(b, c):
    values = ind.adx_wilder(b); p = values['plus_di']; m = values['minus_di']; a = values['adx']
    mean = ind.ema([x['close'] for x in b[:-1]], 20)[-1]; lo, hi = _stops(b)
    strong = a[-1] >= 25 and a[-1] >= a[-2]
    return signal(b, strong and p[-2] <= m[-2] and p[-1] > m[-1] and b[-1]['close'] > mean,
                  strong and p[-2] >= m[-2] and p[-1] < m[-1] and b[-1]['close'] < mean, lo, hi,
                  dict(plus_di=p[-1], minus_di=m[-1], adx=a[-1], previous_adx=a[-2], prior_ema=mean))


@model('cci_reentry', 'مؤشر قناة السلع: عودة من التطرف', 'CCI reentry', 'momentum',
       ['سعر نموذجي ومتوسط وانحراف مطلق لعشرين شمعة، ومعامل مقياس قدره 0.015.',
        'عودة جديدة فوق سالب مئة مع إغلاق صاعد أو تحت موجب مئة مع إغلاق هابط؛ وقف من خمس شموع.'],
       ['CCI20 of typical price using mean absolute deviation and scale .015; flat=0.',
        'Fresh reentry above -100 with rising close or below +100 with falling close; five-bar stop.'],
       {'indicators': ['cci'], 'period': 20, 'scale': .015, 'levels': [-100, 100]}, source=MT5_OSC+'/cci')
def cci_reentry(b, c):
    return _rebound(b, ind.cci(b), -100, 100)


@model('williams_reentry', 'ويليامز: استعادة نطاق الزخم', 'Williams percent-range reentry', 'momentum',
       ['موقع الإغلاق ضمن أعلى وأدنى أربع عشرة شمعة على مقياس سالب مئة إلى صفر.',
        'عودة فوق سالب ثمانين مع ارتفاع الإغلاق أو تحت سالب عشرين مع انخفاضه؛ وقف من خمس شموع.'],
       ['Williams R14=-100*(HH-C)/(HH-LL); flat=-50.',
        'Fresh reentry above -80 with rising close or below -20 with falling close; five-bar stop.'],
       {'indicators': ['williams_r'], 'period': 14, 'levels': [-80, -20]}, source=MT5_OSC+'/wpr')
def williams_reentry(b, c):
    return _rebound(b, ind.williams_r(b), -80, -20)


@model('mfi_tick_rebound', 'تدفق سعري مرجح بالتكات: عودة زخم', 'Tick-weighted MFI proxy rebound', 'volume',
       ['السعر النموذجي مضروب بعدد التكات الموجب؛ التصنيف حسب تغير السعر النموذجي، والتعادل مستبعد.',
        'أربع عشرة حركة؛ عودة فوق عشرين أو تحت ثمانين مع إغلاق موافق؛ ليس حجم صفقات أو تدفق أموال فعلياً.'],
       ['Typical price times positive bar tick count; direction by typical-price change, ties excluded.',
        '14 changes; fresh cross above 20 or below 80 with confirming close; not actual traded money flow.'],
       {'indicators': ['mfi_tick'], 'period': 14, 'levels': [20, 80], 'volume_source': 'tick_volume'},
       needs=['completed_ohlc', 'positive_tick_volume'])
def mfi_tick_rebound(b, c):
    try:
        values = ind.mfi_tick(b[-31:])
    except (TypeError, ValueError, OverflowError):
        return st._result(status='DATA_MISSING', missing=['positive finite tick counts required for tick MFI'],
                          assumptions=['tick MFI is a price-activity proxy, not traded money flow'])
    result = _rebound(b, values, 20, 80, {'volume_source': 'tick_count'})
    result['assumptions'].append('tick MFI is a price-activity proxy, not traded money flow')
    return result


@model('three_bar_reversal', 'الشموع: انعكاس ثلاثي مؤكد', 'Three-bar reversal without gap assumption', 'candle',
       ['اتجاه سابق من متوسط عشرين وميله؛ جسم أول لا يقل عن 0.8 من التقلب السابق، وجسم وسط لا يتجاوز ثلثه.',
        'جسم ثالث معاكس لا يقل عن نصف التقلب وإغلاق يتجاوز منتصف الجسم الأول؛ لا يشترط فجوات لأسواق التداول المتصل.'],
       ['Prior EMA20 slope/context; first body >=.8 prior ATR, middle body <=one third of first.',
        'Opposite third body >=.5 prior ATR and closes beyond first body midpoint; no gap assumption.'],
       {'indicators': ['prior_ema20', 'prior_atr_simple'], 'first_body_atr': .8, 'middle_fraction': 1/3, 'third_body_atr': .5})
def three_bar_reversal(b, c):
    first, middle, last = b[-3:]; prior = b[:-3]; a = st.atr(prior)
    means = st.ema([x['close'] for x in prior], 20); midpoint = (first['open']+first['close'])/2
    body = abs(first['close']-first['open']); small = abs(middle['close']-middle['open']) <= body/3
    valid = a > 0 and body >= .8*a and small and abs(last['close']-last['open']) >= .5*a
    bull = valid and means[-1] < means[-2] and first['close'] < first['open'] and first['open'] < means[-1] and last['close'] > last['open'] and last['close'] > midpoint
    bear = valid and means[-1] > means[-2] and first['close'] > first['open'] and first['open'] > means[-1] and last['close'] < last['open'] and last['close'] < midpoint
    lo, hi = _stops(b, 3)
    return signal(b, bull, bear, lo, hi, dict(first_body=body, middle_small=small, midpoint=midpoint, prior_atr=a))


@model('rectangle_breakout', 'الكلاسيكي: اختراق مستطيل سعري', 'Confirmed rectangle breakout', 'structure',
       ['عشرون شمعة سابقة، ونطاق بين ضعفي وثمانية أضعاف تقلب سابق مستقل.',
        'اختباران لكل حد يفصل بينهما ثلاث شموع على الأقل ضمن سماح 0.15 من التقلب؛ إغلاق جديد خارج الحد مع سلامة المقابل.'],
       ['20 prior bars; width 2..8 times ATR calculated before the range.',
        'Two touches per edge separated by >=3 bars within .15 ATR; fresh close outside with opposite edge intact.'],
       {'indicators': ['prior_20_bar_range', 'prior_atr_simple'], 'window': 20, 'touch_tolerance_atr': .15, 'min_touch_separation': 3})
def rectangle_breakout(b, c):
    window = b[-21:-1]; a = st.atr(b[:-21]); lo = min(x['low'] for x in window); hi = max(x['high'] for x in window)
    def touches(key, level):
        selected = [i for i, x in enumerate(window) if abs(x[key]-level) <= .15*a]
        return len(selected) >= 2 and selected[-1]-selected[0] >= 3
    shape = a > 0 and 2*a <= hi-lo <= 8*a and touches('high', hi) and touches('low', lo)
    bull = shape and b[-2]['close'] <= hi < b[-1]['close'] and b[-1]['low'] > lo
    bear = shape and b[-2]['close'] >= lo > b[-1]['close'] and b[-1]['high'] < hi
    return signal(b, bull, bear, lo, hi, dict(low=lo, high=hi, valid_rectangle=shape, reference_atr=a))


@model('flag_breakout', 'الكلاسيكي: استمرار راية محددة', 'Bounded flag continuation', 'structure',
       ['اندفاع خمس شموع لا يقل عن ثلاثة أضعاف التقلب السابق، يليه تصحيح من ثماني شموع.',
        'تصحيح بين خمس وعشرين وخمسين بالمئة، وعرض لا يتجاوز ثلاثة أضعاف التقلب؛ اختراق جديد في اتجاه السارية.'],
       ['Five-bar pole >=3 pre-pole ATR followed by eight-bar consolidation.',
        'Retracement .25..50, flag width <=3 ATR; fresh directional break of flag with opposite edge intact.'],
       {'indicators': ['prior_atr_simple', 'pole_and_flag_ohlc'], 'pole_bars': 5, 'flag_bars': 8, 'retracement': [.25, .5]})
def flag_breakout(b, c):
    pole = b[-14:-9]; flag = b[-9:-1]; a = st.atr(b[:-14]); move = pole[-1]['close']-pole[0]['open']
    lo = min(x['low'] for x in flag); hi = max(x['high'] for x in flag); distance = abs(move)
    retrace = (pole[-1]['close']-lo if move > 0 else hi-pole[-1]['close'])/distance if distance else 0
    valid = a > 0 and distance >= 3*a and .25 <= retrace <= .5 and hi-lo <= 3*a
    bull = valid and move > 0 and hi <= max(x['high'] for x in pole) and b[-2]['close'] <= hi < b[-1]['close'] and b[-1]['low'] > lo
    bear = valid and move < 0 and lo >= min(x['low'] for x in pole) and b[-2]['close'] >= lo > b[-1]['close'] and b[-1]['high'] < hi
    return signal(b, bull, bear, lo, hi, dict(pole_move=move, retracement=retrace, flag_low=lo, flag_high=hi, reference_atr=a))


HARMONIC_RATIOS = {
    'gartley': {'ab_xa': [.588, .648], 'bc_ab': [.382, .886], 'ad_xa': [.756, .816], 'cd_bc': [1.27, 1.618], 'cd_ab': [.95, 1.05]},
    'bat': {'ab_xa': [.382, .5], 'bc_ab': [.382, .886], 'ad_xa': [.856, .916], 'cd_bc': [1.618, 2.618], 'cd_ab': [1., 1.618]},
    'butterfly': {'ab_xa': [.756, .816], 'bc_ab': [.382, .886], 'ad_xa': [1.24, 1.30], 'cd_bc': [1.618, 2.618], 'cd_ab': [1.27, 1.618]},
}


def harmonic_geometry(pivots, kind):
    """Five alternating XABCD pivots; declared ratio intervals are house choices."""
    if len(pivots) != 5 or kind not in HARMONIC_RATIOS:
        return None
    if any(p['kind'] == q['kind'] or p['index'] >= q['index'] for p, q in zip(pivots, pivots[1:])):
        return None
    sign = 1 if pivots[0]['kind'] == 'LOW' else -1
    x, a, b, c, d = [sign*p['price'] for p in pivots]
    xa = a-x; ab = a-b; bc = c-b; cd = c-d; ad = a-d
    if min(xa, ab, bc, cd, ad) <= 0 or not x < b < c < a:
        return None
    if (kind != 'butterfly' and not x < d < b) or (kind == 'butterfly' and not d < x):
        return None
    ratios = dict(ab_xa=ab/xa, bc_ab=bc/ab, ad_xa=ad/xa, cd_bc=cd/bc, cd_ab=cd/ab)
    if not all(lo <= ratios[name] <= hi for name, (lo, hi) in HARMONIC_RATIOS[kind].items()):
        return None
    return dict(direction='BUY' if sign > 0 else 'SELL', ratios=ratios, pivots=copy.deepcopy(pivots))


def _harmonic(b, c, kind):
    pivots = st._alternating_pivots(c['pivots']); geometry = None
    # A minor post-D confirmation pivot is not an invalidation of XABCD.
    # Keep the newest matching five-pivot window within its declared lifetime;
    # never search outside that lifetime or cherry-pick by eventual outcome.
    for end in range(len(pivots),4,-1):
        p = pivots[end-5:end]
        if len(b)-1-(p[-1]['index']+2)>8:
            break
        geometry = harmonic_geometry(p,kind)
        if geometry is not None:
            break
    if geometry is None:
        return st._result(missing=['five-pivot harmonic geometry incomplete'])
    d = p[-1]; bull = geometry['direction'] == 'BUY'; confirmation = b[d['index']+1:d['index']+3]
    age = len(b)-1-(d['index']+2)
    if len(confirmation) != 2:
        return st._result(missing=['harmonic confirmation incomplete'])
    level = max(x['high'] for x in confirmation) if bull else min(x['low'] for x in confirmation)
    intact = all(x['low'] >= d['price'] if bull else x['high'] <= d['price'] for x in b[d['index']+1:])
    cross = b[-2]['close'] <= level < b[-1]['close'] if bull else b[-2]['close'] >= level > b[-1]['close']
    target = p[-2]['price']; ahead = b[-1]['close'] < target if bull else b[-1]['close'] > target
    active = 1 <= age <= 8 and intact and cross and ahead
    result = signal(b, active and bull, active and not bull, d['price'], d['price'],
                    dict(**geometry, pattern=kind, confirmation_level=level, confirmation_age=age, d_intact=intact), target)
    result['assumptions'].append('harmonic ratio tolerances and execution confirmation are declared house rules')
    return result


def _harmonic_decorator(kind, ar, en):
    return model('harmonic_'+kind, ar, en, 'structure',
                 ['خمسة محاور متناوبة مؤكدة؛ النسب والسماحات العددية محفوظة كاملة في معاملات النموذج.',
                  'عبور جديد لمستوى الشمعتين المؤكدتين للنقطة الأخيرة بعد تأكيدها بواحدة إلى ثماني شموع؛ بقاء النقطة سليمة والهدف عند النقطة السابقة.',
                  'يبقى أحدث تسلسل مطابق ضمن عمره صالحاً رغم محور تأكيد صغير لاحق؛ لا يُبحث عن تسلسل انتهى عمره.'],
                 ['Five confirmed alternating XABCD pivots; every ratio interval is explicit in parameters.',
                  'Fresh break of two D-confirmation bars 1..8 bars after confirmation; D intact and target C ahead.',
                  'Retain the newest matching XABCD window within its lifetime despite minor later confirmation pivots; never reuse expired windows.'],
                 {'indicators': ['causal_five_bar_pivots', 'fibonacci_ratios'], 'ratios': HARMONIC_RATIOS[kind],
                  'ratio_policy': 'house_intervals_not_universal_tolerances', 'max_confirmation_age': 8},
                 source='https://harmonictrader.com/harmonic-patterns/'+kind+'-pattern/')


@_harmonic_decorator('gartley', 'الهارمونيك: غارتلي مؤكد', 'Confirmed Gartley house model')
def harmonic_gartley(b, c):
    return _harmonic(b, c, 'gartley')


@_harmonic_decorator('bat', 'الهارمونيك: بات مؤكد', 'Confirmed Bat house model')
def harmonic_bat(b, c):
    return _harmonic(b, c, 'bat')


@_harmonic_decorator('butterfly', 'الهارمونيك: باترفلاي مؤكد', 'Confirmed Butterfly house model')
def harmonic_butterfly(b, c):
    return _harmonic(b, c, 'butterfly')


@model('wyckoff_range_expansion', 'وايكوف: توسع نطاق مع نشاط تكات', 'Wyckoff-inspired range expansion', 'structure',
       ['نطاق سابق من أربعين شمعة بعرض لا يقل عن ثلاثة أضعاف التقلب وكفاءة اتجاه لا تزيد عن الربع.',
        'إغلاق جديد خارج النطاق بجسم لا يقل عن التقلب، وفي طرف عشرين بالمئة من الشمعة، ونشاط تكات لا يقل عن مرة ونصف الوسيط السابق.',
        'هذا حدث سعري مستوحى من القوة والضعف؛ لا يقرر مرحلة التجميع أو نية المؤسسات.'],
       ['Prior 40-bar range width >=3 prior ATR with close efficiency <=.25.',
        'Fresh boundary break, body>=prior ATR, close in outer 20%, ticks>=1.5 prior median.',
        'Price/activity event only; no complete Wyckoff phase or institutional intent inference.'],
       {'indicators': ['range40', 'efficiency40', 'tick_activity'], 'activity_multiple': 1.5},
       needs=['completed_ohlc', 'positive_tick_volume'], source='https://www.wyckoffanalytics.com/wyckoff-method/')
def wyckoff_range_expansion(b, c):
    prior = b[-41:-1]; x = b[-1]; volumes = [z.get('tick_volume') for z in b[-21:]]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in volumes):
        return st._result(status='DATA_MISSING', missing=['positive finite tick counts required for range expansion'])
    a = st.atr(prior); hi = max(z['high'] for z in prior); lo = min(z['low'] for z in prior)
    travel = sum(abs(q['close']-p['close']) for p, q in zip(prior, prior[1:]))
    efficiency = abs(prior[-1]['close']-prior[0]['close'])/travel if travel else 0
    span = x['high']-x['low']; location = (x['close']-x['low'])/span if span else .5
    active = a > 0 and hi-lo >= 3*a and efficiency <= .25 and abs(x['close']-x['open']) >= a and volumes[-1] >= 1.5*statistics.median(volumes[:-1])
    bull = active and b[-2]['close'] <= hi < x['close'] and x['close'] > x['open'] and location >= .8
    bear = active and b[-2]['close'] >= lo > x['close'] and x['close'] < x['open'] and location <= .2
    result = signal(b, bull, bear, min(z['low'] for z in b[-6:]), max(z['high'] for z in b[-6:]),
                    dict(range_low=lo, range_high=hi, efficiency=efficiency, location=location, activity_ratio=volumes[-1]/statistics.median(volumes[:-1])))
    result['assumptions'].append('range expansion uses tick activity, not actual institutional volume')
    return result


@model('liquidity_bos_retest', 'السيولة: سحب ثم كسر وإعادة اختبار', 'Liquidity sweep BOS first retest', 'structure',
       ['سحب أحد حدي عشر شموع وإغلاق داخله، ثم إغلاق لاحق خارج الحد المقابل بجسم لا يقل عن التقلب السابق.',
        'أول إعادة اختبار للحد المكسور خلال ثماني شموع من السحب بسماح 0.15 من التقلب وإغلاق موافق؛ يبقى حد السحب سليماً.'],
       ['Sweep/reclaim of a prior 10-bar boundary, then later close beyond opposite boundary with body>=pre-sweep ATR.',
        'First retest within eight bars of sweep, tolerance .15 ATR, directional rejection, sweep extreme unbroken.'],
       {'indicators': ['prior_10_bar_range', 'prior_atr_simple'], 'max_sweep_age': 8, 'retest_tolerance_atr': .15})
def liquidity_bos_retest(b, c):
    x = b[-1]
    for i in range(len(b)-4, len(b)-10, -1):
        sweep = b[i]; prior = b[i-10:i]; a = st.atr(b[:i]); lo = min(z['low'] for z in prior); hi = max(z['high'] for z in prior)
        if a <= 0:
            continue
        for bull in (True, False):
            valid = sweep['low'] < lo < sweep['close'] <= hi if bull else sweep['high'] > hi > sweep['close'] >= lo
            if not valid:
                continue
            level = hi if bull else lo
            breaks = [j for j in range(i+1, len(b)-1) if (b[j-1]['close'] <= level < b[j]['close'] and b[j]['close']-b[j]['open'] >= a if bull else
                      b[j-1]['close'] >= level > b[j]['close'] and b[j]['open']-b[j]['close'] >= a)]
            if not breaks:
                continue
            j = breaks[0]; between = b[j+1:-1]
            consumed = any(z['low'] <= level+.15*a if bull else z['high'] >= level-.15*a for z in between)
            intact = all(z['low'] > sweep['low'] if bull else z['high'] < sweep['high'] for z in b[i+1:])
            rejected = (level-.15*a <= x['low'] <= level+.15*a and x['close'] > level and x['close'] > x['open'] if bull else
                        level-.15*a <= x['high'] <= level+.15*a and x['close'] < level and x['close'] < x['open'])
            if not consumed and intact and rejected:
                return signal(b, bull, not bull, sweep['low'], sweep['high'],
                              dict(sweep_time=sweep['time'], bos_time=b[j]['time'], level=level, first_touch=True, reference_atr=a))
    return signal(b, False, False, None, None, {'first_touch': False})


@model('darvas_rising_boxes', 'دارفاس: تتابع صندوقين مؤكدين', 'Darvas two-box continuation', 'structure',
       ['صندوقان متتابعان من عشرين شمعة لكل منهما؛ سقف كل صندوق يسبق ثلاث قمم أدنى بصورة صارمة.',
        'ارتفاع السقف والقاع معاً ثم اختراق جديد للسقف للشراء، أو انخفاضهما واختراق القاع للبيع؛ الوقف عند الحد المقابل.'],
       ['Two consecutive 20-bar boxes; each top precedes at least three strictly lower highs.',
        'Both boundaries rise then fresh upper break for buy, or both fall then lower break for sell; opposite edge stop.'],
       {'indicators': ['two_confirmed_20_bar_boxes'], 'box_bars': 20, 'top_confirmation_bars': 3})
def darvas_rising_boxes(b, c):
    boxes = []
    for window in (b[-41:-21], b[-21:-1]):
        hi = max(z['high'] for z in window); lo = min(z['low'] for z in window)
        index = next(i for i, z in enumerate(window) if z['high'] == hi)
        valid = hi > lo and index <= 16 and all(z['high'] < hi for z in window[index+1:])
        boxes.append(dict(high=hi, low=lo, confirmed=valid))
    old, new = boxes; valid = old['confirmed'] and new['confirmed']
    bull = valid and new['high'] > old['high'] and new['low'] > old['low'] and b[-2]['close'] <= new['high'] < b[-1]['close'] and b[-1]['low'] > new['low']
    bear = valid and new['high'] < old['high'] and new['low'] < old['low'] and b[-2]['close'] >= new['low'] > b[-1]['close'] and b[-1]['high'] < new['high']
    return signal(b, bull, bear, new['low'], new['high'], dict(boxes=boxes))


st.AR.update({
    'indicator warm-up incomplete': 'لم يكتمل تاريخ تهيئة المؤشر',
    'positive finite tick counts required for tick MFI': 'يلزم عدد تكات موجب ومحدود لحاسبة التدفق التقريبي',
    'tick MFI is a price-activity proxy, not traded money flow': 'التدفق المرجح بالتكات تقريب نشاط سعري وليس تدفق أموال فعلياً',
    'five-pivot harmonic geometry incomplete': 'لم تكتمل هندسة الهارمونيك ذات المحاور الخمسة',
    'harmonic confirmation incomplete': 'لم يكتمل تأكيد نقطة الهارمونيك الأخيرة',
    'harmonic ratio tolerances and execution confirmation are declared house rules': 'سماحات نسب الهارمونيك وشروط تأكيد التنفيذ قواعد محلية معلنة',
    'positive finite tick counts required for range expansion': 'يلزم عدد تكات موجب ومحدود لنموذج توسع النطاق',
    'range expansion uses tick activity, not actual institutional volume': 'توسع النطاق يستخدم نشاط التكات ولا يقيس حجم تداول مؤسسي فعلي',
})

# Numerical correction only: bounded percentage ratios divide before scaling.
# Keep old observations separate by rule version and archived source revision.
for _model_id in ('stochastic_rebound','rsi_wilder_rebound','adx_di_cross','williams_reentry','mfi_tick_rebound'):
    st.REGISTRY[_model_id]['version']='1.0.1'
    st.REGISTRY[_model_id]['contract']['rule_version']='1.0.1'

for _model_id in ('harmonic_gartley','harmonic_bat','harmonic_butterfly'):
    st.REGISTRY[_model_id]['version']='1.1.0'
    st.REGISTRY[_model_id]['contract']['rule_version']='1.1.0'

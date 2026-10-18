"""Causal local indicator library, v1.0.0; no market or broker authority.

Outputs align one-to-one with inputs. None denotes unavailable warm-up, never
zero-filled evidence. Formulas and initial seeds are explicit: this library does
not claim bitwise parity with a terminal using a different history/seed/method.
"""
import math
import statistics


def _period(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError('period must be a positive integer')
    return value


def _values(values):
    out = list(values)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in out):
        raise ValueError('indicator inputs must be finite numbers')
    return out


def sma(values, period):
    values = _values(values); n = _period(period)
    return [statistics.fmean(values[i-n+1:i+1]) if i >= n-1 else None for i in range(len(values))]


def rma(values, period):
    """Wilder mean: first n values arithmetic seed, then (prev*(n-1)+x)/n."""
    values = _values(values); n = _period(period); out = [None]*len(values)
    if len(values) < n:
        return out
    out[n-1] = statistics.fmean(values[:n])
    for i in range(n, len(values)):
        out[i] = (out[i-1]*(n-1)+values[i])/n
    return out


def ema(values, period):
    """SMA seed after n observations, alpha=2/(n+1), no pre-seed values."""
    values = _values(values); n = _period(period); out = [None]*len(values)
    if len(values) < n:
        return out
    out[n-1] = statistics.fmean(values[:n]); alpha = 2/(n+1)
    for i in range(n, len(values)):
        out[i] = alpha*values[i]+(1-alpha)*out[i-1]
    return out


def _smooth_valid(values, period, method=sma):
    start = next((i for i, value in enumerate(values) if value is not None), len(values))
    return [None]*start + method(values[start:], period)


def true_range(bars):
    if not bars:
        return []
    # First bar lacks previous close; excluded, not replaced with its range.
    return [None]+[max(x['high']-x['low'], abs(x['high']-p['close']), abs(x['low']-p['close']))
                   for p, x in zip(bars, bars[1:])]


def atr_wilder(bars, period=14):
    return _smooth_valid(true_range(bars), period, rma)


def rsi_wilder(closes, period=14):
    closes = _values(closes); n = _period(period)
    changes = [b-a for a, b in zip(closes, closes[1:])]
    gains = rma([max(x, 0) for x in changes], n)
    losses = rma([max(-x, 0) for x in changes], n)
    out = [None] if closes else []
    for gain, loss in zip(gains, losses):
        out.append(None if gain is None else 50.0 if gain+loss == 0 else 100*gain/(gain+loss))
    return out


def stochastic(bars, period=14, slowing=3, signal=3):
    """Raw 100*(C-LL)/(HH-LL); slow K=SMA(raw,slowing); D=SMA(K,signal).

    This explicitly defined SMA-of-ratios variant does not claim equality to
    terminal variants using a ratio of smoothed numerators/denominators.
    """
    n = _period(period); _period(slowing); _period(signal); raw = []
    for i, x in enumerate(bars):
        if i < n-1:
            raw.append(None); continue
        window = bars[i-n+1:i+1]; hi = max(z['high'] for z in window); lo = min(z['low'] for z in window)
        raw.append(50.0 if hi == lo else 100*(x['close']-lo)/(hi-lo))
    k = _smooth_valid(raw, slowing)
    return {'raw_k': raw, 'k': k, 'd': _smooth_valid(k, signal)}


def macd(closes, fast=12, slow=26, signal=9):
    if _period(fast) >= _period(slow):
        raise ValueError('MACD fast period must be below slow period')
    closes = _values(closes); a = ema(closes, fast); b = ema(closes, slow)
    line = [x-y if x is not None and y is not None else None for x, y in zip(a, b)]
    sig = _smooth_valid(line, signal, ema)
    return {'line': line, 'signal': sig,
            'histogram': [x-y if y is not None else None for x, y in zip(line, sig)]}


def adx_wilder(bars, period=14):
    """Exclusive directional movement: ties -> both zero; Wilder means throughout."""
    n = _period(period); plus = []; minus = []
    for p, x in zip(bars, bars[1:]):
        up = x['high']-p['high']; down = p['low']-x['low']
        plus.append(up if up > down and up > 0 else 0.)
        minus.append(down if down > up and down > 0 else 0.)
    tr = atr_wilder(bars, n)
    psm = ([None]+rma(plus, n)) if bars else []
    msm = ([None]+rma(minus, n)) if bars else []
    pdi = []; mdi = []; dx = []
    for a, p, m in zip(tr, psm, msm):
        pos = None if a is None else 100*p/a if a > 0 else 0.
        neg = None if a is None else 100*m/a if a > 0 else 0.
        pdi.append(pos); mdi.append(neg)
        dx.append(None if pos is None else 100*abs(pos-neg)/(pos+neg) if pos+neg > 0 else 0.)
    return {'plus_di': pdi, 'minus_di': mdi, 'dx': dx, 'adx': _smooth_valid(dx, n, rma)}


def cci(bars, period=20):
    n = _period(period); prices = [(x['high']+x['low']+x['close'])/3 for x in bars]; out = []
    for i, value in enumerate(prices):
        if i < n-1:
            out.append(None); continue
        window = prices[i-n+1:i+1]; mean = statistics.fmean(window)
        deviation = statistics.fmean(abs(x-mean) for x in window)
        out.append((value-mean)/(.015*deviation) if deviation > 0 else 0.)
    return out


def williams_r(bars, period=14):
    n = _period(period); out = []
    for i, x in enumerate(bars):
        if i < n-1:
            out.append(None); continue
        window = bars[i-n+1:i+1]; hi = max(z['high'] for z in window); lo = min(z['low'] for z in window)
        out.append(-100*(hi-x['close'])/(hi-lo) if hi > lo else -50.)
    return out


def mfi_tick(bars, period=14):
    """Typical price times tick count; a declared proxy, never traded cash flow."""
    n = _period(period); volume = _values(x.get('tick_volume') for x in bars)
    if any(x <= 0 for x in volume):
        raise ValueError('MFI tick proxy requires positive tick counts')
    prices = [(x['high']+x['low']+x['close'])/3 for x in bars]
    plus = []; minus = []; out = [None] if bars else []
    for i in range(1, len(bars)):
        value = prices[i]*volume[i]
        if not math.isfinite(value):
            raise ValueError('MFI tick proxy overflow')
        plus.append(value if prices[i] > prices[i-1] else 0.)
        minus.append(value if prices[i] < prices[i-1] else 0.)
        if i < n:
            out.append(None); continue
        p = sum(plus[-n:]); m = sum(minus[-n:])
        out.append(100*p/(p+m) if p+m > 0 else 50.)
    return out


FORMULAS = {
    'sma': {'version': '1.0.0', 'formula': 'mean(last n finite values)', 'warmup': 'n observations'},
    'ema_sma_seed': {'version': '1.0.0', 'formula': 'alpha=2/(n+1); SMA(n) seed; alpha*x+(1-alpha)*previous', 'warmup': 'n observations'},
    'rma': {'version': '1.0.0', 'formula': 'SMA(n) seed; (previous*(n-1)+x)/n', 'warmup': 'n observations'},
    'rsi_wilder': {'version': '1.0.0', 'formula': '100*RMA(gain,n)/(RMA(gain,n)+RMA(loss,n)); flat=50', 'parameters': {'period': 14}, 'warmup': 'n+1 closes'},
    'atr_wilder': {'version': '1.0.0', 'formula': 'RMA(max(H-L,abs(H-Cprev),abs(L-Cprev)),n); first TR unavailable', 'parameters': {'period': 14}},
    'stochastic_sma': {'version': '1.0.0', 'formula': 'raw=100*(C-LLn)/(HHn-LLn); K=SMA(raw,3); D=SMA(K,3); flat raw=50', 'parameters': {'period': 14, 'slowing': 3, 'signal': 3}, 'terminal_parity': False},
    'macd_ema_signal': {'version': '1.0.0', 'formula': 'EMA(C,12)-EMA(C,26); signal=EMA(line,9); histogram=line-signal; SMA seeds', 'terminal_parity': False},
    'adx_wilder': {'version': '1.0.0', 'formula': 'exclusive +DM/-DM (ties=0); DI=100*RMA(DM,14)/ATRw; DX=100*abs(+DI--DI)/(+DI+-DI); ADX=RMA(DX,14); zero denominators=0', 'parameters': {'period': 14}},
    'cci': {'version': '1.0.0', 'formula': '(TP-SMA(TP,20))/(0.015*mean(abs(TP-SMA))); TP=(H+L+C)/3; flat=0'},
    'williams_r': {'version': '1.0.0', 'formula': '-100*(HH14-C)/(HH14-LL14); flat=-50'},
    'mfi_tick': {'version': '1.0.0', 'formula': '100*sum(positive TP*ticks,14)/sum(positive and negative TP*ticks,14); ties excluded; flat=50', 'volume': 'positive_tick_count_proxy_not_real_money_flow'},
}

for _name, _function in {'sma':'sma', 'ema_sma_seed':'ema', 'rma':'rma', 'rsi_wilder':'rsi_wilder',
                          'atr_wilder':'atr_wilder', 'stochastic_sma':'stochastic', 'macd_ema_signal':'macd',
                          'adx_wilder':'adx_wilder', 'cci':'cci', 'williams_r':'williams_r', 'mfi_tick':'mfi_tick'}.items():
    FORMULAS[_name]['implementation']='nexus.indicators.'+_function

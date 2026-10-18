"""Complete UTC buckets only; aggregation creates no additional history."""
from .strategies import validate_bars
from .timeframes import PERIODS, bar_close_time


def aggregate_m1(bars, timeframe, as_of):
    if timeframe not in ('M5', 'H1'):
        raise ValueError('Only explicit M5/H1 aggregation is supported')
    rows = validate_bars(bars, 'M1', as_of)
    seconds = PERIODS[timeframe]
    expected = seconds // 60
    buckets = {}
    for row in rows:
        stamp = row['time'] // seconds * seconds
        buckets.setdefault(stamp, []).append(row)
    result = []
    for stamp, group in sorted(buckets.items()):
        if len(group) != expected or [x['time'] for x in group] != list(range(stamp, stamp + seconds, 60)):
            continue
        if bar_close_time(stamp, timeframe) > as_of:
            continue
        result.append({'time':stamp, 'open':group[0]['open'], 'high':max(x['high'] for x in group),
                       'low':min(x['low'] for x in group), 'close':group[-1]['close'],
                       'tick_volume':sum(x.get('tick_volume', 0) for x in group),
                       'real_volume':sum(x.get('real_volume', 0) for x in group),
                       # Opening quote spread is retained, not an artificially
                       # narrower average of unavailable intrabar quotes.
                       'spread':group[0].get('spread', 0)})
    return result

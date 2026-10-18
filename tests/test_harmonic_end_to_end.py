"""Independent XABCD paths through real causal pivots and shared price plans.

No injected pivots, mocked indicator, broker connection or profitability claim.
"""
import copy
import itertools
import json
import unittest

from nexus import strategies as st

PRICES={'gartley':[100.,110.,103.82,108.32,102.14],
        'bat':[100.,110.,105.,108.,101.14],
        'butterfly':[100.,110.,102.14,107.5,97.3]}


def scenario(kind,side='BUY'):
    points=[(0,105.),(50,PRICES[kind][0]+.03),(58,PRICES[kind][1]-.03),
            (66,PRICES[kind][2]+.03),(74,PRICES[kind][3]-.03),(82,PRICES[kind][4]+.03)]
    rows=[]
    for i in range(83):
        start,end=next((a,b) for a,b in itertools.pairwise(points) if a[0]<=i<=b[0])
        value=start[1]+(end[1]-start[1])*(i-start[0])/(end[0]-start[0])
        opening=value-.01 if end[1]>start[1] else value+.01
        rows.append({'time': 1700000000+i*3600,'open': opening,'close': value,
                         'high': max(opening,value)+.02,'low': min(opening,value)-.02,'tick_volume': 100})
    for index,price,field in zip((50,58,66,74,82),PRICES[kind],('low','high','low','high','low')):
        rows[index][field]=price
    d=PRICES[kind][-1]
    for i in range(83,90):
        o,c,h,l=(.2,.5,.7,.1) if i==83 else (.5,.6,.9,.3) if i==84 else (.5,.6,.8,.4)
        if i==89:o,c,h,l=.6,1.2,1.3,.5
        rows.append({'time': 1700000000+i*3600,'open': d+o,'close': d+c,'high': d+h,'low': d+l,'tick_volume': 100})
    if side=='SELL':
        rows=[dict(x,open=210-x['open'],close=210-x['close'],high=210-x['low'],low=210-x['high']) for x in rows]
    return rows


def analyze(kind,rows,as_of=None):
    return st.analyze_strategy('harmonic_'+kind,'SYNTHETIC_FIXTURE','H1',rows,
                               rows[-1]['time']+3600 if as_of is None else as_of,{'data_kind':'synthetic'})


class HarmonicPipelineTests(unittest.TestCase):
    def test_buy_sell_use_actual_confirmed_pivots_and_bracketed_price_plan(self):
        for kind in PRICES:
            for side in ('BUY','SELL'):
                with self.subTest(kind=kind,side=side):
                    rows=scenario(kind,side);before=copy.deepcopy(rows);card=analyze(kind,rows)
                    self.assertTrue(card['actionable'],card['conditions_missing'])
                    self.assertEqual(card['direction'],side)
                    entry=card['entry']['price'];stop=card['stop']['price'];target=card['targets'][0]['price']
                    self.assertTrue(stop<entry<target if side=='BUY' else target<entry<stop)
                    self.assertAlmostEqual(target,PRICES[kind][-2] if side=='BUY' else 210-PRICES[kind][-2])
                    actual=st.causal_pivots(rows,as_of=rows[-1]['time']+3600,timeframe='H1')
                    self.assertTrue(any(p['index']==84 for p in actual),'the later confirmation pivot must exist in the actual extraction')
                    self.assertEqual(card['evidence'][0]['value']['pivots'][-1]['index'],82,'the original D remains the invalidation anchor')
                    self.assertEqual(rows,before)
                    json.dumps(card,allow_nan=False)

    def test_pivot_confirmation_is_not_the_entry_and_future_bar_never_executes(self):
        for kind in PRICES:
            for side in ('BUY','SELL'):
                with self.subTest(kind=kind,side=side):
                    rows=scenario(kind,side)
                    self.assertFalse(analyze(kind,rows[:85])['actionable'])
                    card=analyze(kind,rows,rows[-1]['time'])
                    self.assertFalse(card['actionable']);self.assertEqual(card['status'],'DATA_INVALID')

    def test_breach_of_d_and_invalid_ratios_abstain(self):
        for kind in PRICES:
            for side in ('BUY','SELL'):
                with self.subTest(kind=kind,side=side):
                    rows=scenario(kind,side)
                    if side=='BUY':rows[85]['low']=PRICES[kind][-1]-.1
                    else:rows[85]['high']=210-PRICES[kind][-1]+.1
                    self.assertFalse(analyze(kind,rows)['actionable'])
                    rows=scenario(kind,side)
                    if side=='BUY':rows[66]['low']=rows[66]['open']-1.7
                    else:rows[66]['high']=rows[66]['open']+1.7
                    self.assertFalse(analyze(kind,rows)['actionable'])

    def test_expired_pattern_is_not_resurrected_by_searching_old_windows(self):
        for kind in PRICES:
            for side in ('BUY','SELL'):
                with self.subTest(kind=kind,side=side):
                    rows=scenario(kind,side)
                    expired=rows[:-1]+[dict(rows[-2]) for _ in range(10)]+rows[-1:]
                    for i,bar in enumerate(expired):bar['time']=1700000000+i*3600
                    self.assertFalse(analyze(kind,expired)['actionable'])


if __name__=='__main__':unittest.main()

import copy
import unittest

from test_strategies import bars

from nexus.quant import replay
from nexus.research_resampling import aggregate_m1
from nexus.walkforward import evaluate_history


def minute_bars(count):
    rows=bars(count,step=60)
    start=rows[0]['time']//3600*3600
    for index,row in enumerate(rows):row['time']=start+index*60
    return rows


# Vulture review: unittest/pytest discovers this TestCase class.
class ExecutionAssumptions(unittest.TestCase):
    def test_market_next_open_applies_adverse_entry_slippage_both_directions(self):
        for side in ('BUY', 'SELL'):
            with self.subTest(side=side):
                rows=bars(40)
                for row in rows:
                    row.update(open=100.,close=100.,high=100.05,low=99.95,spread=2)
                def signal(history, as_of, side=side):
                    if len(history)!=20:return {'status':'WAIT'}
                    return {'status':'READY','direction':side,'entry':{'triggered':True,'zone':[99.,101.]},
                            'stop':{'price':98. if side=='BUY' else 102.},
                            'targets':[{'price':105. if side=='BUY' else 95.}]}
                report=replay(rows,'engulfing',start_index=19,end_index=23,
                              config={'point':.01,'slippage_price':.2,'commission_per_unit':.1},signal_fn=signal)
                self.assertEqual(1,len(report['trades']))
                self.assertAlmostEqual(100.22 if side=='BUY' else 99.8,report['trades'][0]['entry'])
                self.assertIn('next-open',report['trades'][0]['fill_model'])

    def test_resampling_conserves_ohlc_volume_and_opening_spread_without_mutation(self):
        rows=minute_bars(180);original=copy.deepcopy(rows)
        for tf,n in (('M5',5),('H1',60)):
            actual=aggregate_m1(rows,tf,rows[-1]['time']+60)
            for out in actual:
                group=[x for x in rows if out['time']<=x['time']<out['time']+n*60]
                self.assertEqual(n,len(group));self.assertEqual(group[0]['open'],out['open'])
                self.assertEqual(group[-1]['close'],out['close']);self.assertEqual(max(x['high'] for x in group),out['high'])
                self.assertEqual(sum(x['tick_volume'] for x in group),out['tick_volume'])
                self.assertEqual(group[0].get('spread',0),out['spread'])
        self.assertEqual(original,rows)

    def test_partial_and_missing_minute_buckets_are_not_fabricated(self):
        rows=minute_bars(180);as_of=rows[-1]['time']+60
        full=aggregate_m1(rows,'M5',as_of)
        chosen=full[1]['time']+60
        missing=aggregate_m1([x for x in rows if x['time']!=chosen],'M5',as_of)
        self.assertEqual(len(full)-1,len(missing))
        self.assertNotIn(full[1]['time'],[x['time'] for x in missing])

    def test_aggregated_short_history_cannot_bypass_walkforward_gate(self):
        rows=minute_bars(1423)
        for tf in ('M5','H1'):
            aggregated=aggregate_m1(rows,tf,rows[-1]['time']+60)
            self.assertLess(len(aggregated),500)
            with self.assertRaisesRegex(ValueError,'At least 500'):
                evaluate_history(aggregated,'engulfing',symbol='TEST',timeframe=tf,as_of=rows[-1]['time']+60,
                                 costs={'point':.00001,'slippage_price':.0001,'commission_per_unit':0.,'commission_known':True})

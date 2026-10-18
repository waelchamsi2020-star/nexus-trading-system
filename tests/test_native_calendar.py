"""Calendar parser fixtures are synthetic unit data, never broker performance evidence."""
import csv
import itertools
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from test_edge_gate import edge

from nexus.trading_calendar import expected_closure_gap
from nexus.walkforward import evaluate_history


def three_weeks(weeks=3, seconds=300):
    start=datetime(2026,1,4,22,tzinfo=UTC)
    return [{'time':int((start+timedelta(weeks=w,seconds=i*seconds)).timestamp()),
             'open':1.,'high':1.1,'low':.9,'close':1.,'tick_volume':10,'spread':7}
            for w in range(weeks) for i in range(5*86400//seconds)]


# Vulture review: unittest/pytest discovers this TestCase class.
class NativeCalendar(unittest.TestCase):
    def metadata(self):
        return {'source':'MT5_NATIVE','aggregated':False,'timeframe':'M5','timezone':'UTC','symbol':'EURUSD',
                'fee_source':'SYNTHETIC_UNIT_FIXTURE_NOT_BROKER','point':.00001,'contract_size':100000.,
                'commission_per_lot':5.,'account_currency':'USD','profit_currency':'USD'}

    def write(self,path,bars):
        with path.open('w',newline='') as handle:
            out=csv.writer(handle);out.writerow(['<DATE>','<TIME>','<OPEN>','<HIGH>','<LOW>','<CLOSE>','<TICKVOL>','<SPREAD>'])
            for b in bars:
                dt=datetime.fromtimestamp(b['time'],UTC)
                out.writerow([dt.strftime('%Y.%m.%d'),dt.strftime('%H:%M:%S'),b['open'],b['high'],b['low'],b['close'],b['tick_volume'],b['spread']])

    def test_three_trading_weeks_4320_two_weekends_calendar_passes_size_still_rejects(self):
        bars=three_weeks();self.assertEqual(4320,len(bars))
        self.assertEqual(2,sum(b['time']-a['time']>300 for a,b in itertools.pairwise(bars)))
        edge.validate_contiguity(bars,'M5','FX_UTC22_V1')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'SYNTHETIC.csv';self.write(path,bars)
            with self.assertRaisesRegex(ValueError,'5000'):edge.load_native(path,self.metadata(),2_000_000_000)

    def test_5000_native_parser_rows_cross_weekends_and_mid_tuesday_gap_is_rejected(self):
        bars=three_weeks(4)[:5000]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'SYNTHETIC.csv';self.write(path,bars)
            loaded,costs,_=edge.load_native(path,self.metadata(),2_000_000_000)
            self.assertEqual(5000,len(loaded));self.assertEqual(.0001,costs['slippage_price'])
            index=next(i for i,b in enumerate(bars) if datetime.fromtimestamp(b['time'],UTC).weekday()==1 and datetime.fromtimestamp(b['time'],UTC).hour==12)
            self.write(path,bars[:index]+bars[index+1:]+three_weeks(4)[5000:5001])
            with self.assertRaisesRegex(ValueError,'unexpected'):edge.load_native(path,self.metadata(),2_000_000_000)

    def test_holidays_allowed_only_when_all_missing_slots_are_closed(self):
        for month,day in ((12,25),(1,1)):
            start=int(datetime(2026,month,day,tzinfo=UTC).timestamp())
            with self.subTest(holiday=(month,day)):
                self.assertTrue(expected_closure_gap(start,start+86400,300,'FX_UTC22_V1'))
                self.assertFalse(expected_closure_gap(start,start+86400,300,'CONTINUOUS'))
        tuesday=int(datetime(2026,1,6,12,tzinfo=UTC).timestamp())
        self.assertFalse(expected_closure_gap(tuesday,tuesday+300,300,'FX_UTC22_V1'))
        self.assertFalse(expected_closure_gap(tuesday,tuesday+60,300,'FX_UTC22_V1'))
        self.assertFalse(expected_closure_gap(tuesday,tuesday+8*86400,300,'FX_UTC22_V1'))
        with self.assertRaises(ValueError):expected_closure_gap(tuesday,tuesday+300,300,'UNKNOWN')

    def test_calendar_does_not_mask_reopening_missing_bars_or_crypto_gaps(self):
        sunday=int(datetime(2026,1,11,22,tzinfo=UTC).timestamp())
        self.assertFalse(expected_closure_gap(sunday-2*86400,sunday+300,300,'FX_UTC22_V1'))
        self.assertEqual('CONTINUOUS',edge.calendar_profile({'symbol':'BTCUSD'}))
        self.assertEqual('FX_UTC22_V1',edge.calendar_profile({'symbol':'EURUSD.demo'}))
        with self.assertRaises(ValueError):edge.calendar_profile({'calendar_profile':'UNKNOWN'})

    def test_walkforward_uses_same_calendar_strict_default_and_h1_boundaries(self):
        bars=three_weeks()
        result={'folds':[],'metrics':{'net_r':0.,'sample_win_fraction':None,'max_drawdown_r':0.},'status':'FIXTURE'}
        costs={'point':.00001,'slippage_price':.0001,'commission_per_unit':.00005,'commission_known':True}
        with patch('nexus.walkforward.walk_forward',return_value=result) as run:
            with self.assertRaisesRegex(ValueError,'time gap'):
                evaluate_history(bars,'ema_cross',symbol='SYNTHETIC',timeframe='M5',as_of=2_000_000_000,costs=costs)
            run.assert_not_called()
            report=evaluate_history(bars,'ema_cross',symbol='SYNTHETIC',timeframe='M5',as_of=2_000_000_000,costs=costs,
                                    context={'calendar_profile':'FX_UTC22_V1'})
            self.assertFalse(report['qualified']);self.assertEqual(4320,report['review']['completed_bars'])
        edge.validate_contiguity(three_weeks(seconds=3600),'H1','FX_UTC22_V1')

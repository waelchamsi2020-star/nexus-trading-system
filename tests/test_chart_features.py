"""Original completed-chart feature snapshots, not profitability tests."""
import copy
import math
import unittest

from nexus.learning import digest
from nexus.strategies import _chart_features, analyze_strategy, validate_bars


def bars(n=90):
    result=[]
    for i in range(n):
        close=100+.03*i+.4*math.sin(i/4)
        result.append({'time': 1728000000+i*3600,'open': close-.08,
                           'high': close+.5,'low': close-.6,'close': close,
                           'tick_volume': 100+i%7,'real_volume': 0,'spread': 1})
    return result


class ChartFeatureTests(unittest.TestCase):
    def test_snapshot_fingerprint_and_completed_time_are_reproducible(self):
        data=bars();feature=_chart_features('TEST','H1',data,'broker')
        self.assertEqual(feature['source'],'completed_mt5_ohlc')
        self.assertEqual(feature['data_time'],data[-1]['time']+3600)
        unsigned={key:value for key,value in feature.items() if key!='feature_hash'}
        self.assertEqual(feature['feature_hash'],digest(unsigned))
        snapshot=[{key:row[key] for key in ('time','open','high','low','close','tick_volume')} for row in data[-41:]]
        self.assertEqual(feature['input_snapshot_hash'],digest(snapshot))
        self.assertTrue(all(math.isfinite(value) for value in feature['values'].values()))

    def test_features_depend_only_on_declared_window_and_are_detached(self):
        data=bars();before=_chart_features('TEST','H1',data,'broker')
        changed=copy.deepcopy(data);changed[0].update(close=10000,high=10001)
        self.assertEqual(before,_chart_features('TEST','H1',changed,'broker'))
        changed[-1]['tick_volume']+=10
        self.assertNotEqual(before['feature_hash'],_chart_features('TEST','H1',changed,'broker')['feature_hash'])
        self.assertEqual(before,_chart_features('TEST','H1',data,'broker'))

    def test_price_mirror_and_scale_consistency(self):
        data=bars();mirror=copy.deepcopy(data);scaled=copy.deepcopy(data)
        for row in mirror:
            o,h,l,c=[row[key] for key in ('open','high','low','close')]
            row.update(open=300-o,high=300-l,low=300-h,close=300-c)
        for row in scaled:
            for key in ('open','high','low','close'):row[key]*=3
        values=_chart_features('T','H1',data,'broker')['values']
        reverse=_chart_features('T','H1',mirror,'broker')['values']
        larger=_chart_features('T','H1',scaled,'broker')['values']
        directional=('return_1_atr','return_5_atr','ema_gap_atr','rsi_centered','close_location')
        for key in values:
            self.assertAlmostEqual(values[key],larger[key],places=10)
            self.assertAlmostEqual(reverse[key],-values[key] if key in directional else values[key],places=10)

    def test_missing_activity_and_invalid_scales_are_not_filled(self):
        for key,value in [('tick_volume',0),('tick_volume',True),('tick_volume',float('inf'))]:
            data=bars();data[-6][key]=value
            self.assertIsNone(_chart_features('T','H1',data,'broker'))
        self.assertIsNone(_chart_features('T','H1',bars(40),'broker'))
        flat=bars()
        for row in flat:row.update(open=100,high=100,low=100,close=100)
        self.assertIsNone(_chart_features('T','H1',flat,'broker'))

    def test_source_provenance_is_never_upgraded(self):
        for data_kind,expected in [('simulation','synthetic_completed_ohlc'),('unverified','completed_ohlc_undeclared')]:
            self.assertEqual(_chart_features('T','H1',bars(),data_kind)['source'],expected)

    def test_unfinished_bars_never_reach_analyzer_features(self):
        data=bars();now=data[-1]['time']+3600
        good=analyze_strategy('ema_cross','T','H1',data,now,{'data_kind':'broker'})
        self.assertIsNotNone(good['chart_features'])
        data.append({**data[-1],'time':now})
        bad=analyze_strategy('ema_cross','T','H1',data,now,{'data_kind':'broker'})
        self.assertEqual(bad['status'],'DATA_INVALID')
        self.assertNotIn('chart_features',bad)

    def test_nonfinite_or_extreme_features_are_excluded(self):
        data=bars();data[-1].update(open=1e308,high=1e308,low=1e307,close=1e308)
        # Valid positive price geometry can still be numerically unsuitable
        # for the declared bounded feature model; do not silently clip it.
        data=validate_bars(data,'H1',data[-1]['time']+3600)
        self.assertIsNone(_chart_features('T','H1',data,'broker'))


if __name__=='__main__':unittest.main()

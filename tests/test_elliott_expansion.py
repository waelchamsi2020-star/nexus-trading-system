import copy
import json
import unittest

from nexus import strategies as st
from nexus.specialists import elliott_impulse_reversal, elliott_zigzag_reversal


def sample(pattern='impulse', alterations=None):
    anchors=({0:110,40:100,48:110,56:105,64:124,70:114,76:130,79:127}
             if pattern=='impulse' else {0:100,52:120,60:100,68:112,76:95,79:98})
    anchors.update(alterations or {})
    keys=sorted(anchors);bars=[]
    for i in range(80):
        left=max(k for k in keys if k<=i);right=min((k for k in keys if k>i),default=left)
        value=anchors[left] if left==right else anchors[left]+(anchors[right]-anchors[left])*(i-left)/(right-left)
        bars.append({'time': 1728000000+i*3600,'open': value,'high': value+.2,'low': value-.2,'close': value,'tick_volume': 100})
    return bars


def mirror(bars):
    result=copy.deepcopy(bars)
    for x in result:x.update(open=250-x['open'],close=250-x['close'],high=250-x['low'],low=250-x['high'])
    return result


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ElliottExpansion(unittest.TestCase):
    def test_actual_confirmed_impulse_and_zigzag_geometry_have_symmetric_plans(self):
        for sid,pattern,direction in (('elliott_impulse_reversal','impulse','SELL'),('elliott_zigzag_reversal','zigzag','BUY')):
            bars=sample(pattern)
            card=st.analyze_strategy(sid,'TEST','H1',bars,bars[-1]['time']+3600)
            self.assertTrue(card['actionable'],card['evidence'])
            self.assertEqual(card['direction'],direction)
            evidence=card['evidence'][0]['value']
            self.assertTrue(all(evidence['geometry_rules'].values()))
            self.assertFalse(evidence['nested_subdivisions_verified'])
            self.assertFalse(evidence['count_is_unique'])
            self.assertLessEqual(evidence['pivots'][-1]['confirmed_at'],bars[-1]['time'])
            opposite=st.analyze_strategy(sid,'TEST','H1',mirror(bars),bars[-1]['time']+3600)
            self.assertTrue(opposite['actionable'])
            self.assertNotEqual(opposite['direction'],direction)
            json.dumps(card,allow_nan=False)

    def test_impulse_hard_geometry_constraints_reject_invalid_counts(self):
        for changes,failed in (({56:90},'wave2_above_origin'),({70:109},'wave4_no_overlap'),
                                ({48:120,56:108,64:125,70:121,76:150,79:146},'wave3_not_shortest_arithmetic'),
                                ({76:121,79:117},'nontruncated_wave5')):
            bars=sample('impulse',changes)
            result=elliott_impulse_reversal(bars,{'timeframe':'H1'})
            self.assertFalse(result['triggered'])
            if result['evidence']:
                self.assertFalse(result['evidence'][0]['value']['geometry_rules'][failed])

    def test_zigzag_geometry_ratios_are_declared_house_parameters(self):
        for changes in ({68:124},{68:103},{76:75}):
            result=elliott_zigzag_reversal(sample('zigzag',changes),{'timeframe':'H1'})
            self.assertFalse(result['triggered'])
        contract=st.REGISTRY['elliott_zigzag_reversal']['contract']
        self.assertEqual(contract['definition']['parameters']['B_retracement'],[.382,.786])
        self.assertIn('unverified',contract['definition']['scope'])
        self.assertFalse(contract['school_complete'])

    def test_no_trigger_before_confirmation_without_fresh_break_or_after_pivot_breach(self):
        for sid,pattern in (('elliott_impulse_reversal','impulse'),('elliott_zigzag_reversal','zigzag')):
            bars=sample(pattern)
            prefix=st.analyze_strategy(sid,'TEST','H1',bars[:-1],bars[-1]['time'])
            self.assertFalse(prefix['actionable'])
            bars=sample(pattern);bars[-1]['close']=bars[-2]['close'];bars[-1]['high']=max(bars[-1]['high'],bars[-1]['close'])
            bars[-1]['low']=min(bars[-1]['low'],bars[-1]['close'])
            self.assertFalse(st.analyze_strategy(sid,'TEST','H1',bars,bars[-1]['time']+3600)['actionable'])
            bars=sample(pattern)
            if pattern=='impulse':bars[-1]['high']=132
            else:bars[-1]['low']=90
            self.assertFalse(st.analyze_strategy(sid,'TEST','H1',bars,bars[-1]['time']+3600)['actionable'])

    def test_future_or_unfinished_primary_data_cannot_enable_wave_agent(self):
        for sid,pattern in (('elliott_impulse_reversal','impulse'),('elliott_zigzag_reversal','zigzag')):
            bars=sample(pattern)
            for data,now in ((bars,bars[-1]['time']+3599),(bars+[dict(bars[-1],time=bars[-1]['time']+3600)],bars[-1]['time']+3600)):
                card=st.analyze_strategy(sid,'TEST','H1',data,now)
                self.assertEqual(card['status'],'DATA_INVALID')
                self.assertFalse(card['actionable'])

"""Preliminary routing, isolation and fee repricing proofs; no financial efficacy claims."""
import copy
import itertools
import unittest
from unittest.mock import patch

from test_strategies import bars

from nexus.quant import replay
from nexus.segment_research import evaluate_segments, reprice, split_segments
from nexus.walkforward import LookaheadBiasError


# Vulture review: unittest/pytest discovers this TestCase class.
class SegmentResearch(unittest.TestCase):
    def test_fee_repricing_equals_independent_replay_all_three_scenarios(self):
        rows=bars(40)
        for row in rows:row.update(open=100.,close=100.,high=100.05,low=99.95,spread=2)
        def signal(history,as_of):
            if len(history)!=20:return {'status':'WAIT'}
            return {'status':'READY','direction':'BUY','entry':{'triggered':True,'zone':[99.,101.]},
                    'stop':{'price':98.},'targets':[{'price':105.}]}
        config={'point':.00001,'slippage_price':.0001,'commission_per_unit':0.}
        base=replay(rows,'engulfing',start_index=19,end_index=23,config=config,signal_fn=signal)['trades']
        self.assertTrue(base)
        for commission in (0.,3.,7.):
            direct=replay(rows,'engulfing',start_index=19,end_index=23,config={**config,'commission_per_unit':commission/100000.},signal_fn=signal)['trades']
            self.assertEqual(direct,reprice(base,commission/100000.))

    def test_segments_never_join_unexplained_gap_and_train_precedes_test(self):
        rows=bars(430,step=3600)
        for row in rows[210:]:row['time']+=3600
        observed=[]
        def check(segment,sid,symbol,tf,config,data_kind,context):
            observed.append([r['time'] for r in segment])
            self.assertTrue(all(b['time']-a['time']==3600 for a,b in itertools.pairwise(segment)))
            return {'folds':[]}
        with patch('nexus.segment_research.REGISTRY',{'ema_cross':None}),patch('nexus.segment_research.walk_forward',side_effect=check):
            result=evaluate_segments(rows,symbol='SYNTHETIC',timeframe='H1',as_of=2_000_000_000,
                costs={'point':.00001,'slippage_price':.0001,'commission_known':True},profile='CONTINUOUS',commissions=[0.,3.,7.],contract_size=100000.)
        self.assertEqual([210,220],[s['bars'] for s in result['segments']]);self.assertEqual(2,len(observed))
        self.assertEqual(2,result['selected_segments']);self.assertFalse(result['qualified']);self.assertFalse(result['execution_authority'])
        self.assertEqual([(105,46),(110,49)],[(w['train_bars'],w['test_bars']) for w in result['windows']])

    def test_short_fallback_future_and_duplicate_boundaries(self):
        rows=bars(180,step=3600)
        costs={'point':.00001,'slippage_price':.0001,'commission_known':True}
        args={'symbol':'SYNTHETIC','timeframe':'H1','as_of':2_000_000_000,'costs':costs,
              'profile':'CONTINUOUS','commissions':[0.,3.,7.],'contract_size':100000.}
        with patch('nexus.segment_research.REGISTRY',{'ema_cross':None}),patch('nexus.segment_research.walk_forward',return_value={'folds':[]}):
            result=evaluate_segments(rows,**args)
        self.assertTrue(result['fallback_largest_below_200']);self.assertEqual(1,result['selected_segments'])
        invalid=copy.deepcopy(rows);invalid[-1]['time']=2_000_000_000
        with self.assertRaises(LookaheadBiasError):evaluate_segments(invalid,**args)
        with self.assertRaises(ValueError):split_segments(rows[:2]+[rows[1]],'H1','CONTINUOUS')
        with self.assertRaises(ValueError):evaluate_segments(rows,**{**args,'contract_size':0})
        with self.assertRaises(ValueError):reprice([], -1.)

import unittest

from test_strategies import bars

from nexus.quant import replay


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class ReplayRejectionDiagnostics(unittest.TestCase):
    def run_case(self,opening,slip):
        rows=bars(40)
        for row in rows:
            row.update(open=100.,close=100.,high=101.,low=99.,spread=0)
        rows[20].update(open=opening,high=max(101.,opening),low=min(99.,opening))
        def signal(history,as_of):
            if len(history)!=20:return {'status':'WAIT'}
            return {'status':'READY','direction':'BUY','entry':{'triggered':True,'zone':[99.9,100.1]},
                    'stop':{'price':98.},'targets':[{'price':105.}]}
        return replay(rows,'engulfing',start_index=19,end_index=23,
                      config={'point':.01,'slippage_price':slip,'commission_per_unit':.1},signal_fn=signal)

    def test_cost_rejection_can_have_positive_target_scenario_and_keeps_gate(self):
        result=self.run_case(100.,.2)
        self.assertEqual([],result['trades'])
        diagnostic=result['skipped'][0]
        self.assertEqual('COST_ENTRY_ZONE_OR_BRACKET',diagnostic['classification'])
        self.assertTrue(diagnostic['raw_zone_ok'])
        self.assertAlmostEqual(4.5,diagnostic['target_net_price_scenario'])
        self.assertEqual(1,result['signals'])

    def test_raw_gap_is_not_misattributed_to_cost(self):
        result=self.run_case(100.5,.2)
        self.assertEqual([],result['trades'])
        diagnostic=result['skipped'][0]
        self.assertEqual('GAP_OR_STRUCTURE',diagnostic['classification'])
        self.assertFalse(diagnostic['raw_zone_ok'])

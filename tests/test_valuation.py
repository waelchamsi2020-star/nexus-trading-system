import unittest

from nexus.valuation import evaluate


def data(model,**fields):
    return dict(model=model,asset='EXAMPLE',currency='USD',as_of=2000,published_at=1000,source='fixture',**fields)

class ValuationTests(unittest.TestCase):
    def test_discount_cashflow_enterprise_equity_and_terminal_use_same_period_basis(self):
        result=evaluate(data('dcf',cashflows=[100,110],discount_rate=.1,terminal_growth=.02,debt=20,cash=5,shares=10))
        pv=100/1.1+110/1.1**2;terminal=110*1.02/(.1-.02)/1.1**2
        self.assertAlmostEqual(result['enterprise_value'],pv+terminal)
        self.assertAlmostEqual(result['value_per_share'],(pv+terminal-15)/10)
        self.assertFalse(result['execution_authority'])
    def test_ddm_nav_and_relative_models_have_distinct_units(self):
        self.assertAlmostEqual(evaluate(data('ddm',dividend_next=2,discount_rate=.1,dividend_growth=.02))['value_per_share'],25)
        self.assertEqual(evaluate(data('nav',assets_fair_value=120,liabilities=30,contingent_liabilities=10,shares=10))['value_per_share'],8)
        self.assertEqual(evaluate(data('multiples',basis='pe',peer_multiples=[10,12,50],metric=2))['value_per_share'],24)
        self.assertEqual(evaluate(data('multiples',basis='ev_sales',peer_multiples=[1,2,3],metric=100,debt=30,cash=10,shares=10))['value_per_share'],18)
    def test_bond_at_coupon_boundary_matches_par_when_coupon_equals_yield(self):
        result=evaluate(data('bond',par=100,coupon_rate=.06,yield_rate=.06,payments_per_year=2,periods=20))
        self.assertAlmostEqual(result['clean_price_at_coupon_boundary'],100)
    def test_present_value_can_discount_project_outflows(self):
        self.assertAlmostEqual(evaluate(data('pv',cashflows=[-100,121],discount_rate=.1))['present_value'],-100/1.1+121/1.1**2)
    def test_future_publication_invalid_growth_zero_shares_and_nonfinite_rejected(self):
        base=data('dcf',cashflows=[100],discount_rate=.1,terminal_growth=.02,debt=0,cash=0,shares=10)
        for key,value in [('published_at',2001),('terminal_growth',.1),('shares',0),('cash',float('nan')),('discount_rate',True),('cashflows',[float('inf')])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                evaluate({**base, key: value})
        with self.assertRaises(ValueError):evaluate(data('multiples',basis='pe',peer_multiples=[10,20],metric=3))

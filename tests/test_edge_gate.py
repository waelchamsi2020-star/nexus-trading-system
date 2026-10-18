import csv
import importlib.util
import random
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

spec=importlib.util.spec_from_file_location('edge_gate',Path(__file__).resolve().parents[1]/'tools/edge_test.py')
edge=importlib.util.module_from_spec(spec);spec.loader.exec_module(edge)


# Vulture review: unittest/pytest discovers this TestCase class.
class EdgeGate(unittest.TestCase):
    def test_known_positive_synthetic_payoffs_cross_declared_threshold_only(self):
        self.assertEqual('EDGE_FOUND',edge.edge_status({'trades':40,'net_r':20.}))
        self.assertEqual('NO_EDGE_FOUND',edge.edge_status({'trades':29,'net_r':20.}))

    def test_seeded_random_negative_control_has_no_edge_not_a_universal_null_claim(self):
        generator=random.Random(1);values=[1. if generator.random()>.5 else -1. for _ in range(60)]
        self.assertEqual('NO_EDGE_FOUND',edge.edge_status({'trades':len(values),'net_r':sum(values)}))

    def test_native_contract_5000_contiguous_costs_and_rejection_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.csv'
            def write(count=5000,gap=False):
                with path.open('w',newline='') as handle:
                    out=csv.writer(handle,delimiter='\t');out.writerow(['<DATE>','<TIME>','<OPEN>','<HIGH>','<LOW>','<CLOSE>','<TICKVOL>','<SPREAD>'])
                    for i in range(count):
                        stamp=datetime(2020,1,1,tzinfo=UTC)+timedelta(minutes=5*(i+(1 if gap and i>=50 else 0)))
                        out.writerow([stamp.strftime('%Y.%m.%d'),stamp.strftime('%H:%M:%S'),1.,1.1,.9,1.,10,7])
            metadata={'source':'MT5_NATIVE','aggregated':False,'timeframe':'M5','timezone':'UTC','symbol':'SYNTHETIC_PARSER_TEST',
                      'fee_source':'Explicit synthetic parser fixture; not actual broker data','point':.00001,'contract_size':100000.,
                      'commission_per_lot':5.,'account_currency':'USD','profit_currency':'USD'}
            write();rows,costs,fingerprint=edge.load_native(path,metadata,2_000_000_000)
            self.assertEqual(5000,len(rows));self.assertEqual(64,len(fingerprint))
            self.assertEqual(.0001,costs['slippage_price']);self.assertEqual(.00005,costs['commission_per_unit'])
            for key,value in (('aggregated',True),('timeframe','M1'),('point',float('nan')),('timezone','BROKER_LOCAL'),('fee_source',''),('account_currency','EUR')):
                with self.subTest(key=key),self.assertRaises(ValueError):edge.load_native(path,{**metadata,key:value},2_000_000_000)
            write(4999)
            with self.assertRaisesRegex(ValueError,'5000'):edge.load_native(path,metadata,2_000_000_000)
            write(gap=True)
            with self.assertRaisesRegex(ValueError,'gap'):edge.load_native(path,metadata,2_000_000_000)

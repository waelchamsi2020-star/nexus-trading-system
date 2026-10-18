import copy
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from test_specialists import bar, fixture, sample

from nexus import local_models as lm
from nexus import strategies as st
from nexus.engine import Engine


def data(id):
    b=sample();c={"symbol":"PRIMARY","timeframe":"H1","as_of":b[-1]["time"]+3600,"atr":1,"pivots":[]}
    if id in ("interasset_confirmation","smt_proxy"):
        partner=copy.deepcopy(b)
        if id=="interasset_confirmation":
            bar(b,-1,100.2,103.2,100,103);bar(partner,-1,100.2,103.2,100,103)
        else:
            bar(b,-1,99.8,100.4,99,100.3);bar(partner,-1,100.1,100.4,99.6,100.3)
        c.update(partner_symbol="PARTNER",partner_bars=partner)
    elif id=="elliott_candidate":
        c["pivots"]=[{"kind": k,"price": p,"index": i,"time": b[i]["time"],"confirmed_at": b[i+2]["time"]+3600}
                     for k,p,i in [("LOW",100,50),("HIGH",110,60),("LOW",104,70)]]
        for i in range(71,79):bar(b,i,105+(i-71)*.5,105.2+(i-71)*.5,104.8+(i-71)*.5,105+(i-71)*.5)
        bar(b,-1,109,111.2,108.9,111)
    elif id=="wyckoff_spring":
        for i in range(80):bar(b,i,105,105.2,104.8,105)
        b[40]["low"]=100;b[50]["high"]=110
        bar(b,-4,100.5,101,99,100.8);b[-4]["tick_volume"]=200
        bar(b,-3,102,102.2,101.8,102)
        bar(b,-2,100.8,101,100.6,100.8)
        bar(b,-1,100.5,102,100.05,101.8);b[-1]["tick_volume"]=50
    elif id=="smc_ict_proxy":
        b=fixture("fvg_first_return");bar(b,-5,99.8,100.5,99,100)
    elif id=="supply_demand_proxy":b=fixture("base_first_return")
    elif id=="gann":
        c["pivots"]=[{"kind": "LOW","price": 99,"index": 70,"time": b[70]["time"],"confirmed_at": b[72]["time"]+3600}]
        bar(b,-1,100.2,105.2,100,105)
    elif id=="order_flow":
        bar(b,-2,100,100.5,99.5,100)
        bar(b,-1,100.5,102.2,100,102);b[-1]["tick_volume"]=200
    elif id=="seasonality":
        now=datetime(2026,10,10,tzinfo=UTC).timestamp()
        for i,x in enumerate(b):x["time"]=now-(80-i)*3600
        bar(b,-1,100.2,103.2,100,103)
        daily=[]
        for year in (2021,2022,2023,2024,2025):
            for day in range(1,29):
                price=100+(day/28)*(2+(year-2021)*.1)
                daily.append({"time": datetime(year,10,day,tzinfo=UTC).timestamp(),"open": 100,
                                  "high": max(100,price)+.1,"low": 99.9,"close": price,"tick_volume": 100})
        c.update(daily_bars=daily,symbol_info={"currency_base":"EUR","currency_profit":"USD"})
    c["as_of"]=b[-1]["time"]+3600
    return b,c


def mirror(b,c):
    for items in (b,c.get("partner_bars",[]),c.get("daily_bars",[])):
        for x in items:
            x.update(open=240-x["open"],close=240-x["close"],high=240-x["low"],low=240-x["high"])
    for p in c["pivots"]:p.update(price=240-p["price"],kind="HIGH" if p["kind"]=="LOW" else "LOW")


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class LocalModels(unittest.TestCase):
    def test_each_former_placeholder_has_buy_and_sell_rules_and_price_plan(self):
        for id,(fn,*_) in lm.MODELS.items():
            with self.subTest(id=id):
                b,c=data(id)
                for side in ("BUY","SELL"):
                    result=fn(b,c)
                    self.assertTrue(result["triggered"], result)
                    self.assertEqual(result["direction"],side)
                    # Pivots are provided to isolate each formula; the common
                    # causal pivot extractor has independent future-data tests.
                    with patch.object(st,"causal_pivots",return_value=c["pivots"]):
                        card=st.analyze_strategy(id,"PRIMARY","H1",b,c["as_of"],c)
                    self.assertTrue(card["actionable"],card)
                    self.assertEqual(card["version"],st.REGISTRY[id]["version"])
                    self.assertFalse(card["contract"]["school_complete"])
                    self.assertTrue(card["stop"]["price"]<card["entry"]["price"]<card["targets"][0]["price"] if side=="BUY" else
                                    card["targets"][0]["price"]<card["entry"]["price"]<card["stop"]["price"])
                    mirror(b,c)

    def test_pair_identity_alignment_and_future_records(self):
        for id in ("smt_proxy","interasset_confirmation"):
            b,c=data(id);fn=lm.MODELS[id][0]
            base=fn(b,c)
            future=dict(c["partner_bars"][-1],time=c["as_of"]+3600,close=1000,high=1001)
            c["partner_bars"].append(future)
            self.assertEqual(fn(b,c),base)
            c["partner_symbol"]="PRIMARY"
            self.assertEqual(fn(b,c)["status"],"DATA_MISSING")
            c["partner_symbol"]="PARTNER";c["partner_bars"]=c["partner_bars"][:20]
            self.assertEqual(fn(b,c)["status"],"DATA_MISSING")

    def test_monthly_missing_history_unsupported_instrument_and_future_exclusion(self):
        b,c=data("seasonality");baseline=lm.monthly_bias(b,c)
        c["daily_bars"].append(dict(c["daily_bars"][-1],time=c["as_of"]+86400,close=200))
        self.assertEqual(lm.monthly_bias(b,c),baseline)
        c["daily_bars"]=c["daily_bars"][:28]
        self.assertEqual(lm.monthly_bias(b,c)["status"],"DATA_MISSING")
        b,c=data("seasonality");c["symbol_info"]["currency_base"]="XAU"
        self.assertEqual(lm.monthly_bias(b,c)["status"],"DATA_MISSING")

    def test_wave_and_grid_expire_and_reject_broken_anchor(self):
        for id in ("elliott_candidate","gann"):
            b,c=data(id);b[-1]["low"]=90
            self.assertFalse(lm.MODELS[id][0](b,c)["triggered"])
            b,c=data(id)
            for p in c["pivots"]:p["index"]-=40
            self.assertFalse(lm.MODELS[id][0](b,c)["triggered"])

    def test_liquidity_sweep_and_activity_data_are_required(self):
        b,c=data("smc_ict_proxy");b[-5]["low"]=99.5
        self.assertFalse(lm.liquidity_gap(b,c)["triggered"])
        b,c=data("order_flow");b[-2]["tick_volume"]=0
        self.assertEqual(lm.activity_flow(b,c)["status"],"DATA_MISSING")

    def test_engine_resolves_only_declared_unique_metadata_pairs_and_caches(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        temp=directory.name
        engine=Engine(Path(temp),Path(temp)/"data",clock=lambda:1000)
        self.addCleanup(engine.analysis_pool.shutdown,wait=False)
        self.addCleanup(engine.news.db.close);self.addCleanup(engine.cache.db.close)
        calls=[]
        class Broker:
            is_simulation=False
            def symbol(self,name):return {"point": .0001,"trade_tick_size": .0001,"currency_base": "EUR","currency_profit": "USD"}
            def symbols(self):return [{"name": "GBPUSD.custom","currency_base": "GBP","currency_profit": "USD"}]
            def select(self,name):calls.append(("select",name))
            def bars(self,name,tf,count):calls.append((name,tf,count));return sample()
        engine.broker=Broker()
        a=engine._context("EURUSD.custom","M5");engine._context("EURUSD.custom","M5")
        self.assertEqual(a["partner_symbol"],"GBPUSD.custom")
        self.assertEqual(sum(x==("GBPUSD.custom","M5",300) for x in calls),1)
        self.assertEqual(sum(x==("EURUSD.custom","D1",1500) for x in calls),1)
        engine.partner_catalog*=2
        self.assertNotIn("partner_symbol",engine._context("EURUSD.custom","M5"))

    def test_every_local_model_rejects_unfinished_main_bar(self):
        for id in lm.MODELS:
            b,c=data(id)
            self.assertFalse(st.analyze_strategy(id,"PRIMARY","H1",b,b[-1]["time"],c)["actionable"])

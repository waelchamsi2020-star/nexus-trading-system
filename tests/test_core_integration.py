"""Synthetic component/system tests. These never send orders to MT5."""
import copy
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

from nexus.broker import TIMEFRAMES, BrokerError, MT5Broker, SimBroker
from nexus.engine import PLAN_VERSION, Engine
from nexus.market import (
    UniverseScanner,
    classify,
    spread_filter_required,
    validate_bars,
)
from nexus.news import SOURCES, NewsManager, fetch_source, parse_timestamp
from nexus.server import LocalServer
from nexus.store import account_key
from nexus.strategies import REGISTRY

ROOT=Path(__file__).resolve().parents[1]


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.now=time.time();self.b=SimBroker(lambda:self.now)
    def test_complete_universe_outside_watch_and_truthful_scan(self):
        self.assertTrue(all(not s["visible"] for s in self.b.symbols()))
        scanner=UniverseScanner(self.b,lambda:self.now);scanner.begin()
        first=scanner.step(2)
        self.assertEqual(first["discovered"],6);self.assertEqual(first["checked"],2);self.assertFalse(first["complete"])
        done=scanner.step(99)
        self.assertTrue(done["complete"]);self.assertEqual(done["checked"],6);self.assertEqual(done["eligible"],5)
        closed=next(r for r in done["rows"] if r["symbol"]=="CLOSED.asset")
        self.assertFalse(closed["eligible"]);self.assertIn("السوق مغلق",closed["reasons"][0])
        self.assertTrue(self.b.symbol("GOLD#")["visible"])
    def test_spread_cutoff_waiver_keeps_costs_and_stale_quote_gate(self):
        scanner=UniverseScanner(self.b,lambda:self.now)
        tick=self.b.tick
        def wide(name):
            t=tick(name);t['ask']=t['bid']*1.05;return t
        self.b.tick=wide
        scanner.begin();scanner.step(99)
        self.assertFalse(scanner.rows['EURUSD.demo']['eligible'])
        self.assertIn('السبريد مرتفع مقارنة بالنطاق الأخير',scanner.rows['EURUSD.demo']['reasons'])
        scanner.spread_filter=False;scanner.begin();scanner.step(99)
        self.assertTrue(scanner.rows['EURUSD.demo']['eligible'])
        self.assertGreater(scanner.rows['EURUSD.demo']['spread'],0)
        def stale(name):
            t=wide(name);t['time']=self.now-300;return t
        self.b.tick=stale;scanner.begin();scanner.step(99)
        self.assertFalse(scanner.rows['EURUSD.demo']['eligible'])
        self.assertFalse(scanner.rows['CLOSED.asset']['eligible'])

    def test_spread_waiver_requires_authorized_actual_fast_demo(self):
        settings={'decision_protocol':'multi_school_v1','validation_policy':'forward_demo',
            'scalp_only':True,'scalping':{'fast':{'enabled':True},'normal':{'enabled':False}}}
        self.assertFalse(spread_filter_required(settings,{'trade_mode':0}))
        for mode in (1,2,None,False):
            self.assertTrue(spread_filter_required(settings,{'trade_mode':mode}))
        self.assertTrue(spread_filter_required(settings,{'trade_mode':0},simulation=True))
        for key,value in (('decision_protocol','general'),('validation_policy','historical'),('scalp_only',False),
                ('scalping',{'normal':{'enabled':True},'fast':{'enabled':True}})):
            self.assertTrue(spread_filter_required({**settings,key:value},{'trade_mode':0}))

    def test_classification_uses_contract_not_fixed_symbol_name(self):
        i=self.b.symbol("EURUSD.demo");i["name"]="broker-weird-123"
        self.assertEqual(classify(i),"forex")
        self.assertEqual(classify(self.b.symbol("GOLD#")),"metals")
        self.assertEqual(classify(self.b.symbol("OIL-FUT")),"energy")
    def test_classification_respects_official_calculation_mode_enums(self):
        info={"path":"Broker instruments","description":"","currency_base":"","currency_profit":"USD","expiration_time":0}
        for mode,category in ((1,"futures"),(33,"futures"),(32,"stocks"),(38,"stocks"),(2,"other"),(4,"other"),(34,"other"),(36,"other")):
            with self.subTest(mode=mode):self.assertEqual(classify({**info,"trade_calc_mode":mode}),category)
        self.assertEqual(classify({**info,"trade_calc_mode":34,"expiration_time":self.now+86400}),"other")
    def test_stale_future_or_unknown_session_blocks_symbol(self):
        scanner=UniverseScanner(self.b,lambda:self.now)
        original=self.b.tick
        def stale(name):
            t=original(name);t["time"]=self.now-300;return t
        self.b.tick=stale;scanner.begin();scanner.step(99)
        self.assertEqual(scanner.snapshot()["eligible"],0)
        self.b.tick=original;self.b.session=lambda name:{"known":False,"open":False,"as_of":self.now,"reason":"unknown"}
        scanner.begin();scanner.step(99);self.assertEqual(scanner.snapshot()["eligible"],0)
    def test_all_bar_requests_are_closed_and_prefix_consistent(self):
        self.assertEqual(tuple(TIMEFRAMES),(
            "M1","M2","M3","M4","M5","M6","M10","M12","M15","M20","M30",
            "H1","H2","H3","H4","H6","H8","H12","D1","W1","MN1",
        ))
        for tf,seconds in TIMEFRAMES.items():
            a=self.b.bars("GOLD#",tf,100);b=self.b.bars("GOLD#",tf,200)
            self.assertEqual(a,b[-100:]);self.assertTrue(all(x["time"]+seconds<=self.now for x in a))
            self.assertEqual(validate_bars(a,tf,self.now),[])
            bad=copy.deepcopy(a);bad[-1]["time"]=self.now
            self.assertTrue(validate_bars(bad,tf,self.now))
    def test_malformed_contract_and_expired_futures_reject(self):
        self.b._symbols["OIL-FUT"]["expiration_time"]=self.now-1
        self.b._symbols["STOCK.A"]["volume_step"]=0
        scanner=UniverseScanner(self.b,lambda:self.now);scanner.begin();scanner.step(99)
        self.assertFalse(scanner.rows["OIL-FUT"]["eligible"]);self.assertFalse(scanner.rows["STOCK.A"]["eligible"])


class BrokerAdapterTests(unittest.TestCase):
    """Official installed Python enums; no initialize, MT5 calls or orders."""
    def setUp(self):
        import MetaTrader5 as mt5
        self.mt5 = mt5
        self.broker = MT5Broker.__new__(MT5Broker)
        self.broker.mt5 = mt5
        self.broker.symbol = Mock()
        self.request = {"action": "DEAL", "side": "BUY", "symbol": "ENUM-FIXTURE", "volume": .01,
                        "price": 100., "sl": 90., "tp": 120., "magic": 741903, "comment": "fixture",
                        "_authorized_account_key": "not-a-live-account"}

    def raw(self, mask, execution_mode):
        self.broker.symbol.return_value = {"filling_mode": mask, "trade_exemode": execution_mode}
        with patch.object(self.mt5, "initialize") as initialize, patch.object(self.mt5, "order_check") as check, patch.object(self.mt5, "order_send") as send:
            result = self.broker._request(self.request)
            initialize.assert_not_called();check.assert_not_called();send.assert_not_called()
        return result

    def test_official_module_symbol_masks_map_to_request_filling_enums(self):
        for mask, expected in ((1, self.mt5.ORDER_FILLING_FOK), (2, self.mt5.ORDER_FILLING_IOC),
                               (3, self.mt5.ORDER_FILLING_FOK)):
            with self.subTest(mask=mask):
                result = self.raw(mask, self.mt5.SYMBOL_TRADE_EXECUTION_MARKET)
                self.assertEqual(result["type_filling"], expected)
                self.assertEqual(result["type"], self.mt5.ORDER_TYPE_BUY)
                self.assertEqual(result["action"], self.mt5.TRADE_ACTION_DEAL)
                self.assertNotIn("_authorized_account_key", result)

    def test_return_filling_only_falls_back_on_known_nonmarket_execution(self):
        for mode in (self.mt5.SYMBOL_TRADE_EXECUTION_REQUEST, self.mt5.SYMBOL_TRADE_EXECUTION_INSTANT,
                     self.mt5.SYMBOL_TRADE_EXECUTION_EXCHANGE):
            with self.subTest(mode=mode):
                self.assertEqual(self.raw(0, mode)["type_filling"], self.mt5.ORDER_FILLING_RETURN)
        for mask in (0, 4):
            with self.subTest(mask=mask), self.assertRaises(BrokerError):
                self.raw(mask, self.mt5.SYMBOL_TRADE_EXECUTION_MARKET)

    def test_unknown_filling_mask_or_execution_mode_fails_closed(self):
        for mask, mode in ((8, self.mt5.SYMBOL_TRADE_EXECUTION_MARKET), (-1, 2), (None, 2), (1, 99), (0, None)):
            with self.subTest(mask=mask, mode=mode), self.assertRaises(BrokerError):
                self.raw(mask, mode)

    def test_reconnect_rebinds_mt5_ipc_and_refreshes_bridge_path(self):
        fake=Mock()
        fake.initialize.return_value=True
        fake.terminal_info.return_value={"connected":True,"path":r"C:\Program Files\Broker\terminal64.exe","data_path":r"C:\BrokerData"}
        fake.account_info.return_value={"login":123,"server":"DEMO","trade_mode":0}
        broker=MT5Broker.__new__(MT5Broker)
        broker.mt5=fake;broker.lock=threading.RLock();broker._initialize_args=[];broker._bridge_override=""
        result=broker.reconnect()
        fake.shutdown.assert_called_once_with();fake.initialize.assert_called_once_with(timeout=10000)
        self.assertTrue(result["connected"])
        self.assertEqual(broker.bridge_path,Path(r"C:\BrokerData")/"MQL5"/"Files"/"NEXUS_bridge.json")
        self.assertEqual(broker.account()["platform_id"],broker.platform_id)

    def test_cancel_and_protection_translate_using_official_action_enums(self):
        for action, expected in (("REMOVE", self.mt5.TRADE_ACTION_REMOVE), ("SLTP", self.mt5.TRADE_ACTION_SLTP)):
            with self.subTest(action=action):
                raw = self.broker._request({**self.request, "action": action, "position": 1, "order": 2})
                self.assertEqual(raw["action"], expected)
                self.assertNotIn("type_filling", raw)
                self.assertNotIn("side", raw)
        self.broker.symbol.assert_not_called()

    def test_pinned_sdk_receives_expanded_fields_and_send_still_checks_demo(self):
        self.broker.lock = threading.RLock()
        self.broker.symbol.return_value = {"filling_mode": 1, "trade_exemode": self.mt5.SYMBOL_TRADE_EXECUTION_MARKET}
        account = {"trade_mode": 0, "login": 1, "server": "FIXTURE", "platform_id": "FIXTURE", "trade_allowed": True}
        self.broker.account = Mock(return_value=account)
        self.broker.terminal = Mock(return_value={"connected": True, "trade_allowed": True, "tradeapi_disabled": False})
        request = {**self.request, "_authorized_account_key": account_key(account)}
        def native_fake(*args, **kwargs):
            self.assertEqual(args, ())
            self.assertNotIn("request", kwargs)
            self.assertNotIn("_authorized_account_key", kwargs)
            self.assertEqual(kwargs["action"], self.mt5.TRADE_ACTION_DEAL)
            self.assertEqual(kwargs["symbol"], "ENUM-FIXTURE")
            self.assertEqual(kwargs["volume"], .01)
            return {"retcode": 0, "request": kwargs}
        with patch.object(self.mt5, "initialize") as initialize, patch.object(self.mt5, "order_check", side_effect=native_fake) as check, patch.object(self.mt5, "order_send", side_effect=native_fake) as send:
            self.broker.check(request)
            self.broker.send(request)
            check.assert_called_once();send.assert_called_once();initialize.assert_not_called()
            account["trade_mode"] = 2
            with self.assertRaises(BrokerError):self.broker.send(request)
            account["trade_mode"] = 0
            with self.assertRaises(BrokerError):self.broker.send({**request, "_authorized_account_key": "another-platform"})
            send.assert_called_once()


class NewsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=time.time();self.b=SimBroker(lambda:self.now)
        self.news=NewsManager(Path(self.tmp.name)/"news.sqlite3",lambda:self.now,external_feeds=True)
        self.addCleanup(self.news.db.close)
    def test_publisher_timezone_is_explicit(self):
        self.assertEqual(parse_timestamp("2026-09-30T12:00:00+04:00"),parse_timestamp("2026-09-30T08:00:00Z"))
        self.assertIsNone(parse_timestamp("2026-09-30T12:00:00"))
    def test_mt5_only_policy_never_fetches_or_reuses_external_cache(self):
        self.news.db.execute("INSERT OR REPLACE INTO cache VALUES('feeds',?)",
                             (json.dumps([[{"status":"OK","name":"old"}],[{"title":"cached external title"}]]),))
        self.news.db.commit()
        fetch=Mock(side_effect=AssertionError("No external fetch allowed"))
        local=NewsManager(Path(self.tmp.name)/"news.sqlite3",lambda:self.now,fetcher=fetch)
        self.addCleanup(local.db.close)
        with patch("urllib.request.urlopen",side_effect=AssertionError("No HTTP allowed")) as http:
            local.refresh(blocking=True);local.refresh()
            snapshot=local.snapshot(self.b.calendar())
            self.assertEqual(snapshot["items"],[])
            self.assertEqual(snapshot["data_policy"],"MT5_ONLY")
            self.assertEqual(snapshot["sources"][0]["id"],"mt5_calendar")
            fetch.assert_not_called();http.assert_not_called()
        gate=local.gate(self.b.symbol("EURUSD.demo"),self.b.calendar())
        self.assertTrue(gate["ok"])
        self.assertFalse(gate["coverage"]["official_feeds"])
        broken=self.b.calendar();broken["ok"]=False
        self.assertFalse(local.gate(self.b.symbol("EURUSD.demo"),broken)["ok"])
    def test_rss_gap_is_reported_but_calendar_remains_the_hard_event_gate(self):
        result=self.news.gate(self.b.symbol("EURUSD.demo"),self.b.calendar())
        self.assertTrue(result["ok"])
        self.assertFalse(result["coverage"]["official_feeds"])
        self.assertTrue(result["coverage"]["calendar"])
        self.assertTrue(self.news.gate(self.b.symbol("EURUSD.demo"),self.b.calendar(),True)["ok"])
    def test_calendar_missing_old_window_or_event_blocks(self):
        info=self.b.symbol("EURUSD.demo");c=self.b.calendar()
        c["ok"]=False;self.assertFalse(self.news.gate(info,c,True)["ok"])
        c=self.b.calendar();c["as_of"]=self.now-500;self.assertFalse(self.news.gate(info,c,True)["ok"])
        c=self.b.calendar();c["to_utc"]=self.now+30;self.assertFalse(self.news.gate(info,c,True)["ok"])
        c=self.b.calendar();c["events"]=[{"currency":"USD","importance":3,"time_utc":self.now+600,"time_mode":0}]
        result=self.news.gate(info,c,True);self.assertTrue(result["blackout"]);self.assertFalse(result["ok"])
    def test_xml_injection_and_links_are_rejected(self):
        class Response:
            url=SOURCES[0]["url"]
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return b'<!DOCTYPE rss [<!ENTITY bad SYSTEM "file:///secret">]><rss />'
        with patch("urllib.request.urlopen",return_value=Response()):
            state,items=fetch_source(SOURCES[0],self.now)
        self.assertEqual(state["status"],"ERROR");self.assertEqual(items,[])
    def test_unknown_high_impact_timing_fails_closed(self):
        for invalid_time in (None,float("nan"),0,True):
            c=self.b.calendar();c["events"]=[{"currency":"USD","importance":3,"time_utc":invalid_time,"time_mode":0}]
            result=self.news.gate(self.b.symbol("EURUSD.demo"),c,True)
            self.assertFalse(result["ok"]);self.assertTrue(result["blackout"])
    def test_item_freshness_is_recomputed_after_cached_time_passes(self):
        self.news.items=[{"published_at":self.now-86400*31,"fresh":True,"source":"old"}]
        self.assertFalse(self.news.snapshot()["items"][0]["fresh"])


class EngineTests(unittest.TestCase):
    def test_performance_counts_standalone_owned_fee_once_and_reports_unallocated_cost(self):
        entry = {"id": "a"*64, "kind": "ENTRY", "state": "CLOSED", "reserved": 0,
                 "payload": {"position_ids": [77], "result": {"order": 88}, "proposal": {"strategy_id": "fixture", "symbol": "fixture"}}}
        now=self.e.clock()
        self.e.broker._deals = [
            {"ticket": 1, "type": 0, "entry": 1, "position_id": 77, "order": 89, "magic": 741903, "profit": 100., "time": now},
            {"ticket": 2, "type": 7, "position_id": 77, "order": 88, "magic": 0, "profit": -3., "time": now},
            {"ticket": 3, "type": 4, "magic": 0, "profit": -5., "time": now},
            {"ticket": 4, "type": 2, "magic": 0, "profit": 5000., "time": now},
        ]
        result=self.e._performance([entry]);row=result["rows"][0]
        self.assertEqual(row["gross"],100);self.assertEqual(row["costs"],-3);self.assertEqual(row["net"],97)
        self.assertEqual(result["closed_trades"],1);self.assertEqual(result["unattributed_costs"],5)
        self.assertEqual(result["cost_uncertainty"],[])
        # A repeated position identifier cannot assign one financial record to
        # two strategy rows. Ambiguous data is surfaced instead of doubled.
        other=copy.deepcopy(entry);other["id"]="b"*64;other["payload"]["result"]={"order":99}
        result=self.e._performance([entry,other])
        self.assertEqual(result["net_realized"],0)
        self.assertEqual(result["unattributed_costs"],8)
        self.assertTrue(result["cost_uncertainty"])
    def test_manual_flatten_stops_auto_entries_before_closing(self):
        engine=Engine.__new__(Engine);engine.broker=object();engine.executor=Mock();engine.status="AUTO_DEMO"
        engine.executor.flatten_owned_positions.return_value={"results":[]}
        result=engine._action({"action":"flatten"})
        self.assertTrue(result["ok"])
        self.assertEqual([call[0] for call in engine.executor.mock_calls],["stop_entries","flatten_owned_positions"])
        self.assertEqual(engine.status,"ENTRIES_STOPPED")
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.e=Engine(ROOT,Path(self.tmp.name));self.e._connect(True)
        self.addCleanup(self.close)
    def close(self):
        self.e.stop_worker()
        if self.e.store:self.e.store.close()
        self.e.cache.db.close();self.e.news.db.close()
    def settings(self):
        return {"action":"start","risk_value":100,"target_value":50,"unit":"money","mode":"AUTO_DEMO","commission_per_lot":0,"slippage_points":10}
    def test_start_needs_user_values_and_never_activates_on_launch(self):
        self.assertEqual(self.e.executor.status()["mode"],"READ_ONLY")
        with self.assertRaises(ValueError):self.e._action({"action":"start","risk_value":100,"target_value":50})
        self.assertEqual(self.e.executor.status()["mode"],"READ_ONLY")
        self.e._action(self.settings());self.assertEqual(self.e.executor.status()["mode"],"AUTO_DEMO")
    def test_shutdown_revokes_authorization_before_waiting_for_analysis(self):
        self.e._action(self.settings())
        self.e.thread=Mock()
        def finish_analysis(**kwargs):
            self.assertTrue(self.e.research_cancel.is_set())
            status=self.e.executor.status()
            self.assertEqual(status["mode"],"READ_ONLY")
            self.assertTrue(status["entries_paused"])
        self.e.thread.join.side_effect=finish_analysis
        self.e.stop_worker()
    def test_percent_is_equity_and_reactivation_keeps_original_day(self):
        p=self.settings();p.update(unit="percent",risk_value=1,target_value=.5)
        self.e._action(p);self.assertEqual(self.e.risk.settings["risk_amount"],100)
        p.update(risk_value=10,target_value=10);self.e._action(p)
        self.assertEqual(self.e.risk.settings["risk_amount"],100);self.assertEqual(self.e.risk.settings["target_amount"],50)

    def test_explicit_amendment_tightens_risk_and_changes_target_without_reset(self):
        self.e._action(self.settings());before=self.e.store.get_day(self.e.risk.key,self.e.clock())
        p=self.settings();p.update(risk_value=50,target_value=100,amend_daily_limits=True)
        self.e._action(p);after=self.e.store.get_day(self.e.risk.key,self.e.clock())
        self.assertEqual(after["risk_amount"],50);self.assertEqual(after["target_amount"],100)
        self.assertEqual(after["created"],before["created"]);self.assertEqual(after["equity_start"],before["equity_start"])
        p["risk_value"]=60
        with self.assertRaises(ValueError):self.e._action(p)
        self.e.store.halt_day(self.e.risk.key,"DAILY_LOSS",self.e.clock());p["risk_value"]=40
        with self.assertRaises(ValueError):self.e._action(p)
    def test_scan_chart_cards_and_synthetic_evidence_do_not_trade(self):
        self.e.scanner.step(99)
        self.e._analyze_symbol("EURUSD.demo")
        self.e._action({"action":"chart","symbol":"EURUSD.demo","timeframe":"M15"})
        self.e._publish();state=self.e.snapshot()
        self.assertTrue(state["simulation"]);self.assertEqual(len(state["chart"]["cards"]),len(REGISTRY))
        self.assertTrue(state["chart"]["bars"]);self.assertEqual(self.e.broker.sent,[])
        self.assertFalse(any(r.get("qualified") for r in state["quant_results"]))
        for timeframe in ("M1","M5","D1","MN1"):
            self.e._action({"action":"chart","symbol":"EURUSD.demo","timeframe":timeframe})
            self.assertEqual(self.e.chart["timeframe"],timeframe)
            self.assertTrue(self.e.chart["bars"])
        with self.assertRaises(ValueError):self.e._action({"action":"chart","symbol":"EURUSD.demo","timeframe":"Q1"})
    def test_actual_readonly_policy_on_real_account(self):
        self.e.broker._account["trade_mode"]=2
        with self.assertRaises(ValueError):self.e._action(self.settings())
        self.assertEqual(self.e.broker.sent,[])
    def test_certificates_expire_and_bind_version_costs_and_strategy(self):
        symbol="GOLD#";tf="H1";sid="engulfing";config=self.e._quant_config(symbol);now=self.e.clock()
        result={"strategy_id":sid,"version":"1.0.0","plan_version":PLAN_VERSION,"data_kind":"synthetic","symbol":symbol,"timeframe":tf,
            "cost_config_hash":self.e._cost_hash(config),"checked_at":now,"certificate_expires_at":now+3600,"data_time":now-10}
        self.assertTrue(self.e._certificate_valid(result,symbol,tf,sid,config))
        for key,value in (("plan_version","closed-bar-full-v2"),("strategy_id","dow_structure"),("version","old"),("certificate_expires_at",now-1),("data_time",now+10),("cost_config_hash","changed")):
            wrong={**result,key:value};self.assertFalse(self.e._certificate_valid(wrong,symbol,tf,sid,config))
    def test_reconnect_closes_global_mt5_before_new_initialize(self):
        old=self.e.broker;trace=[]
        old.close=lambda:trace.append("shutdown")
        def create(*args):trace.append("initialize");return SimBroker()
        with patch("nexus.engine.MT5Broker",side_effect=create):self.e._connect(False)
        self.assertEqual(trace,["shutdown","initialize"])
    def test_stale_mt5_ipc_recovers_read_only_and_revokes_old_authorization(self):
        self.e._action(self.settings())
        class RecoveringBroker(SimBroker):
            is_simulation=False
            def __init__(self,clock):super().__init__(clock);self.reconnects=0
            def reconnect(self):self.reconnects+=1;return self.terminal()
        recovered=RecoveringBroker(self.e.clock);self.e.broker=recovered
        self.assertTrue(self.e._recover_mt5_connection(BrokerError("account_info: IPC send failed")))
        self.assertEqual(recovered.reconnects,1)
        self.assertIs(self.e.executor.broker,recovered)
        self.assertEqual(self.e.executor.status()["mode"],"READ_ONLY")
        self.assertTrue(self.e.executor.status()["entries_paused"])
        self.assertEqual(self.e.status,"READ_ONLY")
        self.assertTrue(self.e.scanner.queue)
    def test_api_after_worker_shutdown_does_not_bypass_coordinator(self):
        self.e.ever_started=True
        with self.assertRaises(ValueError):self.e.action({"action":"scan"})

    def test_research_invalidation_cancels_prior_cost_generation(self):
        from concurrent.futures import Future
        old_event=self.e.research_cancel;future=Future();generation=self.e.generation
        self.e.pending_quant[(generation,"old")]=(future,"cache",{})
        self.e._invalidate_research()
        self.assertTrue(old_event.is_set());self.assertTrue(future.cancelled())
        self.assertEqual(self.e.pending_quant,{})
        self.assertFalse(self.e.research_cancel.is_set())
        self.assertEqual(self.e.generation,generation+1)

    def test_completed_qualified_quant_prioritizes_fresh_symbol_analysis(self):
        from concurrent.futures import Future
        self.e.scanner.step(99);symbol="EURUSD.demo"
        future=Future();future.set_result({"qualified":True,"symbol":symbol,"strategy_id":"engulfing","timeframe":"M5","status":"QUALIFIED_DEMO_RESEARCH"})
        self.e.pending_quant[(self.e.generation,"EURUSD.demo:M5:engulfing")]=(future,"fixture",{})
        self.e.deep_queue=["GOLD#",symbol,"USDJPY.demo"]
        self.e._collect_quant()
        self.assertEqual(self.e.deep_queue,[symbol,"GOLD#","USDJPY.demo"])
        self.assertEqual(self.e.pending_quant,{})
    def test_diagnostics_contains_consistent_journal_without_token(self):
        self.e.error="account_info: IPC send failed";self.e.status="DATA_ERROR";self.e._publish();report=self.e._diagnostics()
        import zipfile
        with zipfile.ZipFile(report["path"]) as bundle:
            state=json.loads(bundle.read("state.json"))
            ai_report=json.loads(bundle.read("ai-report.json"))
            self.assertTrue(str(state["account"]["login"]).startswith("***"))
            self.assertIn("journal.sqlite3",bundle.namelist())
            self.assertIn("ai-report.json",bundle.namelist())
            self.assertNotIn("session_token",state)
            self.assertEqual(ai_report["mode"],state["mode"])
            self.assertEqual(ai_report["status"],state["status"])
            self.assertIn("errors",ai_report)
            self.assertIn("current_blockers",ai_report)
            self.assertNotIn("rows",ai_report["scan"])
            self.assertIn("recent_decisions",ai_report)
            self.assertIn("quant_results",ai_report)
            self.assertNotIn("session_token",ai_report)
            self.assertEqual(ai_report["current_blockers"][0]["code"],"current_state_error")
            self.assertIn("IPC send failed",ai_report["current_blockers"][0]["message"])
            self.assertEqual(len(ai_report["active_errors"]),1)

    def test_diagnostics_does_not_label_historical_errors_as_active(self):
        self.e._audit("ANALYSIS_ERROR",{"symbol":"EURUSD.demo","reason":"old failure"})
        self.e.error="";self.e._publish();report=self.e._diagnostics()
        import zipfile
        with zipfile.ZipFile(report["path"]) as bundle:
            ai_report=json.loads(bundle.read("ai-report.json"))
        self.assertEqual(ai_report["active_errors"],[])
        self.assertTrue(any(row["payload"].get("reason")=="old failure" for row in ai_report["error_history"]))
        self.assertEqual(ai_report["errors"],ai_report["error_history"])

    def test_diagnostics_explains_completed_scan_with_no_eligible_symbols(self):
        original_tick=self.e.broker.tick
        def stale_tick(symbol):
            tick=original_tick(symbol);tick["time"]=self.e.clock()-300;return tick
        with patch.object(self.e.broker,"tick",side_effect=stale_tick):
            self.e.scanner.begin();self.e.scanner.step(99)
        self.e._publish();report=self.e._diagnostics()
        import zipfile
        with zipfile.ZipFile(report["path"]) as bundle:
            ai_report=json.loads(bundle.read("ai-report.json"))
        self.assertTrue(ai_report["scan"]["complete"])
        self.assertEqual(ai_report["scan"]["eligible"],0)
        self.assertIn("no_eligible_symbols",{row["code"] for row in ai_report["current_blockers"]})
        self.assertEqual(ai_report["market_exclusion_reason_counts"]["الأسعار مفقودة أو قديمة أو غير سليمة"],6)

    def test_diagnostics_includes_every_card_and_describes_card_completeness(self):
        cards=[{"strategy_id":"fixture-"+str(index),"status":"WAIT"} for index in range(501)]
        self.e.cards_by_symbol={"EURUSD.demo":cards};self.e._publish();report=self.e._diagnostics()
        import zipfile
        with zipfile.ZipFile(report["path"]) as bundle:
            ai_report=json.loads(bundle.read("ai-report.json"))
        self.assertEqual(ai_report["cards_total"],501)
        self.assertEqual(ai_report["cards_included"],501)
        self.assertFalse(ai_report["cards_truncated"])
        self.assertEqual(len(ai_report["cards"]),501)
        self.assertEqual(ai_report["cards"][-1]["strategy_id"],"fixture-500")

    def test_terminal_ipc_failure_preserves_diagnostic_evidence(self):
        self.e.scanner.step(99)
        self.e.cards_by_symbol={"EURUSD.demo":[{"strategy_id":"fixture","status":"WAIT"}]}
        self.e.quant_results={"fixture":{"strategy_id":"fixture","status":"REJECTED"}}
        self.e._audit("ANALYSIS_ERROR",{"symbol":"EURUSD.demo","reason":"fixture"})
        self.e._publish()
        good=self.e.snapshot()
        with patch.object(self.e.broker,"account",side_effect=BrokerError("account_info IPC failure")):
            self.e._publish()
        state=self.e.snapshot()
        self.assertEqual(state["status"],"DATA_ERROR")
        self.assertTrue(state["data_stale"])
        self.assertIn("IPC failure",state["error"])
        self.assertEqual(state["account"],good["account"])
        self.assertEqual(state["terminal"],good["terminal"])
        self.assertEqual(state["scan"]["checked"],good["scan"]["checked"])
        self.assertEqual(state["cards"][0]["strategy_id"],"fixture")
        self.assertEqual(state["quant_results"][0]["strategy_id"],"fixture")
        self.assertTrue(any(e.get("event")=="ANALYSIS_ERROR" for e in state["events"]))
        report=self.e._diagnostics()
        import zipfile
        with zipfile.ZipFile(report["path"]) as bundle:
            ai_report=json.loads(bundle.read("ai-report.json"))
        self.assertTrue(ai_report["data_stale"])
        self.assertIn("IPC failure",ai_report["error"])
        self.assertTrue(ai_report["errors"])
        self.assertEqual(ai_report["card_status_counts"],{"fixture:WAIT":1})
        self.assertEqual(ai_report["cards"][0]["strategy_id"],"fixture")
        self.assertEqual(len(ai_report["strategy_coverage"]),len(REGISTRY))


class ServerTests(unittest.TestCase):
    def setUp(self):
        class EngineStub:
            def __init__(self):self.calls=[]
            def snapshot(self):return {"mode":"READ_ONLY"}
            def action(self,p):self.calls.append(p);return {"ok":True}
        self.e=EngineStub();self.s=LocalServer(self.e,ROOT/"ui");self.url=self.s.start();self.addCleanup(self.s.stop)
    def request(self,path,headers=None,data=None):
        req=urllib.request.Request(self.url+path,headers=headers or {},data=data)
        return urllib.request.urlopen(req,timeout=5)
    def test_api_requires_token_and_html_delivers_only_same_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request("/api/state")
        self.assertEqual(error.exception.code,401)
        with self.request("/") as response:
            body=response.read().decode();self.assertIn(self.s.token,body)
            self.assertIn("frame-ancestors 'none'",response.headers["Content-Security-Policy"])
        with self.request("/i18n.js") as response:
            self.assertIn("NEXUS_I18N",response.read().decode())
        with self.request("/session-view.js") as response:
            self.assertIn("QuantSessionView",response.read().decode())
            self.assertIn("text/javascript",response.headers["Content-Type"])
        with self.request("/api/state",{"X-Nexus-Token":self.s.token}) as response:self.assertEqual(json.load(response)["mode"],"READ_ONLY")
    def test_cross_origin_host_rebinding_and_html_cross_site_denied(self):
        for headers,path in (({"Origin":"https://evil.example","X-Nexus-Token":self.s.token},"/api/state"),
                             ({"Host":"evil.example"},"/"),({"Sec-Fetch-Site":"cross-site"},"/")):
            with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,headers)
            self.assertEqual(error.exception.code,403)
    def test_action_requires_json_and_rejects_nonfinite(self):
        headers={"X-Nexus-Token":self.s.token,"Content-Type":"application/json"}
        with self.request("/api/action",headers,json.dumps({"action":"scan"}).encode()) as response:self.assertTrue(json.load(response)["ok"])
        self.assertEqual(self.e.calls,[{"action":"scan"}])
        with self.assertRaises(urllib.error.HTTPError):self.request("/api/action",headers,b'{"action":"start","risk":NaN}')
        self.assertEqual(len(self.e.calls),1)
    def test_files_cannot_escape_ui_directory(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request("/../src/nexus/risk.py")
        self.assertEqual(error.exception.code,404)


if __name__=="__main__":unittest.main()

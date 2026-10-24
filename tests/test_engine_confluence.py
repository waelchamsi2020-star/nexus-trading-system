"""Offline coordinator contract tests; only an in-memory Demo fixture sends."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_confluence import fixture

from nexus import confluence, scalping
from nexus.broker import TIMEFRAMES
from nexus.engine import DECISION_TIMEFRAMES, Engine
from nexus.learning import digest
from nexus.risk import MAGIC, comment_for, protocol_certificate_hash
from nexus.store import account_key
from nexus.strategies import analyze_all

ROOT=Path(__file__).resolve().parents[1]
MODULES=("confluence.py","confluence_registry.py","scalping.py","risk.py","execution.py","engine.py")


class EngineConfluenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=1728000000+54*300
        self.fixture_time=self.now
        self.engine=Engine(ROOT,Path(self.tmp.name)/"data",clock=lambda:self.now)
        self.addCleanup(self.close)
        self.engine._connect(True);self.engine.broker.is_simulation=False
        self.engine.scanner.step(999)
        self.symbol="EURUSD.demo"
        self.engine.broker._prices[self.symbol]=1.07999
        self.reference_root=Path(self.tmp.name)/"reference"
        self.write_reference()
        self.engine.root=self.reference_root
        self.original_bars=self.engine.broker.bars
        self.engine.broker.bars=self.bars
        self.ready_timeframes={"M5"}
        self.changed=False

    def close(self):
        self.engine.stop_worker()
        if self.engine.store:self.engine.store.close()
        self.engine.cache.db.close();self.engine.news.db.close()

    def write_reference(self):
        modules={}
        for name in MODULES:
            blob=(ROOT/"src/nexus"/name).read_bytes()
            destination=self.reference_root/"src/nexus"/name
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(blob)
            modules[name]={"sha256":hashlib.sha256(blob).hexdigest(),"source_python":blob.decode("utf-8")}
        reference={"schema":1,"decision_protocol":"four_school_v1","protocol_definition":confluence.definition(),
            "scalp_definition":{**scalping.POLICY_DEFINITION,"revision":scalping.POLICY_REVISION},"source_modules":modules}
        reference["revision"]=digest(reference)
        path=self.reference_root/"docs/knowledge/execution-reference.json"
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(reference,ensure_ascii=False),encoding="utf-8")

    def bars(self,symbol,tf,count):
        if symbol!=self.symbol or tf not in self.ready_timeframes:return self.original_bars(symbol,tf,count)
        bars=fixture()
        for i,b in enumerate(bars):
            b["time"]=self.fixture_time-(54-i)*TIMEFRAMES[tf]
            for k in ("open","high","low","close"):b[k]=round(1.0696+b[k]*.0001,10)
        if self.changed:bars[-1]["low"]=1.078
        return bars

    def start(self,**overrides):
        payload={"action":"start","risk_value":50,"target_value":100,"unit":"amount","mode":"AUTO_DEMO",
            "commission_per_lot":0,"slippage_points":10,"validation_policy":"forward_demo","decision_protocol":"four_school_v1"}
        self.engine._action({**payload,**overrides})

    def analyze(self):
        self.engine._analyze_symbol(self.symbol)
        return self.engine.decisions[self.symbol]

    def profile(self,variant="normal",target=1.,risk=.01,rr=2):
        return {variant:{"enabled":True,"target_value":target,"risk_percent":risk,"min_reward_risk":rr}}

    def test_real_rule_matrix_reaches_independent_risk_and_single_sender(self):
        self.start();decision=self.analyze()
        self.assertEqual(decision["decision"],"BUY",decision["protocol_reasons"])
        self.assertEqual(set(decision["decision_matrices"]),set(DECISION_TIMEFRAMES))
        self.assertEqual(len(self.engine.cards_by_symbol[self.symbol]),len(DECISION_TIMEFRAMES)*len(self.engine.rule_library))
        proposal=decision["proposals"][0]
        self.assertFalse(proposal["qualified"])
        self.assertEqual(proposal["strategy_id"],"four_school_confluence")
        self.assertEqual(proposal["rule_revision"],self.engine.rule_library["four_school_confluence"]["revision"])
        self.assertEqual(proposal["execution_style"],"BASE")
        self.assertEqual(proposal["decision_matrix"]["certificate_hash"],protocol_certificate_hash(proposal))
        self.assertTrue(proposal["decision_matrix"]["net_rr_preview"]["read_only"])
        self.assertEqual(self.engine.store.intents(),[])
        self.engine._trade_candidates();self.engine._trade_candidates()
        self.assertEqual(len(self.engine.broker.sent),1,self.engine.opportunities)
        self.assertEqual(self.engine.broker.sent[0]["sl"],proposal["sl"])
        self.assertEqual(self.engine.broker.sent[0]["tp"],proposal["tp"])
        self.assertLessEqual(self.engine.store.intents()[0]["reserved"],10.)

    def test_incomplete_data_waits_with_bilingual_reasons_even_old_oos_exists(self):
        self.start();self.ready_timeframes=set()
        self.engine.quant_results[f"{self.symbol}:M5:four_school_confluence"]={"qualified":True,"strategy_id":"four_school_confluence"}
        with patch.object(self.engine.broker,"bars",return_value=[]):decision=self.analyze()
        self.assertEqual(decision["decision"],"WAIT");self.assertEqual(decision["proposals"],[])
        for reasons in decision["protocol_reasons"].values():
            self.assertTrue(reasons)
            self.assertTrue(all(r["ar"] and r["en"] for r in reasons))
        self.engine._trade_candidates();self.assertEqual(self.engine.broker.sent,[])

    def test_old_oos_cannot_activate_composite_historical_policy(self):
        self.engine.quant_results[f"{self.symbol}:M5:four_school_confluence"]={"qualified":True}
        with self.assertRaisesRegex(ValueError,"historical qualification"):
            self.start(validation_policy="historical")
        self.assertEqual(self.engine.executor.mode,"READ_ONLY")

    def test_fresh_closed_bar_change_and_certificate_edit_cannot_send(self):
        self.start();proposal=self.analyze()["proposals"][0]
        self.changed=True
        with self.assertRaisesRegex(ValueError,"no longer ready|changed"):
            self.engine._fresh_proposal(proposal)
        self.changed=False
        corrupted=copy.deepcopy(proposal);corrupted["decision_matrix"]["time"]["status"]="WAIT"
        with self.assertRaisesRegex(ValueError,"certificate"):
            self.engine._fresh_proposal(corrupted)
        self.assertEqual(self.engine.broker.sent,[])

    def test_fresh_price_changes_reseal_without_new_formation_identity(self):
        self.start();proposal=self.analyze()["proposals"][0]
        self.engine.broker._prices[self.symbol]+=0.00002
        fresh=self.engine._fresh_proposal(proposal)
        self.assertEqual(fresh["id"],proposal["id"])
        self.assertEqual(fresh["sl"],proposal["sl"]);self.assertEqual(fresh["tp"],proposal["tp"])
        self.assertNotEqual(fresh["entry"],proposal["entry"])
        self.assertNotEqual(fresh["decision_matrix"]["certificate_hash"],proposal["decision_matrix"]["certificate_hash"])
        self.assertEqual(fresh["decision_matrix"]["certificate_hash"],protocol_certificate_hash(fresh))
        self.assertEqual(self.analyze()["proposals"][0]["id"],proposal["id"])

    def test_opposing_ready_timeframe_vetoes_existing_fresh_proposal(self):
        self.start();proposal=self.analyze()["proposals"][0]
        original=confluence.evaluate
        def evaluate(symbol,tf,*args,**kwargs):
            value=original(symbol,tf,*args,**kwargs)
            if tf=="H1":
                value=original(symbol,"M5",self.bars(symbol,"M5",300),self.now,.00001,quote=self.engine.broker.tick(symbol))
                value["candidate"]["side"]="SHORT"
            return value
        with patch("nexus.engine.confluence.evaluate",side_effect=evaluate):
            with self.assertRaisesRegex(ValueError,"opposing ICT"):
                self.engine._fresh_proposal(proposal)
            self.assertEqual(self.analyze()["proposals"],[])

    def test_exclusive_normal_and_fast_routing_share_daily_budget(self):
        self.ready_timeframes=set(DECISION_TIMEFRAMES)
        self.start(scalping=self.profile("normal",10))
        decision=self.analyze();proposals=decision["proposals"]
        self.assertEqual(len(proposals),5,decision["protocol_reasons"])
        for p in proposals:
            if p["timeframe"] in ("M1","M5"):
                self.assertEqual(p["execution_style"],"SCALP");self.assertEqual(p["execution_plan"]["max_hold_bars"],3)
            else:self.assertEqual(p["execution_style"],"BASE")
        self.assertEqual(len({p["id"] for p in proposals}),5)
        self.start(scalping=self.profile("fast",10))
        for p in self.analyze()["proposals"]:
            if p["timeframe"]=="M1":
                self.assertEqual(p["execution_style"],"SCALP");self.assertIsNone(p["execution_plan"]["max_hold_bars"])
            else:self.assertEqual(p["execution_style"],"BASE")
        self.assertEqual(self.engine.risk.settings["daily_risk"],50)
        self.assertEqual(self.engine.risk.settings["daily_target"],100)

    def test_latched_scalp_goal_survives_off_on_and_cannot_increase(self):
        self.start(scalping=self.profile());proposal=self.analyze()["proposals"][0]
        key=account_key(self.engine.broker.account());sid=proposal["scalp_session_id"]
        self.assertTrue(self.engine.store.reserve("owned-entry",key,1,{"proposal":proposal,"confirmed":True},[],50,now=self.now-20))
        self.engine.store.set_intent_state("owned-entry","CLOSED",order=123,position_ids=[55])
        self.engine.broker._deals.extend([
            {"ticket":1,"order":123,"position_id":55,"time":self.now-20,"type":0,"entry":0,"magic":MAGIC,"comment":comment_for("owned-entry"),"profit":0,"commission":0,"fee":0,"swap":0},
            {"ticket":2,"order":124,"position_id":55,"time":self.now-10,"type":1,"entry":1,"magic":MAGIC,"comment":comment_for("owned-entry"),"profit":2,"commission":0,"fee":0,"swap":0}])
        progress=self.engine._refresh_scalping()["normal"]
        self.assertEqual(progress["progress"]["progress_net"],2)
        self.assertTrue(progress["latched"])
        self.start(scalping={})
        with self.assertRaisesRegex(ValueError,"may only be lowered"):
            self.start(scalping=self.profile(target=2))
        self.start(scalping=self.profile(target=.5))
        self.assertEqual(self.engine.scalping_state["normal"]["session_id"],sid)
        self.assertTrue(self.engine.scalping_state["normal"]["latched"])
        with self.assertRaisesRegex(ValueError,"stopped new entries"):
            self.engine._fresh_proposal(proposal)
        self.assertEqual(self.analyze()["proposals"],[])
        # Same-source verification is now idempotent: it must preserve the
        # original permission and latched session, without renewing either.
        permission=self.engine.executor.authorization
        settings=copy.deepcopy(self.engine.settings)
        session=copy.deepcopy(self.engine.scalping_state["normal"])
        reused=self.engine._connect(True)
        self.assertTrue(reused["connection_reused"])
        self.assertTrue(reused["authorization_preserved"])
        self.assertIs(self.engine.executor.authorization,permission)
        self.assertEqual(self.engine.settings,settings)
        self.assertEqual(self.engine.scalping_state["normal"],session)
        # A genuinely different bridge keeps the original fail-closed reset
        # contract and must still retain the persisted scalp-goal latch.
        self.engine._connect(True,bridge_path="synthetic-different-goal-bridge")
        self.engine.broker.is_simulation=False
        self.assertEqual(self.engine.executor.mode,"READ_ONLY")
        self.assertIsNone(self.engine.executor.authorization)
        self.assertEqual(self.engine.settings,{})
        self.start(scalping=self.profile(target=.5))
        self.assertEqual(self.engine.scalping_state["normal"]["session_id"],sid)
        self.assertTrue(self.engine.scalping_state["normal"]["latched"])
        self.assertFalse(self.engine.scalping_state["normal"]["progress"]["entries_allowed"])

    def test_prior_unlinked_base_fees_do_not_corrupt_current_scalp_progress(self):
        self.start(scalping=self.profile(target=10))
        proposal=self.analyze()["proposals"][0];key=account_key(self.engine.broker.account())
        self.assertTrue(self.engine.store.reserve("owned-entry",key,1,{"proposal":proposal,"confirmed":True},[],50,now=self.now))
        self.engine.store.set_intent_state("owned-entry","REJECTED")
        self.engine.broker._deals.append({"ticket":99,"time":self.now-3600,"type":7,"magic":0,"profit":-6,"commission":0,"fee":0,"swap":0})
        progress=self.engine._refresh_scalping()["normal"]["progress"]
        self.assertTrue(progress["progress_valid"],progress)
        self.assertEqual(progress["progress_net"],0)

    def test_net_cost_preview_blocks_stricter_scalp_rr_without_reserving(self):
        self.start(scalping=self.profile(target=10,rr=2.5))
        decision=self.analyze()
        self.assertEqual(decision["proposals"],[])
        self.assertIn("NET_RR_OR_POLICY_GATE",[r["code"] for r in decision["protocol_reasons"]["M5"]])
        self.assertIn("net reward/risk",decision["protocol_reasons"]["M5"][0]["en"])
        self.assertEqual(self.engine.store.intents(),[])
        rows=[r for r in self.engine.opportunities if r["timeframe"]=="M5"]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["decision"],"WAIT")
        self.assertIn("decision_matrix",rows[0]);self.assertTrue(rows[0]["protocol_reasons"])

    def test_changing_base_to_scalp_cannot_duplicate_the_same_used_formation(self):
        self.start();proposal=self.analyze()["proposals"][0]
        key=account_key(self.engine.broker.account())
        result=self.engine.store.reserve("used-base",key,1,{"proposal":proposal,"confirmed":True},[],50,now=self.now)
        self.assertTrue(result["approved"])
        self.engine.store.set_intent_state("used-base","REJECTED")
        self.start(scalping=self.profile(target=10))
        decision=self.analyze()
        self.assertEqual(decision["proposals"],[])
        self.assertIn("FORMATION_ALREADY_USED",[r["code"] for r in decision["protocol_reasons"]["M5"]])
        self.assertEqual(self.engine.broker.sent,[])

    def test_reference_missing_and_source_tampering_reject_strict_activation(self):
        self.assertTrue(self.engine._load_execution_reference(required=True))
        path=self.reference_root/"src/nexus/engine.py";path.write_bytes(path.read_bytes()+b"\n# fixture edit\n")
        with self.assertRaisesRegex(ValueError,"source mismatch"):
            self.start()
        self.assertEqual(self.engine.executor.mode,"READ_ONLY")
        (self.reference_root/"docs/knowledge/execution-reference.json").unlink()
        with self.assertRaisesRegex(ValueError,"verified execution reference"):
            self.start()
        self.start(decision_protocol="general")
        self.assertEqual(self.engine.executor.mode,"AUTO_DEMO")

    def test_invalid_dual_profile_never_authorizes_and_config_preserves_choice(self):
        with self.assertRaisesRegex(ValueError,"Only one"):
            self.start(scalping={**self.profile("normal"),**self.profile("fast")})
        self.assertEqual(self.engine.executor.mode,"READ_ONLY")
        self.start(scalping=self.profile("normal",10))
        self.engine.broker.is_simulation=True
        permission=self.engine.executor.authorization
        settings=copy.deepcopy(self.engine.settings)
        reused=self.engine._connect(True)
        self.assertTrue(reused["connection_reused"])
        self.assertTrue(reused["authorization_preserved"])
        self.assertIs(self.engine.executor.authorization,permission)
        self.assertEqual(self.engine.settings,settings)
        self.assertEqual(self.engine.executor.mode,"AUTO_DEMO")
        self.engine._connect(True,bridge_path="synthetic-different-profile-bridge")
        self.assertEqual(self.engine.config["decision_protocol"],"four_school_v1")
        self.assertTrue(self.engine.config["scalping"]["normal"]["enabled"])
        self.assertEqual(self.engine.settings,{})
        self.assertEqual(self.engine.executor.mode,"READ_ONLY")
        self.assertIsNone(self.engine.executor.authorization)

    def test_moving_clock_during_context_and_bar_reads_keeps_current_quote_eligible(self):
        self.start()
        context=self.engine._context;bars=self.engine.broker.bars;gate=self.engine.news.gate
        observed_analyses=[];observed_gates=[];observed_evaluations=[]

        def delayed_context(*args):
            self.now+=.25
            value=context(*args)
            self.now+=.25
            return value

        def delayed_bars(*args):
            self.now+=.4
            value=bars(*args)
            self.now+=.4
            return value

        def analyze(symbol,tf,book,as_of,context):
            self.assertGreaterEqual(as_of,self.now)
            observed_analyses.append(as_of)
            return analyze_all(symbol,tf,book,as_of,context)

        def current_gate(info,calendar,simulation,as_of):
            self.assertGreaterEqual(as_of,self.now)
            observed_gates.append(as_of)
            return gate(info,calendar,simulation,as_of)

        evaluate=confluence.evaluate
        def current_evaluation(symbol,tf,book,as_of,tick_size,**kwargs):
            observed_evaluations.append((as_of,copy.deepcopy(kwargs["quote"])))
            return evaluate(symbol,tf,book,as_of,tick_size,**kwargs)

        with patch.object(self.engine,"_context",side_effect=delayed_context), \
                patch.object(self.engine.broker,"bars",side_effect=delayed_bars), \
                patch("nexus.engine.analyze_all",side_effect=analyze), \
                patch.object(self.engine.news,"gate",side_effect=current_gate):
            decision=self.analyze()
            self.assertEqual(decision["decision"],"BUY",decision["protocol_reasons"])
            proposal=decision["proposals"][0]
            self.assertGreater(decision["as_of"],observed_analyses[0])
            self.assertEqual(decision["as_of"],observed_gates[-1])
            with patch("nexus.engine.confluence.evaluate",side_effect=current_evaluation):
                fresh=self.engine._fresh_proposal(proposal)
            self.assertEqual(len(observed_evaluations),len(DECISION_TIMEFRAMES))
            self.assertEqual(len({as_of for as_of,_quote in observed_evaluations}),1)
            self.assertTrue(all(as_of>=quote["time"] for as_of,quote in observed_evaluations))
            self.assertTrue(all(quote==observed_evaluations[0][1] for _as_of,quote in observed_evaluations))
            self.assertEqual(fresh["id"],proposal["id"])
            self.assertEqual((fresh["sl"],fresh["tp"],fresh["entry_zone"]),
                             (proposal["sl"],proposal["tp"],proposal["entry_zone"]))
            self.engine._trade_candidates()
            self.assertEqual(len(self.engine.broker.sent),1,self.engine.opportunities)

    def test_stale_and_future_quotes_still_refused_after_refreshing_decision_clock(self):
        self.start();proposal=self.analyze()["proposals"][0]
        tick=self.engine.broker.tick
        for age in (-1,61):
            with self.subTest(age=age):
                def invalid_quote(symbol,age=age):
                    value=tick(symbol);value["time"]=self.now-age
                    return value
                with patch.object(self.engine.broker,"tick",side_effect=invalid_quote):
                    decision=self.analyze()
                    self.assertEqual(decision["proposals"],[])
                    self.assertIn("QUOTE_INVALID",[r["code"] for r in decision["protocol_reasons"]["M5"]])
                    with self.assertRaisesRegex(ValueError,"market/session gate"):
                        self.engine._fresh_proposal(proposal)
        self.assertEqual(self.engine.broker.sent,[])

    def test_proposal_expiring_during_closed_bar_reads_is_rejected_before_evaluation(self):
        self.start();proposal=self.analyze()["proposals"][0]
        bars=self.engine.broker.bars
        def slow_bars(*args):
            value=bars(*args);self.now+=70
            return value
        with patch.object(self.engine.broker,"bars",side_effect=slow_bars), \
                patch("nexus.engine.confluence.evaluate") as evaluate:
            with self.assertRaisesRegex(ValueError,"انتهت صلاحية الاقتراح أثناء تحديث البيانات"):
                self.engine._fresh_proposal(proposal)
            evaluate.assert_not_called()
        self.assertGreaterEqual(self.now,proposal["expires_at"])
        self.assertEqual(self.engine.broker.sent,[])


    def test_explicit_demo_limit_increase_preserves_existing_financial_records(self):
        self.start()
        key=account_key(self.engine.broker.account())
        self.engine.store.reserve("original-ledger",key,1,{"proposal":{}},[],50,now=self.now)
        self.engine.store.set_intent_state("original-ledger","REJECTED")
        before=self.engine.store.intents(key)
        self.start(risk_value=100,amend_daily_limits=True,allow_daily_risk_increase=True)
        self.assertEqual(self.engine.risk.snapshot(self.now)["risk_amount"],100)
        self.assertEqual(self.engine.store.intents(key),before)
        self.engine.store.halt_day(key,"DAILY_LOSS",self.now)
        with self.assertRaisesRegex(ValueError,"Stopped daily policy"):
            self.start(risk_value=200,amend_daily_limits=True,allow_daily_risk_increase=True)
        self.assertEqual(self.engine.store.get_day(key,self.now)["risk_amount"],100)

    def test_scalp_profit_percentage_caps_volume_without_moving_structural_target(self):
        profiles=self.profile(target=100,risk=1)
        profiles["normal"]["profit_percent"]=.1
        self.start(scalping=profiles)
        proposal=self.analyze()["proposals"][0]
        original_tp=proposal["tp"]
        self.assertEqual(proposal["requested_profit_percent"],.1)
        result=self.engine.risk.prepare(proposal,now=self.now)
        self.assertTrue(result["approved"],result)
        self.assertEqual(result["request"]["tp"],original_tp)
        self.assertGreater(result["planned_net_target"],0)
        self.assertLessEqual(result["planned_net_target"],self.engine.broker.account()["equity"]*.001+1e-8)
        self.assertLessEqual(result["risk"],self.engine.broker.account()["equity"]*.01+1e-8)
        proposal["requested_profit_percent"]=2
        with self.assertRaisesRegex(ValueError,"certificate"):
            self.engine.risk.validate_protocol_certificate(proposal)

    def test_scalp_only_authorization_independently_vetoes_base_entries(self):
        self.start(scalping=self.profile("fast",100,1),scalp_only=True)
        proposal=self.analyze()["proposals"][0]
        self.assertEqual(proposal["execution_style"],"BASE")
        result=self.engine.risk.prepare(proposal,now=self.now)
        self.assertFalse(result["approved"])
        self.assertIn("selected scalp variant only",result["reason"])
        self.assertEqual(self.engine.store.intents(),[])
        self.assertEqual(self.engine.broker.sent,[])

    def test_invalid_profit_percent_cannot_activate_or_replace_authorized_profile(self):
        for value in (0,-1,True,101,float("nan")):
            profile=self.profile(target=100,risk=1)
            profile["normal"]["profit_percent"]=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.start(scalping=profile)
        self.assertEqual(self.engine.broker.sent,[])

if __name__=="__main__":unittest.main()

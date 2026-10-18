"""Bounded single-worker FAST scheduling; synthetic broker only."""
import copy
import queue
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_engine_confluence as fixtures

from nexus import confluence
from nexus.engine import (
    DECISION_TIMEFRAMES,
    FAST_BATCH_LIMIT,
    FAST_SCAN_BATCH_LIMIT,
    _analysis_bar_count,
)


class FastSchedulerTests(unittest.TestCase):
    # Reuse fixture helpers without inheriting its test methods/discovery count.
    close=fixtures.EngineConfluenceTests.close
    write_reference=fixtures.EngineConfluenceTests.write_reference
    bars=fixtures.EngineConfluenceTests.bars
    start=fixtures.EngineConfluenceTests.start
    profile=fixtures.EngineConfluenceTests.profile

    def setUp(self):
        fixtures.EngineConfluenceTests.setUp(self)
        self.engine.running=True
        self.monotonic=[0.]
        self.engine._fast_monotonic=lambda:self.monotonic[0]
        self.ready_timeframes={"M1"}
        self.start(scalping=self.profile("fast",100,risk=1))
        row=self.engine.scanner.rows[self.symbol]
        self.engine.scanner.rows={self.symbol:row}
        self.engine.scanner.queue=[]

    def test_static_wait_prescreen_avoids_heavy_research_even_during_partial_scan(self):
        self.ready_timeframes=set()
        self.engine.scanner.rows["UNVERIFIED"]={"checked":False,"eligible":False}
        self.engine.scanner.queue=[{"name":"UNVERIFIED"}]
        bars=self.engine.broker.bars
        with patch.object(self.engine,"_context",side_effect=AssertionError("Heavy context in FAST prescreen")), \
                patch("nexus.engine.analyze_all",side_effect=AssertionError("42-school work in FAST prescreen")), \
                patch.object(self.engine.scanner,"step") as scan, \
                patch.object(self.engine.broker,"bars",wraps=bars) as history:
            self.assertFalse(self.engine._run_fast_batch())
            self.assertFalse(self.engine._run_fast_batch())
        scan.assert_not_called()
        self.assertTrue(all(call.args[1:]==("M1",_analysis_bar_count("M1")) for call in history.call_args_list))
        self.assertEqual(self.engine._fast_metrics["evaluations"],1)
        self.assertEqual(self.engine._fast_metrics["skipped_unchanged_bar"],1)
        self.assertEqual(self.engine._fast_metrics["verified_eligible"],1)
        self.assertEqual(self.engine._fast_metrics["skipped_unverified"],2)
        self.assertEqual(self.engine.broker.sent,[])

    def test_quote_changes_within_same_closed_bar_can_reach_fast_sender(self):
        self.engine.broker._prices[self.symbol]=1.08049
        self.assertFalse(self.engine._run_fast_batch())
        before=self.engine._fast_bar_cache[self.symbol]
        self.assertIn("QUOTE_OUTSIDE_ZONE",before["evaluation"]["reason_codes"])
        self.assertFalse(before["static_wait"])
        self.engine.broker._prices[self.symbol]=1.07999
        self.assertTrue(self.engine._run_fast_batch())
        self.assertEqual(len(self.engine.broker.sent),1,self.engine.opportunities)
        intent=self.engine.store.intents()[0];proposal=intent["payload"]["proposal"]
        self.assertEqual((proposal["timeframe"],proposal["execution_style"],proposal["scalp_variant"]),("M1","SCALP","fast"))
        self.assertEqual(proposal["requested_risk_percent"],1)
        self.assertEqual(proposal["requested_min_reward_risk"],2)
        self.assertIsNone(proposal["execution_plan"]["max_hold_bars"])
        self.assertTrue(proposal["scalp_session_id"])
        self.assertLessEqual(intent["reserved"],10.)
        self.assertEqual(self.engine.risk.settings["risk_amount"],50)
        self.assertEqual(self.engine.risk.settings["target_amount"],100)
        self.assertEqual(self.engine._fast_metrics["ready_rechecks"],1)

    def test_quote_dependent_no_target_wait_is_not_cached(self):
        original=confluence.evaluate;calls=[]
        def evaluate(*args,**kwargs):
            calls.append(args[1]);value=original(*args,**kwargs)
            if len(calls)==1:
                value.update(status="WAIT",execution_ready=False,candidate=None,reason_codes=["NO_UNSWEPT_TARGET"],
                    reasons=[{"code":"NO_UNSWEPT_TARGET","ar":"لا يوجد هدف","en":"No target"}])
            return value
        with patch("nexus.engine.confluence.evaluate",side_effect=evaluate):
            self.assertFalse(self.engine._run_fast_batch())
            self.assertFalse(self.engine._fast_bar_cache[self.symbol]["static_wait"])
            self.assertTrue(self.engine._run_fast_batch())
        self.assertGreater(len(calls),1)
        self.assertEqual(len(self.engine.broker.sent),1)

    def test_ready_prescreen_rechecks_all_five_timeframes_and_opposition(self):
        original=confluence.evaluate;seen=[]
        def evaluate(symbol,tf,*args,**kwargs):
            seen.append((tf,args[1],copy.deepcopy(kwargs["quote"])))
            value=original(symbol,tf,*args,**kwargs)
            if tf=="H1":
                value=original(symbol,"M1",self.bars(symbol,"M1",300),self.now,.00001,quote=self.engine.broker.tick(symbol))
                value["candidate"]["side"]="SHORT"
            return value
        with patch("nexus.engine.confluence.evaluate",side_effect=evaluate):
            self.assertFalse(self.engine._run_fast_batch())
        shared=seen[-len(DECISION_TIMEFRAMES):]
        self.assertEqual({tf for tf,_as_of,_quote in shared},set(DECISION_TIMEFRAMES))
        self.assertEqual(len({as_of for _tf,as_of,_quote in shared}),1)
        self.assertTrue(all(quote==shared[0][2] for _tf,_as_of,quote in shared))
        reasons=self.engine.decisions[self.symbol]["protocol_reasons"]["M1"]
        self.assertIn("TIMEFRAME_OPPOSITION",[r["code"] for r in reasons])
        self.assertEqual(self.engine.broker.sent,[])

    def test_queued_stop_during_read_yields_before_analysis_or_send(self):
        bars=self.engine.broker.bars
        def enqueue_stop(*args):
            value=bars(*args);self.engine.commands.put(({"action":"stop"},None))
            return value
        with patch.object(self.engine.broker,"bars",side_effect=enqueue_stop), \
                patch("nexus.engine.confluence.evaluate") as evaluate:
            self.assertFalse(self.engine._run_fast_batch())
        evaluate.assert_not_called()
        self.assertEqual(self.engine._fast_metrics["skipped_commands"],1)
        self.assertEqual(self.engine.commands.qsize(),1)
        def dispatch(payload):
            self.engine.running=False
            return {"ok":True}
        with patch.object(self.engine,"_action",side_effect=dispatch) as action:
            self.engine._run_loop()
        action.assert_called_once_with({"action":"stop"})
        self.assertEqual(self.engine.broker.sent,[])

    def test_queued_shutdown_prevents_any_fast_broker_work(self):
        self.engine.commands.put(({"action":"shutdown"},None))
        with patch.object(self.engine.broker,"bars") as bars:
            self.assertFalse(self.engine._run_fast_batch())
        bars.assert_not_called()
        self.assertEqual(self.engine._fast_metrics["skipped_commands"],1)

    def test_cheap_checks_fill_the_time_slice_without_the_old_four_symbol_ceiling(self):
        names=['S'+str(i).zfill(2) for i in range(60)]
        self.engine.scanner.rows={name:{'checked':True,'eligible':True} for name in names}
        visited=[]
        def cheap(symbol):
            visited.append(symbol);self.monotonic[0]+=.02
            return False
        with patch.object(self.engine,'_fast_analyze_symbol',side_effect=cheap),patch.object(self.engine,'_rank'):
            self.engine._run_fast_batch()
        self.assertEqual(visited,names[:FAST_BATCH_LIMIT])
        self.assertGreater(len(visited),4)
        self.assertLessEqual(self.engine._fast_metrics['last_batch_seconds'],1.)

    def test_confirmed_fast_cash_entry_runs_management_before_returning_to_scan(self):
        e=self.engine;e.settings['fast_profit_protection']=True
        p={'id':'cash-post-fill','symbol':self.symbol,'execution_style':'SCALP','scalp_variant':'fast','timeframe':'M1'}
        row={'proposal':p};e.opportunities=[row]
        with patch.object(e,'_scalp_entry_guard'),patch.object(e,'_fresh_proposal',return_value=p), \
             patch.object(e.executor,'execute',return_value={'approved':True,'confirmed':True}), \
             patch.object(e.executor,'manage',return_value={'ok':True,'results':[]}) as manage:
            e._trade_candidates(fast_only=True)
        manage.assert_called_once();self.assertTrue(row['risk_result']['approved'])
        self.assertTrue(row['post_fill_management']['ok']);self.assertTrue(row['attempted'])

    def test_post_fill_management_error_never_relabels_or_replays_confirmed_entry(self):
        e=self.engine;e.settings['fast_profit_protection']=True
        p={'id':'cash-post-fill-error','symbol':self.symbol,'execution_style':'SCALP','scalp_variant':'fast','timeframe':'M1'}
        row={'proposal':p};e.opportunities=[row]
        with patch.object(e,'_scalp_entry_guard'),patch.object(e,'_fresh_proposal',return_value=p), \
             patch.object(e.executor,'execute',return_value={'approved':True,'confirmed':True}) as send, \
             patch.object(e.executor,'manage',side_effect=RuntimeError('Fixture management failure')):
            e._trade_candidates(fast_only=True);e._trade_candidates(fast_only=True)
        send.assert_called_once();self.assertTrue(row['risk_result']['approved']);self.assertTrue(row['attempted'])

    def test_batch_time_budget_is_fair_and_cadence_is_measured(self):
        names=["S"+str(i) for i in range(10)]
        self.engine.scanner.rows={name:{"checked":True,"eligible":True} for name in names}
        visited=[]
        def observe(symbol):
            visited.append(symbol);self.monotonic[0]+=.4
            return False
        with patch.object(self.engine,"_fast_analyze_symbol",side_effect=observe),patch.object(self.engine,"_rank"):
            self.engine._run_fast_batch()
            self.assertEqual(visited,names[:3])
            self.assertLessEqual(len(visited),FAST_BATCH_LIMIT)
            self.assertEqual(self.engine._fast_metrics["skipped_time_budget"],1)
            while not self.engine._fast_metrics["sweep_count"]:self.engine._run_fast_batch()
            self.assertEqual(set(visited),set(names))
            self.assertAlmostEqual(self.engine._fast_metrics["last_sweep_seconds"],4.)
            self.engine._run_fast_batch()
        self.assertGreater(self.engine._fast_metrics["observed_revisit_seconds"],0)
        self.assertGreater(self.engine._fast_metrics["budget_overruns"],0)

    def test_changing_eligibility_preserves_round_progress_and_next_symbol(self):
        self.engine.scanner.rows={name:{"checked":True,"eligible":True} for name in 'ABCDE'}
        visited=[]
        def observe(symbol):
            visited.append(symbol);self.monotonic[0]+=.4
            return False
        with patch.object(self.engine,"_fast_analyze_symbol",side_effect=observe),patch.object(self.engine,"_rank"):
            self.engine._run_fast_batch()
            self.assertEqual(visited,list('ABC'))
            self.engine.scanner.rows['B']['eligible']=False
            self.engine.scanner.rows['F']={"checked":True,"eligible":True}
            self.engine._run_fast_batch()
        self.assertEqual(visited,list('ABCDEF'))
        self.assertEqual(self.engine._fast_metrics['sweep_count'],1)
        self.assertAlmostEqual(self.engine._fast_metrics['last_sweep_seconds'],2.4)

    def test_scan_completion_starts_refresh_interval_and_is_bounded(self):
        self.engine.last_scan=self.now-900
        pending=list(range(2*FAST_SCAN_BATCH_LIMIT+3));steps=[];begins=[]
        def step(limit):
            steps.append(limit);pending.pop(0)
        scanner=SimpleNamespace(rows={self.symbol:{"checked":True,"eligible":True}},queue=pending,
            step=step,begin=lambda:begins.append(True),snapshot=lambda:{"complete":not pending},
            candidates=lambda limit:[{"symbol":self.symbol}])
        self.engine.scanner=scanner
        self.engine._fast_scan_step();self.assertEqual(len(steps),FAST_SCAN_BATCH_LIMIT)
        self.engine._fast_scan_step();self.assertEqual(len(steps),2*FAST_SCAN_BATCH_LIMIT)
        self.engine._fast_scan_step();self.assertEqual(len(steps),2*FAST_SCAN_BATCH_LIMIT+3)
        self.assertEqual(self.engine.last_scan,self.now)
        self.engine._fast_scan_step();self.assertEqual(begins,[])
        self.assertTrue(all(limit==1 for limit in steps))

    def test_background_observation_is_one_timeframe_per_step(self):
        self.engine.deep_queue=[self.symbol]
        self.engine._fast_metrics["sweep_count"]=1;self.monotonic[0]=200
        def cards(symbol,tf,bars,now,context):return [{"id":str(i),"timeframe":tf} for i in range(42)]
        result={"symbol":self.symbol,"decision":"WAIT","proposals":[],"ranked":[],"reasons":[],"as_of":self.now,"expires_at":self.now,
            "decision_protocol":"four_school_v1","decision_matrices":{},"protocol_reasons":{}}
        with patch.object(self.engine,"_context",return_value={}),patch("nexus.engine.analyze_all",side_effect=cards) as analyze, \
                patch.object(self.engine,"_observe_rules") as observe,patch.object(self.engine,"_fast_full_context",return_value=({}, {}, {},self.now,{})), \
                patch.object(self.engine,"_strict_decision",return_value=result):
            self.engine._fast_background_step();self.assertEqual(analyze.call_count,1)
            for _ in range(4):self.engine._fast_background_step()
        self.assertEqual({call.args[1] for call in analyze.call_args_list},set(DECISION_TIMEFRAMES))
        self.assertEqual(observe.call_count,5)
        self.assertEqual(len(self.engine.cards_by_symbol[self.symbol]),42*5)
        self.assertIsNone(self.engine._fast_background_job)

    def test_general_policy_keeps_original_deep_analysis_path(self):
        self.start(decision_protocol="general",scalping={})
        self.engine.deep_queue=[self.symbol];self.engine.last_scan=self.now;self.engine.news.last_attempt=self.now
        with patch.object(self.engine,"_run_fast_batch",side_effect=AssertionError("FAST lane used for general policy")), \
                patch.object(self.engine,"_analyze_symbol") as analyze,patch.object(self.engine,"_collect_quant"), \
                patch.object(self.engine,"_trade_candidates"),patch.object(self.engine,"_update_learning"), \
                patch.object(self.engine.commands,"get",side_effect=queue.Empty), \
                patch.object(self.engine,"_publish",side_effect=lambda:setattr(self.engine,"running",False)):
            self.engine._run_loop()
        analyze.assert_called_once_with(self.symbol)

    def test_worker_without_broker_can_publish_without_fast_flag_error(self):
        self.engine.broker=None;self.engine.news.last_attempt=self.now
        with patch.object(self.engine.commands,"get",side_effect=queue.Empty), \
                patch.object(self.engine,"_publish",side_effect=lambda:setattr(self.engine,"running",False)) as publish, \
                patch("nexus.engine.LOG.exception") as error:
            self.engine._run_loop()
        publish.assert_called_once();error.assert_not_called()


if __name__=="__main__":unittest.main()

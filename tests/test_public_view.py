"""Public JSON isolation and concurrent authority publication, no broker I/O."""
import json
import threading
import unittest
from unittest.mock import patch

from nexus.engine import Engine


class PublicViewTests(unittest.TestCase):
    def engine(self):
        e=Engine.__new__(Engine);e.view_lock=threading.Lock();e._json_view_lock=threading.Lock()
        e._json_view_ref=None;e._json_view_bytes=None
        e._view={'mode':'AUTO_DEMO','execution':{'entries_paused':False},'cards':[{'symbol':'TEST','evidence':[1,2]}]}
        return e

    def test_public_bytes_and_mutable_snapshots_match_without_aliases(self):
        e=self.engine();raw=e.snapshot_json();view=e.snapshot()
        self.assertEqual(json.loads(raw),view)
        view['cards'][0]['evidence'].append(99);view['execution']['entries_paused']=True
        self.assertEqual(json.loads(e.snapshot_json())['cards'][0]['evidence'],[1,2])
        self.assertFalse(e.snapshot()['execution']['entries_paused'])

    def test_unchanged_publication_serializes_once(self):
        e=self.engine()
        with patch.object(e,'_encode_view',wraps=e._encode_view) as encode:
            raw=e.snapshot_json()
            for _ in range(5):self.assertIs(e.snapshot_json(),raw)
            self.assertEqual(encode.call_count,1)

    def test_authority_change_cannot_reuse_old_active_cache(self):
        e=self.engine();e.snapshot_json()
        with e.view_lock:e._view={**e._view,'mode':'READ_ONLY','execution':{'entries_paused':True}}
        current=json.loads(e.snapshot_json())
        self.assertEqual(current['mode'],'READ_ONLY');self.assertTrue(current['execution']['entries_paused'])

    def test_slow_reader_does_not_block_new_publication_or_replace_its_cache(self):
        e=self.engine();entered=threading.Event();resume=threading.Event();result=[]
        original=e._encode_view
        def slow(view):
            entered.set();self.assertTrue(resume.wait(5));return original(view)
        with patch.object(e,'_encode_view',side_effect=slow):
            worker=threading.Thread(target=lambda:result.append(e.snapshot_json()));worker.start()
            self.assertTrue(entered.wait(5))
            self.assertTrue(e.view_lock.acquire(timeout=.2),'JSON encoding must not hold publication lock')
            newer={**e._view,'mode':'READ_ONLY'};new_raw=original(newer)
            e._view=newer;e._json_view_ref=newer;e._json_view_bytes=new_raw;e.view_lock.release()
            resume.set();worker.join(5);self.assertFalse(worker.is_alive())
        self.assertEqual(json.loads(result[0])['mode'],'AUTO_DEMO')
        self.assertIs(e.snapshot_json(),new_raw)
        self.assertEqual(e.snapshot()['mode'],'READ_ONLY')

    def test_nonfinite_data_is_not_silently_serialized(self):
        e=self.engine();e._view={'risk':float('nan')}
        with self.assertRaises(ValueError):e.snapshot_json()

    def test_public_card_inventory_is_bounded_but_counts_remain_complete(self):
        cards=[{"strategy_id":f"model-{i%58}","status":"WAIT","analyzed_at":i,
                "evidence":["x"*1000 for _ in range(5)]} for i in range(1200)]
        cards.append({"strategy_id":"model-hot","status":"READY","actionable":True,"analyzed_at":1})
        display,total,truncated,activity=Engine._public_card_view({"EURUSD":cards},limit=100)
        self.assertEqual(len(display),100)
        self.assertEqual(total,1201)
        self.assertTrue(truncated)
        self.assertEqual(activity["model-0"]["WAIT"],21)
        self.assertEqual(display[0]["strategy_id"],"model-hot")
        self.assertLess(len(json.dumps(display,separators=(",",":"))),600_000)
        self.assertEqual(len(cards),1201)

    def test_public_quantitative_results_drop_large_trade_traces(self):
        source={"strategy_id":"fixture","qualified":False,"metrics":{"trades":3,"expectancy_r":-0.1},
                "trades":[{"evidence":"x"*10000} for _ in range(500)],"reasons":["a","b","c","d","e","f"]}
        compact=Engine._public_quant_view([source])
        self.assertEqual(len(compact),1)
        self.assertEqual(compact[0]["metrics"]["trades"],3)
        self.assertEqual(len(compact[0]["reasons"]),5)
        self.assertNotIn("trades",compact[0])
        self.assertEqual(len(source["trades"]),500)

    def test_public_intents_are_compact_but_preserve_active_rows_and_counts(self):
        rows=[{"id":str(i),"kind":"ENTRY","state":"REJECTED","reserved":0,
               "created":i,"updated":i,"account_key":"private","buckets":{"x":1},
               "payload":{"reason":"blocked","evidence":"x"*5000,
                          "proposal":{"id":"proposal","symbol":"EURUSD","side":"BUY",
                                      "risk_amount":2,"private_trace":"x"*5000}}} for i in range(4)]
        rows.append({"id":"active","kind":"ENTRY","state":"PENDING_APPROVAL","reserved":2,
                     "created":5,"updated":5,"payload":{"proposal":{"symbol":"GBPUSD","side":"SELL"}}})
        compact,total,omitted=Engine._public_intent_view(rows,limit=2)
        self.assertEqual(total,5);self.assertEqual(omitted,2);self.assertEqual(len(compact),3)
        self.assertEqual(compact[0]["id"],"active")
        self.assertNotIn("account_key",compact[0]);self.assertNotIn("buckets",compact[0])
        self.assertNotIn("evidence",compact[1]["payload"])
        self.assertNotIn("private_trace",compact[1]["payload"]["proposal"])
        self.assertLess(len(json.dumps(compact,separators=(",",":"))),2000)

    def test_public_audit_hides_other_account_and_all_account_rows_without_identity(self):
        rows=[{"sequence":1,"event":"GLOBAL","account_key":None,"payload":{"reason":"ok"}},
              {"sequence":2,"event":"OWN","account_key":"acct-a","payload":{"reason":"ok"}},
              {"sequence":3,"event":"OTHER","account_key":"acct-b","payload":{"reason":"secret"}}]
        self.assertEqual(Engine._public_audit_view(rows,None),[])
        own=Engine._public_audit_view(rows,"acct-a")
        self.assertEqual([row["event"] for row in own],["OWN"])
        self.assertNotIn("account_key",own[-1]["payload"])

if __name__=='__main__':unittest.main()

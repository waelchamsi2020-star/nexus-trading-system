"""Command completion uses isolated coordinator fakes and loopback HTTP only.

No broker, terminal, account, order or application data directory is opened.
"""
import concurrent.futures
import copy
import json
import logging
import queue
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nexus.engine import ACTION_RESULT_LIMIT, ACTION_RESULT_TTL, Engine
from nexus.server import LocalServer


class ActionCompletionTests(unittest.TestCase):
    def setUp(self):
        # Exercise production action/worker methods without constructing any
        # broker, SQLite store, news manager or background research worker.
        self.engine=Engine.__new__(Engine)
        self.engine.commands=queue.Queue()
        self.engine.running=True;self.engine.ever_started=True;self.engine.thread=None
        self.engine._action_result_lock=threading.Lock();self.engine._action_results={}
        self.now=[100.];self.engine._action_result_clock=lambda:self.now[0]
        self.engine.clock=lambda:0.
        self.engine.broker=None;self.engine.executor=None
        self.engine.news=SimpleNamespace(last_attempt=0.,refresh=Mock())
        self.engine.research_cancel=threading.Event();self.engine.analysis_pool=Mock()
        self.engine._publish=Mock();self.engine._audit=Mock();self.engine.error=""
        self.release=threading.Event()
        self.addCleanup(self.close)

    def close(self):
        self.release.set()
        with self.engine._action_result_lock:self.engine.running=False
        self.engine._reject_pending_actions()
        if self.engine.thread:self.engine.thread.join(timeout=3)

    def start(self,handler):
        self.engine._action=Mock(side_effect=handler)
        self.engine.thread=threading.Thread(target=self.engine._loop,daemon=True)
        self.engine.thread.start()

    def queued(self,payload=None):
        reply=self.engine.action(payload or {"action":"knowledge_export"},timeout=0)
        self.assertTrue(reply['ok']);self.assertTrue(reply['queued'])
        self.assertEqual(reply['status'],'PENDING')
        self.assertRegex(reply['request_id'],r'^[0-9a-f]{32}$')
        return reply['request_id']

    def await_completion(self,request_id):
        future=self.engine._action_results[request_id]['future']
        try:future.result(timeout=2)
        except Exception:
            logging.getLogger(__name__).exception("Handled boundary failure")
            self.assertTrue(future.done())
        return self.engine.action_result(request_id)

    def test_queued_result_preserves_exact_response_once_and_copies_inputs_and_outputs(self):
        payload={'action':'knowledge_export','nested':{'value':'original'}}
        request_id=self.queued(payload)
        payload['nested']['value']='changed'
        self.assertEqual(self.engine.action_result(request_id),{'ok':True,'status':'PENDING','result':None})
        calls=[];final={'ok':True,'path':'C:/fake/export.zip','details':{'count':41}}
        def execute(command):
            calls.append(command);self.release.wait(timeout=2);return final
        self.start(execute)
        self.release.set()
        complete=self.await_completion(request_id)
        self.assertEqual(complete,{'ok':True,'status':'COMPLETE','result':final})
        complete['result']['details']['count']=0
        final['details']['count']=99
        again=self.engine.action_result(request_id)
        self.assertEqual(again['result']['details']['count'],41)
        self.assertEqual(calls,[{'action':'knowledge_export','nested':{'value':'original'}}])
        self.engine._action.assert_called_once()

    def test_completed_rejection_remains_a_final_response_not_transport_success(self):
        request_id=self.queued({'action':'approve','intent_id':'fake'})
        final={'ok':False,'result':{'approved':False},'message':'risk guard rejected'}
        self.start(lambda _payload:final)
        self.assertEqual(self.await_completion(request_id)['result'],final)
        self.engine._action.assert_called_once()

    def test_async_exception_is_final_even_when_rejection_audit_fails(self):
        request_id=self.queued()
        def audit_failure(*_args):
            self.engine.running=False
            raise OSError('fake audit unavailable')
        self.engine._audit.side_effect=audit_failure
        with patch('nexus.engine.LOG.exception'),patch('nexus.engine.time.sleep'):
            self.start(lambda _payload:(_ for _ in ()).throw(ValueError('fake command failed')))
            complete=self.await_completion(request_id)
            self.engine.thread.join(timeout=2)
        self.assertEqual(complete,{'ok':True,'status':'COMPLETE',
            'result':{'ok':False,'error':'fake command failed','message':'fake command failed'}})
        self.engine._action.assert_called_once()

    def test_immediate_results_and_errors_preserve_existing_behavior(self):
        final={'ok':True,'path':'C:/fake/export.zip'}
        self.start(lambda _payload:copy.deepcopy(final))
        self.assertEqual(self.engine.action({'action':'knowledge_export'},timeout=2),final)
        self.assertEqual(self.engine._action_results,{})
        self.engine._action.side_effect=ValueError('fake immediate error')
        with self.assertRaisesRegex(ValueError,'fake immediate error'):
            self.engine.action({'action':'knowledge_export'},timeout=2)
        self.assertEqual(self.engine._action_results,{})
        self.engine._action.side_effect=concurrent.futures.TimeoutError('command timed out')
        with self.assertRaisesRegex(concurrent.futures.TimeoutError,'command timed out'):
            self.engine.action({'action':'knowledge_export'},timeout=2)
        self.assertEqual(self.engine._action_results,{})

    def test_invalid_unknown_ids_never_allocate_or_execute(self):
        self.engine._action=Mock()
        for request_id in (None,True,123,'','a'*31,'A'*32,'g'*32,'0'*32,'../api/action'):
            with self.subTest(request_id=request_id):
                result=self.engine.action_result(request_id)
                self.assertFalse(result['ok']);self.assertIn('error',result)
        self.assertEqual(self.engine._action_results,{})
        self.assertEqual(self.engine.commands.qsize(),0)
        self.engine._action.assert_not_called()

    def test_interrupted_waiter_cannot_discard_unfinished_command(self):
        request_id=self.queued()
        self.engine._forget_action_result(request_id)
        self.assertEqual(self.engine.action_result(request_id)['status'],'PENDING')
        self.assertEqual(self.engine.commands.qsize(),1)

    def test_ttl_starts_at_completion_pending_never_expires_and_reads_do_not_extend_it(self):
        request_id=self.queued()
        self.now[0]+=ACTION_RESULT_TTL*10
        self.assertEqual(self.engine.action_result(request_id)['status'],'PENDING')
        self.start(lambda _payload:{'ok':True})
        self.assertEqual(self.await_completion(request_id)['status'],'COMPLETE')
        self.now[0]+=ACTION_RESULT_TTL-1
        self.assertEqual(self.engine.action_result(request_id)['status'],'COMPLETE')
        self.now[0]+=1
        self.assertFalse(self.engine.action_result(request_id)['ok'])
        self.assertNotIn(request_id,self.engine._action_results)
        self.engine._action.assert_called_once()

    def test_capacity_rejects_before_submission_and_prunes_only_expired_completions(self):
        with patch('nexus.engine.ACTION_RESULT_LIMIT',2):
            completed=self.queued();pending=self.queued()
            _payload,future=self.engine.commands.get_nowait()
            self.engine._settle_action(future,result={'ok':True,'path':'fake'})
            with self.assertRaisesRegex(ValueError,'لم يُرسل'):
                self.engine.action({'action':'knowledge_export'},timeout=0)
            self.assertEqual(self.engine.commands.qsize(),1)
            self.assertEqual(len(self.engine._action_results),2)
            self.now[0]+=ACTION_RESULT_TTL
            self.assertFalse(self.engine.action_result(completed)['ok'])
            self.assertEqual(self.engine.action_result(pending)['status'],'PENDING')
            another=self.queued()
            self.assertNotEqual(another,pending)
            self.assertEqual(self.engine.commands.qsize(),2)
            self.assertEqual(len(self.engine._action_results),2)

    def test_concurrent_admission_never_exceeds_capacity(self):
        def submit(_index):
            try:return self.engine.action({'action':'knowledge_export'},timeout=0)
            except ValueError:return None
        with (patch('nexus.engine.ACTION_RESULT_LIMIT',4), concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool):
            responses=list(pool.map(submit,range(32)))
        self.assertEqual(sum(response is not None for response in responses),4)
        self.assertEqual(self.engine.commands.qsize(),4)
        self.assertEqual(len(self.engine._action_results),4)
        self.assertEqual(len({r['request_id'] for r in responses if r}),4)
        self.assertGreater(ACTION_RESULT_LIMIT,0)

    def test_stop_completes_unstarted_requests_without_replaying_them(self):
        request_id=self.queued();self.engine._action=Mock()
        self.engine.stop_worker()
        result=self.engine.action_result(request_id)
        self.assertEqual(result['status'],'COMPLETE');self.assertFalse(result['result']['ok'])
        self.assertIn('لم يُنفذ',result['result']['error'])
        self.engine._action.assert_not_called()
        with self.assertRaises(ValueError):self.engine.action({'action':'knowledge_export'})
        self.assertEqual(self.engine.commands.qsize(),0)

    def test_shutdown_command_preserves_revocation_and_rejects_remaining_queue(self):
        shutdown=self.queued({'action':'shutdown'});remaining=self.queued()
        self.engine.executor=Mock();self.engine.broker=Mock()
        self.engine._trade_candidates=Mock();self.engine._collect_quant=Mock();self.engine._update_learning=Mock()
        self.start(lambda payload:Engine._action(self.engine,payload))
        result=self.await_completion(shutdown)
        self.engine.thread.join(timeout=2)
        self.assertEqual(result['result'],{'ok':True})
        self.assertFalse(self.engine.action_result(remaining)['result']['ok'])
        self.engine.executor.deactivate.assert_called_once()
        self.engine.executor.activate.assert_not_called()
        self.engine._action.assert_called_once_with({'action':'shutdown'})
        self.engine.broker.terminal.assert_not_called()
        self.engine.executor.reconcile.assert_not_called()
        self.engine.executor.manage.assert_not_called()
        self.engine._trade_candidates.assert_not_called()
        self.engine._collect_quant.assert_not_called()
        self.engine._update_learning.assert_not_called()

    def test_shutdown_winning_between_queue_removal_and_dispatch_prevents_execution(self):
        request_id=self.queued({'action':'start','mode':'AUTO_DEMO'})
        removed=threading.Event();original_get=self.engine.commands.get
        def pause_after_removal(*args,**kwargs):
            item=original_get(*args,**kwargs)
            removed.set();self.release.wait(timeout=2)
            return item
        with patch.object(self.engine.commands,'get',side_effect=pause_after_removal):
            self.start(lambda _payload:{'ok':True})
            self.assertTrue(removed.wait(timeout=2))
            worker=self.engine.thread;self.engine.thread=Mock()
            try:self.engine.stop_worker()
            finally:self.engine.thread=worker
            self.assertEqual(self.engine.action_result(request_id)['status'],'PENDING')
            self.release.set()
            result=self.await_completion(request_id)
            worker.join(timeout=2)
        self.assertFalse(result['result']['ok'])
        self.assertIn('لم يُنفذ',result['result']['error'])
        self.engine._action.assert_not_called()
        self.engine._publish.assert_not_called()

    def test_command_claim_winning_shutdown_keeps_true_result_and_releases_lock_before_handler(self):
        request_id=self.queued()
        claimed=threading.Event();original_claim=self.engine._claim_worker_step
        def pause_after_claim(future=None):
            allowed=original_claim(future)
            if allowed and future is not None:
                claimed.set();self.release.wait(timeout=2)
            return allowed
        def execute(_payload):
            self.assertTrue(self.engine._action_result_lock.acquire(blocking=False))
            self.engine._action_result_lock.release()
            return {'ok':True,'path':'fake claimed command completed'}
        with patch.object(self.engine,'_claim_worker_step',side_effect=pause_after_claim):
            self.start(execute)
            self.assertTrue(claimed.wait(timeout=2))
            self.assertTrue(self.engine._action_results[request_id]['future'].running())
            worker=self.engine.thread;self.engine.thread=Mock()
            try:self.engine.stop_worker()
            finally:self.engine.thread=worker
            self.assertEqual(self.engine.action_result(request_id)['status'],'PENDING')
            self.release.set()
            result=self.await_completion(request_id)
            worker.join(timeout=2)
        self.assertEqual(result['result'],{'ok':True,'path':'fake claimed command completed'})
        self.engine._action.assert_called_once()
        self.engine._publish.assert_not_called()

    def test_stop_does_not_claim_started_io_was_cancelled(self):
        active=self.queued();remaining=self.queued()
        started=threading.Event()
        def execute(_payload):
            started.set();self.release.wait(timeout=2);return {'ok':True,'path':'fake completed export'}
        self.start(execute)
        self.assertTrue(started.wait(timeout=2))
        worker=self.engine.thread
        # Model join timing out while its already-started operation continues.
        self.engine.thread=Mock()
        try:self.engine.stop_worker()
        finally:self.engine.thread=worker
        self.assertEqual(self.engine.action_result(active)['status'],'PENDING')
        self.assertFalse(self.engine.action_result(remaining)['result']['ok'])
        self.release.set()
        self.assertTrue(self.await_completion(active)['result']['ok'])
        self.engine._action.assert_called_once()

    def test_aborted_active_command_reports_uncertain_outcome_and_never_replays(self):
        active=self.queued();remaining=self.queued()
        self.engine._action=Mock(side_effect=SystemExit('fake abrupt worker exit'))
        with self.assertRaises(SystemExit):self.engine._loop()
        result=self.engine.action_result(active)
        self.assertEqual(result['status'],'COMPLETE');self.assertFalse(result['result']['ok'])
        self.assertIn('قبل تأكيد',result['result']['error'])
        self.assertIn('لا تُعد',result['result']['error'])
        self.assertFalse(self.engine.action_result(remaining)['result']['ok'])
        self.engine._action.assert_called_once()

    def test_abnormal_worker_exit_settles_queue_and_never_allows_direct_fallback(self):
        request_id=self.queued()
        self.engine._run_loop=Mock(side_effect=RuntimeError('fake worker exit'))
        with self.assertRaisesRegex(RuntimeError,'fake worker exit'):self.engine._loop()
        self.assertFalse(self.engine.running)
        self.assertFalse(self.engine.action_result(request_id)['result']['ok'])
        with self.assertRaises(ValueError):self.engine.action({'action':'start'})

    def test_unconnected_start_still_runs_the_existing_authority_guard(self):
        request_id=self.queued({'action':'start','mode':'AUTO_DEMO','risk_value':100})
        self.start(lambda payload:Engine._action(self.engine,payload))
        complete=self.await_completion(request_id)
        self.assertFalse(complete['result']['ok'])
        self.assertIn('MT5 Demo',complete['result']['error'])
        self.assertIsNone(self.engine.executor)
        self.engine._action.assert_called_once()


class ActionResultServerTests(unittest.TestCase):
    close=ActionCompletionTests.close
    start=ActionCompletionTests.start
    await_completion=ActionCompletionTests.await_completion

    def setUp(self):
        ActionCompletionTests.setUp(self)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        stub=SimpleNamespace(snapshot=lambda:{'mode':'READ_ONLY'},
            action=lambda payload:self.engine.action(payload,timeout=0),action_result=self.engine.action_result)
        self.server=LocalServer(stub,temporary.name)
        self.url=self.server.start();self.addCleanup(self.server.stop)

    def request(self,path,headers=None,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        request=urllib.request.Request(self.url+path,headers=headers or {},data=data)
        return urllib.request.urlopen(request,timeout=3)

    def test_http_submission_and_result_lookup_keep_original_final_response(self):
        headers={'X-Nexus-Token':self.server.token,'Content-Type':'application/json'}
        with self.request('/api/action',headers,{'action':'knowledge_export'}) as response:
            queued=json.load(response)
        path='/api/action-result?id='+queued['request_id']
        with self.request(path,headers) as response:
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertEqual(json.load(response)['status'],'PENDING')
        self.start(lambda _payload:{'ok':True,'path':'C:/fake/knowledge.zip'})
        self.await_completion(queued['request_id'])
        with self.request(path,headers) as response:
            final=json.load(response)
        self.assertEqual(final['result'],{'ok':True,'path':'C:/fake/knowledge.zip'})
        self.engine._action.assert_called_once()

    def test_result_endpoint_obeys_token_origin_host_and_fetch_guards(self):
        path='/api/action-result?id='+'0'*32
        cases=[({},401),({'X-Nexus-Token':'wrong'},401),
               ({'X-Nexus-Token':self.server.token,'Origin':'https://evil.example'},403),
               ({'X-Nexus-Token':self.server.token,'Host':'evil.example'},403),
               ({'X-Nexus-Token':self.server.token,'Sec-Fetch-Site':'cross-site'},403),
               ({'X-Nexus-Token':self.server.token,'Sec-Fetch-Site':'same-site'},403)]
        for headers,expected in cases:
            with self.subTest(headers=headers):
                with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,headers)
                self.assertEqual(error.exception.code,expected)
        self.assertEqual(self.engine.commands.qsize(),0)

    def test_unknown_invalid_and_duplicate_queries_do_not_submit_commands(self):
        headers={'X-Nexus-Token':self.server.token,'Origin':self.server.origin}
        self.engine._action=Mock()
        for path in ('/api/action-result?id='+'0'*32,'/api/action-result?id=invalid','/api/action-result?id='):
            with self.request(path,headers) as response:self.assertFalse(json.load(response)['ok'])
        for query in ('','?id=one&id=two','?action=start','?id=one&action=start'):
            with self.subTest(query=query):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.request('/api/action-result'+query,headers)
                self.assertEqual(error.exception.code,400)
        self.assertEqual(self.engine._action_results,{})
        self.assertEqual(self.engine.commands.qsize(),0)
        self.engine._action.assert_not_called()


if __name__=='__main__':unittest.main()

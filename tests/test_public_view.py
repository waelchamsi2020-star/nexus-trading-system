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

if __name__=='__main__':unittest.main()

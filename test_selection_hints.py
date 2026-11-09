import threading,time,unittest
from unittest.mock import Mock
from selection_hints import VisibleWordHints


class SelectionHintTests(unittest.TestCase):
    def test_refresh_does_not_block_capture_and_never_reuses_another_app(self):
        entered=threading.Event();release=threading.Event()
        def read(target):entered.set();release.wait(1);return 'common topic'
        hints=VisibleWordHints(read);one={'hwnd':1,'pid':10,'title':'one'}
        before=time.monotonic();self.assertEqual(hints.get(one),'')
        self.assertLess(time.monotonic()-before,.2)
        self.assertTrue(entered.wait(1));release.set()
        for _ in range(100):
            if hints.get(one):break
            time.sleep(.01)
        self.assertEqual(hints.get(one),'common topic')
        self.assertEqual(hints.get({'hwnd':2,'pid':20,'title':'two'}),'')

    def test_power_clear_prevents_pending_read_restoring_old_words(self):
        release=threading.Event()
        hints=VisibleWordHints(lambda target:release.wait(1) and 'old document')
        target={'hwnd':1};hints.get(target);hints.clear();release.set()
        for _ in range(100):
            with hints.lock:pending=bool(hints.pending)
            if not pending:break
            time.sleep(.01)
        self.assertEqual(hints.cached,{})

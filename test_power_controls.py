import unittest
from command_voice import CommandVoice,power_intent


class PowerTests(unittest.TestCase):
    def test_power_on_off_requires_named_explicit_command(self):
        self.assertEqual(power_intent('Gwen turn on'),'power_on')
        self.assertEqual(power_intent('Gwen turn off.'),'power_off')
        for text in ('turn off','type Gwen turn off','open Gwen turn off','Gwen turn off Word'):
            self.assertIsNone(power_intent(text))

    def test_off_blocks_all_actions_until_explicit_reactivation(self):
        session=CommandVoice({'handsfree':True})
        self.assertEqual(session.route({'text':'Gwen turn off','confidence':1})['control'],'power_off')
        self.assertFalse(session.active);self.assertFalse(session.handsfree)
        for text in ('open word','Gwen open word','Gwen listen','yes','type hello','stop'):
            self.assertEqual(session.route({'text':text,'confidence':1})['kind'],'ignore',text)
        self.assertEqual(session.route({'text':'Gwen turn on','confidence':1})['control'],'power_on')
        self.assertTrue(session.active);self.assertTrue(session.handsfree)
        self.assertEqual(session.route({'text':'open word','confidence':1})['kind'],'command')

    def test_power_overrides_busy_and_dictation_but_low_confidence_does_not(self):
        session=CommandVoice({'handsfree':True});session.dictating=True
        self.assertEqual(session.route({'text':'Gwen turn off','confidence':.5})['kind'],'ignore')
        self.assertTrue(session.active)
        self.assertEqual(session.route({'text':'Gwen turn off','confidence':1},{'busy':True})['control'],'power_off')
        self.assertFalse(session.dictating)
        self.assertEqual(session.route({'text':'Gwen turn on','confidence':1},{'busy':True})['control'],'power_on')

    def test_restored_off_state_and_wake_only_vocabulary(self):
        from vosk_speech import vocabulary
        session=CommandVoice({'assistant_active':False,'handsfree':True})
        self.assertFalse(session.active);self.assertFalse(session.handsfree)
        phrases=vocabulary({'assistant_active':False},None)
        self.assertIn('gwen turn on',phrases)
        self.assertNotIn('open word',phrases)

    def test_native_overlays_hide_remain_hidden_and_allow_capture(self):
        import tkinter as tk,ctypes
        from ctypes import wintypes as w
        import windows_api as win
        from status_indicator import StatusIndicator
        from cursor_marker import CursorMarker
        root=tk.Tk();root.withdraw();root.update()
        before=win.foreground();pointer=win.cursor()
        badge=StatusIndicator(root);marker=CursorMarker(root)
        user=ctypes.WinDLL('user32');user.GetWindowDisplayAffinity.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
        try:
            for overlay in (badge,marker):
                affinity=w.DWORD(123)
                self.assertTrue(user.GetWindowDisplayAffinity(overlay.hwnd,ctypes.byref(affinity)))
                self.assertEqual(affinity.value,0)
                overlay.set_visible(False)
            marker.tick();badge.update(('Listening','green'));root.update()
            for overlay in (badge,marker):self.assertFalse(win.user.IsWindowVisible(overlay.hwnd))
            for overlay in (badge,marker):overlay.set_visible(True)
            root.update()
            for overlay in (badge,marker):self.assertTrue(win.user.IsWindowVisible(overlay.hwnd))
            self.assertEqual(win.foreground(),before);self.assertEqual(win.cursor(),pointer)
        finally:badge.close();marker.close();root.destroy()


if __name__=='__main__':unittest.main()

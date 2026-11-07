import unittest
from status_indicator import indicator_state


class IndicatorTests(unittest.TestCase):
    def test_grid_and_cursor_annotations_do_not_activate(self):
        import tkinter as tk
        import windows_api as win
        from grid_overlay import GridOverlay
        from cursor_marker import CursorMarker
        root=tk.Tk();root.withdraw();root.update()
        before=win.foreground();pointer=win.cursor()
        overlay=GridOverlay(root);marker=CursorMarker(root)
        picture={'active':True,'mode':'smart','config':{'line_color':'cyan','label_color':'yellow','label_background':'black','font_size':9},
                 'areas':[{'monitor':1,'bounds':(0,0,800,600),'cells':[{'label':'A','bounds':(10,10,100,40)}]}]}
        try:
            for _ in range(3):
                overlay.draw(picture);root.update()
                self.assertEqual(win.foreground(),before);self.assertEqual(win.cursor(),pointer)
        finally:overlay.close();marker.close();root.destroy()

    def state(self,**changes):
        values=dict(ready=True,busy=False,enabled=True,microphone=True,handsfree=False)
        values.update(changes)
        return indicator_state(**values)[0]

    def test_listening_requires_open_microphone(self):
        self.assertEqual(self.state(),'Say Gwen listen')
        self.assertEqual(self.state(handsfree=True),'Listening')
        self.assertEqual(self.state(armed=True),'Listening')
        self.assertEqual(self.state(handsfree=True,microphone=False),'Mic starting')
        self.assertEqual(self.state(enabled=False,handsfree=True),'Voice off · F9')

    def test_activity_and_failure_states(self):
        self.assertEqual(self.state(busy=True),'Working')
        self.assertEqual(self.state(recognizing=True),'Hearing you')
        self.assertEqual(self.state(error=True),'Mic error · F10')
        self.assertEqual(self.state(review=True),'Needs reply')
        self.assertEqual(self.state(ready=False),'Starting')

    def test_native_badge_visible_passive_and_focus_unchanged(self):
        import tkinter as tk
        import windows_api as win
        from status_indicator import StatusIndicator
        root=tk.Tk();root.withdraw();root.update()
        before=win.foreground();point=win.cursor()
        badge=StatusIndicator(root)
        try:
            for name,color in (('Listening','#4ade80'),('Working','#fbbf24'),('Needs reply','#fbbf24')):
                badge.update((name,color));root.update()
                self.assertTrue(win.user.IsWindowVisible(badge.hwnd))
                self.assertEqual(win.foreground(),before)
                self.assertEqual(win.cursor(),point)
                style=badge.user.GetWindowLongW(badge.hwnd,-20)
                self.assertEqual(style&0x080800a0,0x080800a0)
        finally:badge.close();root.destroy()


if __name__=='__main__':unittest.main()

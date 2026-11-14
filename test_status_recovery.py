import unittest
from unittest.mock import Mock,patch
from status_indicator import StatusIndicator

class StatusRecoveryTests(unittest.TestCase):
    def indicator(self):
        item=StatusIndicator.__new__(StatusIndicator)
        item.anchor=Mock();item.anchor.layout.return_value=(804,12,248,40)
        item.visible=True;item.canvas=Mock();item.dot=1;item.caption=2;item.meter=3;item.meter_back=4
        item.last=('Listening','#4ade80');item.position=(804,12);item.last_raise=10;item.hwnd=123;item.user=Mock()
        def area(action,param,pointer,flags):
            pointer._obj.left=0;pointer._obj.top=0;pointer._obj.right=1000;pointer._obj.bottom=700;return 1
        item.user.SystemParametersInfoW.side_effect=area
        return item
    def test_stationary_badge_reasserts_z_order_without_activation(self):
        item=self.indicator()
        with patch('status_indicator.time.monotonic',return_value=10.6):item.update(item.last)
        item.user.SetWindowPos.assert_called_once()
        args=item.user.SetWindowPos.call_args.args
        self.assertEqual(args[2:6],(804,12,248,40));self.assertTrue(args[6]&0x10)
        self.assertFalse(args[6]&0x40);self.assertTrue(args[6]&0x200)
        with patch('status_indicator.time.monotonic',return_value=10.7):item.update(item.last)
        self.assertEqual(item.user.SetWindowPos.call_count,1)
    def test_hidden_badge_stays_hidden_and_show_resets_recovery(self):
        item=self.indicator();item.set_visible(False);item.update(item.last)
        item.user.SetWindowPos.assert_not_called()
        item.set_visible(True)
        with patch('status_indicator.time.monotonic',return_value=10.1):item.update(item.last)
        item.user.SetWindowPos.assert_called_once()

    def test_hidden_dictionary_reminders_do_not_take_focus_or_hide_badge(self):
        item=self.indicator();item.window=Mock()
        item.update(item.last,help_hidden=True)
        self.assertTrue(item.visible)
        self.assertEqual(item.badge_height,68)
        captions=[call.kwargs.get('text') for call in item.canvas.create_text.call_args_list]
        self.assertEqual(captions,['show dictionary','nava turn off · open grid'])
        item.window.focus_force.assert_not_called();item.user.ShowWindow.assert_not_called()
        item.update(item.last,help_hidden=False)
        self.assertEqual(item.badge_height,40)

if __name__=='__main__':unittest.main()

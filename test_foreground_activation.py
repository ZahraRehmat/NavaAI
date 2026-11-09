import threading,unittest
from unittest.mock import Mock,patch,call
import windows_api as win
from window_commands import open_and_activate,NoRunningWindow


class ActivationTests(unittest.TestCase):
    def test_background_queue_links_are_always_detached(self):
        user=Mock();user.GetWindowThreadProcessId.side_effect=[20,30]
        user.AttachThreadInput.return_value=True
        with patch.object(win,'user',user),patch.object(win,'current_thread_id',return_value=10),patch.object(win,'foreground',side_effect=[1,2]):
            self.assertTrue(win.activate_with_input_queues(2))
        self.assertEqual(user.AttachThreadInput.call_args_list,[call(10,20,True),call(10,30,True),call(10,30,False),call(10,20,False)])
        user.BringWindowToTop.assert_called_once_with(2)

    def test_queues_detached_if_activation_raises(self):
        user=Mock();user.GetWindowThreadProcessId.side_effect=[20,20]
        user.AttachThreadInput.return_value=True;user.SetForegroundWindow.side_effect=OSError('failed')
        with patch.object(win,'user',user),patch.object(win,'current_thread_id',return_value=10),patch.object(win,'foreground',return_value=1):
            with self.assertRaises(OSError):win.activate_with_input_queues(2)
        self.assertEqual(user.AttachThreadInput.call_args_list,[call(10,20,True),call(10,20,False)])

    def test_restore_then_fallback_is_verified(self):
        user=Mock();user.IsIconic.return_value=True
        with patch.object(win,'user',user),patch.object(win,'action_window',return_value=2),patch.object(win,'ensure_input_allowed'),patch.object(win.time,'sleep'),patch.object(win,'foreground',side_effect=[1]*6+[2]),patch.object(win,'activate_with_input_queues',return_value=True) as fallback:
            self.assertEqual(win.focus_handle(2),2)
            user.ShowWindowAsync.assert_called_once_with(2,9);fallback.assert_called_once_with(2)

    def test_failure_never_reports_success(self):
        user=Mock();user.IsIconic.return_value=False
        with patch.object(win,'user',user),patch.object(win,'action_window',return_value=2),patch.object(win,'ensure_input_allowed'),patch.object(win.time,'sleep'),patch.object(win,'foreground',return_value=1),patch.object(win,'activate_with_input_queues',return_value=False):
            with self.assertRaisesRegex(ValueError,'refused to activate'):win.focus_handle(2)

    def test_open_reuses_existing_window_without_launch(self):
        catalog=Mock();target={'hwnd':2,'title':'Word'}
        with patch('window_commands.switch_to',return_value=target):
            self.assertEqual(open_and_activate('word',catalog,None,threading.Event()),(target,False))
        catalog.launch.assert_not_called()

    def test_launch_waits_for_window_and_verifies_activation(self):
        catalog=Mock();catalog.launch.return_value='Word';target={'hwnd':2,'title':'Word'}
        with patch('window_commands.switch_to',side_effect=[NoRunningWindow(),NoRunningWindow(),target]):
            self.assertEqual(open_and_activate('word',catalog,None,threading.Event()),(target,True))
        catalog.launch.assert_called_once_with('word')

    def test_failed_activation_is_not_mistaken_for_missing_app(self):
        catalog=Mock()
        with patch('window_commands.switch_to',side_effect=ValueError('Windows refused to activate')):
            with self.assertRaises(ValueError):open_and_activate('word',catalog,None,threading.Event())
        catalog.launch.assert_not_called()

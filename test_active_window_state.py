import threading,unittest
from unittest.mock import Mock,patch
from window_commands import intent,resize_window
from command_voice import CommandVoice
from smart_grid import AdaptiveGrid
from grid_test_support import FakeMouse
from agent import Agent


class ActiveWindowTests(unittest.TestCase):
    def test_current_app_and_screen_phrases(self):
        for verb in ('minimize','maximize','restore','close'):
            for target in ('this app','this screen','current window','the current app'):
                self.assertEqual(intent(verb+' '+target),{'action':verb+'_window'})
                self.assertEqual(CommandVoice({'handsfree':True}).route({'text':verb+' '+target,'confidence':1})['kind'],'command')
        self.assertEqual(intent('minimise this screen'),{'action':'minimize_window'})
        self.assertEqual(intent('maximise this app'),{'action':'maximize_window'})
        self.assertIsNone(intent('maximize cells E5:F6'))

    def test_both_grids_pass_current_window_actions_to_agent(self):
        grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[])
        try:
            for enable in ('gwen grid','gwen full grid'):
                grid.run(enable)
                for task in ('minimize this app','maximize this screen','close this screen','restore this window','minimize chat g p t','maximize Word'):
                    before=list(grid.mouse.events)
                    self.assertIsNone(grid.run(task));self.assertTrue(grid.active)
                    self.assertEqual(grid.mouse.events,before)
        finally:grid.close()

    def test_state_requests_use_bound_hwnd_without_model_or_clicks(self):
        context=dict(hwnd=42,pid=123,title='Editor',class_name='EditorClass')
        for action,command,iconic,zoomed in (('minimize_window',6,True,False),('maximize_window',3,False,True),('restore_window',9,False,False)):
            with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.action_window',return_value=42),patch('window_commands.win.ensure_input_allowed') as guard,patch('window_commands.win.user.ShowWindowAsync',return_value=True) as show,patch('window_commands.win.user.IsIconic',return_value=iconic),patch('window_commands.win.user.IsZoomed',return_value=zoomed),patch('window_commands.win.title',return_value='Editor'):
                result=resize_window(context,action,threading.Event())
            show.assert_called_once_with(42,command);guard.assert_called_once_with(42)
            self.assertIn('Editor',result)
        agent=Agent(log=lambda _:None)
        with patch('window_commands.resize_window',return_value='Maximized Editor.') as resize,patch('planner.Planner',side_effect=AssertionError('No visual inference')):
            self.assertEqual(agent.run('maximize this screen',interaction=context),'Maximized Editor.')
        self.assertEqual(resize.call_args.args[:2],(context,'maximize_window'))

    def test_desktop_stale_or_blocked_window_never_resizes(self):
        context=dict(hwnd=42,pid=123,title='Desktop',class_name='Progman')
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.user.ShowWindowAsync') as show:
            with self.assertRaisesRegex(ValueError,'Select the app'):resize_window(context,'maximize_window',threading.Event())
        show.assert_not_called()
        context.update(title='Editor',class_name='EditorClass')
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.action_window',return_value=43),patch('window_commands.win.user.ShowWindowAsync') as show:
            with self.assertRaisesRegex(ValueError,'active dialog'):resize_window(context,'minimize_window',threading.Event())
        show.assert_not_called()

    def test_cancelled_resize_sends_nothing(self):
        stop=threading.Event();stop.set()
        context=dict(hwnd=42,pid=123,title='Editor',class_name='EditorClass')
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.action_window',return_value=42),patch('window_commands.win.user.ShowWindowAsync') as show:
            self.assertEqual(resize_window(context,'maximize_window',stop),'Stopped')
        show.assert_not_called()

    def test_named_resize_uses_directory_without_current_target_or_model(self):
        from test_app_identity import directory
        context=dict(hwnd=42,pid=123,title='ChatGPT',app='ChatGPT',process='ChatGPT',class_name='Chrome_WidgetWin_1')
        agent=Agent(log=lambda _:None);agent.catalog=directory()
        self.assertEqual(intent('minimize chat g p t'),{'action':'minimize_named','name':'chat g p t'})
        with patch('window_commands.running_windows',return_value=[context]),patch('window_commands.resize_window',return_value='Minimized ChatGPT.') as resize,patch('planner.Planner',side_effect=AssertionError('No visual fallback')):
            self.assertEqual(agent.run('minimize chat g p t'),'Minimized ChatGPT.')
        self.assertEqual(resize.call_args.args[:2],(context,'minimize_window'))

    def test_startup_restores_focus_only_if_tk_stole_it(self):
        import windows_api as win
        previous=dict(hwnd=1,pid=10,title='Editor',class_name='EditorClass')
        with patch('windows_api.snapshot',return_value={'hwnd':2,'pid':99}),patch('windows_api.target_alive',return_value=True),patch('windows_api.user.SetForegroundWindow') as focus,patch('windows_api.foreground',return_value=1):
            self.assertTrue(win.restore_launch_focus(previous,own_pid=99))
        focus.assert_called_once_with(1)
        with patch('windows_api.snapshot',return_value={'hwnd':3,'pid':88}),patch('windows_api.target_alive',return_value=True),patch('windows_api.user.SetForegroundWindow') as focus:
            self.assertFalse(win.restore_launch_focus(previous,own_pid=99))
        focus.assert_not_called()
        with patch('windows_api.target_alive',return_value=True):
            self.assertEqual(win.choose_target({'hwnd':2,'title':'Gwen Doer - Type commands'},[previous]),previous)


if __name__=='__main__':unittest.main()

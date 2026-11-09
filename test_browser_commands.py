import unittest,threading
from unittest.mock import Mock,patch
from browser_commands import intent,tab_index
from agent import Agent
from test_existing_browser import CHROME

class BrowserCommandTests(unittest.TestCase):
    def test_human_phrases(self):
        examples=[('open a new tab','tab_new'),('new tab','tab_new'),('close the current tab','tab_close'),('close this tab','tab_close'),('switch to youtube tab','tab_switch'),('switch to tab YouTube','tab_switch'),('next tab','tab_switch'),('go to the second tab','tab_switch'),('pause the video','media_pause'),('pause youtube','media_pause'),('pause the video on youtube','media_pause'),('resume the video','media_play'),('play','media_play')]
        for task,action in examples:
            with self.subTest(task=task):self.assertEqual(intent(task,True)['action'],action)
        self.assertIsNone(intent('close this window',True))
        self.assertIsNone(intent('open Word',True))
        self.assertEqual(intent('switch to reference tab',True),{'action':'tab_switch','target':'reference'})
        self.assertEqual(intent('switch to tab YouTube',True),{'action':'tab_switch','target':'YouTube'})
    def test_tab_ordinal_wraparound_and_fuzzy_choices(self):
        rows=[{'name':'Cats - YouTube'},{'name':'Project docs'},{'name':'Dogs - YouTube'}]
        self.assertEqual(tab_index('next',rows,2),0);self.assertEqual(tab_index('previous',rows,0),2)
        self.assertEqual(tab_index('second',rows),1);self.assertEqual(tab_index('last',rows),2)
        self.assertEqual(tab_index('youtube',rows,chooser=lambda *_:1),2)
        with self.assertRaises(ValueError):tab_index('10',rows)
    def test_tab_commands_bypass_windows_apps_files_and_model(self):
        for task in ('open new tab','close current tab','switch to youtube tab','pause youtube'):
            a=Agent(log=lambda _:None)
            with patch('native_browser.command',return_value='OK') as execute,patch('window_commands.intent',side_effect=AssertionError('Must use browser route')),patch('file_control.open_requested_file',side_effect=AssertionError('No file route')),patch('planner.Planner',side_effect=AssertionError('No Qwen')):
                self.assertEqual(a.run(task,interaction=CHROME),'OK')
            execute.assert_called_once()
    def test_native_keyboard_shortcuts_and_changed_tab_guard(self):
        from native_browser import command
        with patch('native_browser.focused'),patch('native_browser.win.foreground',return_value=44),patch('native_browser.win.title',return_value=CHROME['title']),patch('desktop_control.act') as act:
            command(CHROME,{'action':'tab_new'},threading.Event());command(CHROME,{'action':'tab_close'},threading.Event())
        self.assertEqual([c.args[0]['keys'] for c in act.call_args_list],[['ctrl','t'],['ctrl','w']])
        with patch('native_browser.focused'),patch('native_browser.win.title',return_value='Another tab'),patch('desktop_control.act') as act:
            with self.assertRaisesRegex(ValueError,'active tab changed'):command(CHROME,{'action':'tab_close'},threading.Event())
        act.assert_not_called()
    def test_native_pause_uses_button_and_does_not_toggle_if_paused(self):
        from native_browser import command
        probe=Mock();probe.observe.return_value=[dict(id=5,type='Button',name='Pause (k)')]
        with patch('native_browser.focused'),patch('accessibility.NativeControls',return_value=probe):
            result=command(CHROME,{'action':'media_pause'},threading.Event())
        self.assertIn('Pause',result);probe.act.assert_called_once_with({'action':'ui_click','id':5,'expected_name':'Pause (k)'})
        probe.reset_mock();probe.observe.return_value=[dict(id=5,type='Button',name='Play (k)')]
        with patch('native_browser.focused'),patch('accessibility.NativeControls',return_value=probe):self.assertIn('already paused',command(CHROME,{'action':'media_pause'},threading.Event()))
        probe.act.assert_not_called()
    def test_explicit_tab_request_reuses_background_browser(self):
        a=Agent(log=lambda _:None);a.last_browser_window=dict(CHROME)
        with patch('windows_api.target_alive',return_value=True),patch('windows_api.title',return_value=CHROME['title']),patch('native_browser.command',return_value='Switched to tab') as run:
            self.assertEqual(a.run('switch to youtube tab',interaction={'hwnd':9,'title':'Document - Word','class_name':'OpusApp'}),'Switched to tab')
        self.assertEqual(run.call_args.args[0]['hwnd'],CHROME['hwnd'])

if __name__=='__main__':unittest.main()

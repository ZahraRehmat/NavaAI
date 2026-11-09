import threading,unittest
from unittest.mock import Mock,patch
from agent import Agent
from routing import browser_channel,website_intent,web_url
from native_browser import navigate_window

CHROME={'hwnd':44,'pid':321,'title':'New tab - Google Chrome','class_name':'Chrome_WidgetWin_1'}

class ExistingBrowser(unittest.TestCase):
    def test_browser_detection(self):
        self.assertEqual(browser_channel(CHROME),'chrome')
        self.assertEqual(browser_channel({'title':'Word instructions - Microsoft Edge'}),'msedge')
        self.assertIsNone(browser_channel({'title':'Google Chrome notes - Word'}))
    def test_domains_and_files_stay_distinct(self):
        for task in ('open youtube.com','open https://www.youtube.com/','open youtube website','open youtube on chrome'):
            with self.subTest(task=task):self.assertIn('youtube.com',website_intent(task,'chrome')['url'])
        for task in ('open README.md','open red.jpg','open Word.pdf','open FYP folder'):
            self.assertIsNone(website_intent(task,'chrome'))
        self.assertEqual(web_url('http://127.0.0.1:9191/test'),'http://127.0.0.1:9191/test')
        self.assertIsNone(web_url('javascript:alert(1)'))
    def test_user_logged_requests_bypass_model_and_managed_profile(self):
        for task in ('open youtube.com','search youtube.com','search cats','open dailymotion website','search cats on chrome'):
            with self.subTest(task=task):
                a=Agent(log=lambda _:None)
                with patch('native_browser.navigate_window',return_value='Navigation requested') as nav,patch.object(a.browser,'open',side_effect=AssertionError('Must reuse current Chrome')),patch('planner.Planner',side_effect=AssertionError('No Qwen')),patch('file_control.open_requested_file',return_value=None),patch('folder_control.open_requested_folder',return_value=None):
                    self.assertEqual(a.run(task,interaction=CHROME),'Navigation requested')
                self.assertEqual(nav.call_args.args[0],CHROME)
                self.assertIn('https://',nav.call_args.args[1])
    def test_open_url_before_file_matching(self):
        a=Agent(log=lambda _:None)
        with patch('native_browser.navigate_window',return_value='Navigation requested'),patch('file_control.open_requested_file',side_effect=AssertionError('URL must not reach dictionary')):
            a.run('open youtube.com',interaction=CHROME)
    def test_same_title_different_pid_is_not_a_dom_connection(self):
        a=Agent(log=lambda _:None);a.browser=Mock();a.browser.process_id=123;a.browser.context=Mock()
        a.browser.page.title.return_value='New tab'
        self.assertFalse(a._managed_target(CHROME))
    def test_address_bar_sequence_and_changed_focus(self):
        with patch('native_browser.win.target_alive',return_value=True),patch('native_browser.win.focus_handle'),patch('native_browser.win.foreground',return_value=44),patch('desktop_control.act') as act:
            navigate_window(CHROME,'https://www.youtube.com/',threading.Event())
        self.assertEqual([call.args[0]['action'] for call in act.call_args_list],['hotkey','type','press'])
        self.assertEqual(act.call_args_list[0].args[0]['keys'],['ctrl','l'])
        self.assertEqual(act.call_args_list[-1].args[0]['key'],'enter')
        with patch('native_browser.win.target_alive',return_value=True),patch('native_browser.win.focus_handle'),patch('native_browser.win.foreground',side_effect=[44,55]),patch('desktop_control.act') as act:
            with self.assertRaisesRegex(ValueError,'focus changed'):navigate_window(CHROME,'https://www.youtube.com/',threading.Event())
        self.assertEqual(act.call_count,1)
    def test_external_browser_never_claims_load_completed(self):
        with patch('native_browser.win.target_alive',return_value=True),patch('native_browser.win.focus_handle'),patch('native_browser.win.foreground',return_value=44),patch('desktop_control.act'):
            result=navigate_window(CHROME,'https://www.youtube.com/',threading.Event())
        self.assertIn('requested',result)

if __name__=='__main__':unittest.main()

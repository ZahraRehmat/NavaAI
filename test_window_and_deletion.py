import threading,unittest
from unittest.mock import Mock,patch
from office_control import parse_office
from window_commands import intent,match_window,request_close
from test_app_launch_priority import fixture
from agent import Agent

class WindowAndDeletion(unittest.TestCase):
    def test_delete_and_border_language(self):
        cases=[('delete E5','cells_clear','E5',''),('clear selected cells','cells_clear','',''),
          ('delete cells E5:F6 shift up','cells_delete','E5:F6','up'),('delete the table','table_delete','table',''),
          ('delete table 2','table_delete','table 2',''),('remove the table','table_remove','table',''),
          ('change table outline colour to red','table_borders','table','red'),('make table 2 lines blue','table_borders','table 2','blue')]
        for task,action,target,value in cases:
            with self.subTest(task=task):
                op=parse_office(task);self.assertEqual((op['action'],op['target'],op['value']),(action,target,value))
    def test_window_intents_do_not_steal_office_tabs(self):
        self.assertEqual(intent('close this window'),{'action':'close_window'})
        self.assertEqual(intent('switch to whats app'),{'action':'switch_window','name':'whats app'})
        self.assertEqual(intent('bring Word to front'),{'action':'switch_window','name':'Word'})
        self.assertIsNone(intent('switch to sheet Results'))
    def test_running_match_uses_process_aliases(self):
        rows=[dict(hwnd=1,title='Notes.docx - Word',app='Word',process='WINWORD'),dict(hwnd=2,title='Google Chrome',app='chrome',process='chrome')]
        for query,wanted in [('ms word',1),('chorme',2),('Notes.docx',1)]:self.assertEqual(match_window(rows,query,fixture())['hwnd'],wanted)
        with self.assertRaisesRegex(ValueError,'No running window'):match_window(rows,'steam',fixture())
        with self.assertRaises(ValueError):match_window([dict(hwnd=3,title='file - Visual Studio Code',process='Code')],'vs studio',fixture())
    def test_multiple_documents_need_title(self):
        rows=[dict(hwnd=n,title=f'Doc{n} - Word',app='Word') for n in (1,2)]
        with self.assertRaisesRegex(ValueError,'Several running'):match_window(rows,'word',fixture())
        self.assertEqual(match_window(rows,'word',fixture(),{'hwnd':2})['hwnd'],2)
    def test_close_confirmation_is_once_and_target_is_bound(self):
        ctx=dict(hwnd=7,pid=42,title='Scratch',class_name='TkTopLevel');confirm=Mock(return_value=True)
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.win.ensure_input_allowed'),patch('window_commands.win.user.PostMessageW') as post,patch('window_commands.win.user.IsWindow',return_value=False):
            result=request_close(ctx,confirm,threading.Event())
        confirm.assert_called_once();post.assert_called_once_with(7,0x0010,0,0);self.assertIn('Closed',result)
    def test_declining_close_sends_no_input(self):
        ctx=dict(hwnd=7,title='Scratch',class_name='TkTopLevel');confirm=Mock(return_value=False)
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.win.user.PostMessageW') as post:
            self.assertEqual(request_close(ctx,confirm,threading.Event()),'Close cancelled.')
        post.assert_not_called();confirm.assert_called_once()
    def test_changed_window_after_confirmation_is_not_closed(self):
        ctx=dict(hwnd=7,title='Scratch',class_name='TkTopLevel')
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',side_effect=['Scratch','Another document']),patch('window_commands.win.user.PostMessageW') as post:
            with self.assertRaisesRegex(ValueError,'changed'):request_close(ctx,lambda _:True,threading.Event())
        post.assert_not_called()
    def test_switch_routes_before_file_or_model(self):
        a=Agent(log=lambda _:None);ctx=dict(hwnd=9,title='Scratch - Word',class_name='OpusApp')
        with patch('window_commands.switch_to',return_value=ctx) as switch,patch('file_control.open_requested_file',side_effect=AssertionError('No file route')),patch('planner.Planner',side_effect=AssertionError('No Qwen')):
            self.assertIn('Switched',a.run('switch to Word'))
        switch.assert_called_once();self.assertEqual(a.interaction,ctx)

if __name__=='__main__':unittest.main()

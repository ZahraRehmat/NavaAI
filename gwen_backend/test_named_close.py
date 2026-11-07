import threading,unittest
from unittest.mock import Mock,patch
from window_commands import intent,request_close_named,request_force_close,match_window
from test_app_launch_priority import fixture
from command_voice import CommandVoice
from smart_grid import AdaptiveGrid
from test_full_grid import FakeMouse
from agent import Agent


class NamedCloseTests(unittest.TestCase):
    def test_spoken_whats_app_alias_survives_suffix_cleanup(self):
        rows=[dict(hwnd=8,title='WhatsApp',app='WhatsApp.Root',process='WhatsApp.Root')]
        for spoken in ('close whats app','quit whats app','stop whats app','force close whats app','close app whats app'):
            parsed=intent(spoken)
            self.assertEqual(parsed['name'],'whats app',spoken)
            self.assertEqual(match_window(rows,parsed['name'],fixture())['hwnd'],8)
        self.assertEqual(intent('close word app')['name'],'word')

    def test_failed_close_is_recorded_with_reason(self):
        a=Agent(log=lambda _:None)
        with patch.object(a,'record') as record,patch('window_commands.request_close_named',side_effect=ValueError('No running window matches')):
            result=a.run('close nowhere')
        self.assertIn('No running window matches',result)
        self.assertTrue(any(call.args[0].get('window_command') and 'No running window matches' in call.args[0].get('result','') for call in record.call_args_list))
    def test_native_termination_of_disposable_test_process(self):
        import subprocess,sys
        from window_commands import terminate_process
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            self.assertIn('Force-stopped',terminate_process(child.pid))
            self.assertIsNotNone(child.wait(timeout=3))
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=3)

    def test_close_quit_stop_and_force_intents_preserve_grid_and_tabs(self):
        for text,name in (('close Word','Word'),('close notepas','notepas'),('quit chrome','chrome'),('stop excel','excel')):
            self.assertEqual(intent(text),{'action':'close_named','name':name})
        self.assertEqual(intent('force stop chrome'),{'action':'force_close_named','name':'chrome'})
        self.assertEqual(intent('terminate this app'),{'action':'force_close_window'})
        for text in ('stop grid','exit grid','close current tab','stop video'):self.assertIsNone(intent(text))

    def test_voice_accepts_close_verbs_but_bare_stop_remains_emergency(self):
        session=CommandVoice({'handsfree':True})
        for text in ('close word','quit chrome','stop notepad','force close excel','quit'):
            self.assertEqual(session.route({'text':text,'confidence':1})['kind'],'command')
        self.assertEqual(session.route({'text':'stop','confidence':1})['control'],'stop')

    def test_observed_copilot_repetition_and_unrelated_words(self):
        from vosk_speech import vocabulary
        session=CommandVoice({'handsfree':True})
        for heard,wanted in (('copilot close copilot','close copilot'),('close copilot close copilot','close copilot'),('open copilot open copilot','open copilot')):
            result=session.route({'text':heard,'confidence':.9},{'grid_active':True,'labels':['A']})
            self.assertEqual(result['kind'],'command');self.assertEqual(result['text'],wanted)
        for heard in ('news copilot','quick copilot'):
            self.assertEqual(session.route({'text':heard,'confidence':1})['kind'],'review')
        self.assertEqual(session.route({'text':'type close copilot close copilot','confidence':1})['text'],'type close copilot close copilot')
        model=Mock();model.vosk_model_find_word.return_value=1
        phrases=vocabulary({'target_names':['Copilot']},model)
        for command in ('close copilot','quit copilot','force close copilot','gwen close copilot'):self.assertIn(command,phrases)

    def test_both_grids_pass_app_close_through(self):
        g=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[])
        try:
            for enable in ('gwen grid','gwen full grid'):
                g.run(enable)
                for text in ('close word','quit chrome','stop notepas','force close word'):
                    self.assertIsNone(g.run(text));self.assertTrue(g.active)
                self.assertIn('off',g.run('exit grid').lower())
        finally:g.close()

    def test_fuzzy_named_close_uses_running_app_and_normal_close_only(self):
        target=dict(hwnd=42,pid=99,title='Untitled - Notepad',app='Notepad',process='notepad')
        with patch('window_commands.running_windows',return_value=[target]),patch('window_commands.request_close',return_value='Closed') as close,patch('window_commands.terminate_process',side_effect=AssertionError('No force fallback')):
            confirm=Mock();stop=threading.Event()
            self.assertEqual(request_close_named('notepas',fixture(),None,confirm,stop),'Closed')
            close.assert_called_once_with(target,confirm,stop)

    def test_ambiguous_window_has_choice(self):
        rows=[dict(hwnd=i,title=f'Doc{i} - Word',app='Word') for i in (1,2)]
        chooser=Mock(return_value=1)
        self.assertEqual(match_window(rows,'word',fixture(),chooser=chooser)['hwnd'],2)
        chooser.assert_called_once()

    def test_agent_named_close_does_not_load_model(self):
        a=Agent(log=lambda _:None)
        with patch('window_commands.request_close_named',return_value='Closed Notepad') as close,patch('planner.Planner',side_effect=AssertionError('No model')):
            self.assertEqual(a.run('quit notepas'),'Closed Notepad')
        close.assert_called_once()

    def test_force_requires_one_confirmation_and_refuses_changed_target(self):
        ctx=dict(hwnd=7,pid=99999,title='Scratch',class_name='TkTopLevel')
        confirm=Mock(return_value=True)
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.process_name',return_value='notepad'),patch('window_commands.win.ensure_input_allowed'),patch('window_commands.terminate_process',return_value='Stopped') as terminate:
            self.assertEqual(request_force_close(ctx,confirm,threading.Event()),'Stopped')
        confirm.assert_called_once();terminate.assert_called_once_with(99999)
        with patch('window_commands.win.target_alive',side_effect=[True,False]),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.process_name',return_value='notepad'),patch('window_commands.terminate_process') as terminate:
            with self.assertRaisesRegex(ValueError,'changed'):request_force_close(ctx,lambda _:True,threading.Event())
        terminate.assert_not_called()

    def test_declining_force_or_protected_process_never_terminates(self):
        ctx=dict(hwnd=7,pid=99999,title='Scratch',class_name='TkTopLevel')
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.process_name',return_value='notepad'),patch('window_commands.terminate_process') as terminate:
            self.assertIn('cancelled',request_force_close(ctx,lambda _:False,threading.Event()))
        terminate.assert_not_called()
        with patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.title',return_value='Scratch'),patch('window_commands.process_name',return_value='explorer'),patch('window_commands.terminate_process') as terminate:
            with self.assertRaisesRegex(ValueError,'unavailable'):request_force_close(ctx,lambda _:True,threading.Event())
        terminate.assert_not_called()


if __name__=='__main__':unittest.main()

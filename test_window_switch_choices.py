import threading,unittest
from unittest.mock import Mock,patch
from window_commands import match_window,switch_to,switch_taskbar_group
from test_app_identity import directory
from dialog_voice import answer,grammar


class WindowSwitchChoiceTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(hwnd=i,pid=10,title=f'ChatGPT window {i}',process='ChatGPT') for i in (1,2,3)]

    def test_switch_asks_even_if_one_matching_window_is_current(self):
        chooser=Mock(return_value=2)
        chosen=match_window(self.rows,'chat gpt',directory(),current=self.rows[0],chooser=chooser,prefer_current=False)
        self.assertEqual(chosen['hwnd'],3)
        choices=chooser.call_args.args[1]
        self.assertEqual([o['choice_number'] for o in choices],[1,2,3])
        self.assertTrue(choices[1]['label'].startswith('2. '))

    def test_switch_focuses_only_chosen_live_window(self):
        with patch('window_commands.running_windows',return_value=self.rows),patch('window_commands.win.target_alive',return_value=True),patch('window_commands.win.focus_handle',return_value=2) as focus,patch('window_commands.win.snapshot',return_value=self.rows[1]):
            self.assertEqual(switch_to('chat gpt',directory(),chooser=lambda *args:1)['hwnd'],2)
            focus.assert_called_once_with(2,self.rows[1]['title'])

    def test_cancel_stale_and_stop_never_focus(self):
        for alive,choice,stopped in [(True,None,False),(False,0,False),(True,0,True)]:
            stop=threading.Event()
            if stopped:stop.set()
            with patch('window_commands.running_windows',return_value=self.rows),patch('window_commands.win.target_alive',return_value=alive),patch('window_commands.win.focus_handle') as focus:
                with self.assertRaises((ValueError,InterruptedError)):switch_to('chat gpt',directory(),chooser=lambda *args:choice,stop=stop)
                focus.assert_not_called()

    def test_grouped_taskbar_button_uses_same_chooser(self):
        chooser=Mock()
        with patch('window_commands.switch_to',return_value=self.rows[1]) as switch:
            result=switch_taskbar_group({'scope':'taskbar','name':'ChatGPT - 3 running windows'},chooser,threading.Event())
            self.assertIn('window 2',result);self.assertIs(switch.call_args.kwargs['chooser'],chooser)
            switch.reset_mock()
            self.assertIsNone(switch_taskbar_group({'scope':'app','name':'ChatGPT'},chooser,None));switch.assert_not_called()

    def test_numeric_and_speech_friendly_letters_choose_same_windows(self):
        labels=['A','F','H'];numbers=[1,2,3]
        for text,index in [('two',1),('window three',2),('select one',0),('foxtrot',1)]:
            self.assertEqual(answer(text,3,labels=labels,numbers=numbers),index)
        self.assertIsNone(answer('four',3,labels=labels,numbers=numbers))
        phrases=grammar({'dialog_count':3,'dialog_labels':labels,'dialog_numbers':numbers})
        self.assertIn('window two',phrases);self.assertIn('foxtrot',phrases);self.assertNotIn('bravo',phrases)

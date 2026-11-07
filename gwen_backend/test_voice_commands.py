import unittest,uuid
from unittest.mock import Mock,patch
import numpy as np
from direct_commands import parse_direct
from voice_gate import VoiceGate
from speech import Segmenter
from agent import Agent
from app_runtime import SingleInstance

class DirectCommandTests(unittest.TestCase):
    def test_scroll_and_typos(self):
        self.assertEqual(parse_direct('sroll up')['direction'],'up')
        self.assertEqual(parse_direct('scroll down a lot')['steps'],12)
        self.assertEqual(parse_direct('scroll down 2 pages')['steps'],10)
        self.assertEqual(parse_direct('clikc herte'),{'kind':'pointer','action':'click'})
        self.assertIsNone(parse_direct('click on Netflix'))

    def test_keys_and_literal_typing(self):
        self.assertEqual(parse_direct('press control a')['keys'],['ctrl','a'])
        self.assertEqual(parse_direct('press page down')['keys'],['pagedown'])
        self.assertEqual(parse_direct('type "Hello world."')['text'],'Hello world.')

    def test_scroll_bypasses_model(self):
        a=Agent(log=lambda _:None)
        target={'hwnd':42,'title':'Test editor','bounds':(100,100,900,700),'pointer':(300,300)}
        with patch('planner.Planner',side_effect=AssertionError('Must not load')),patch('windows_api.focus_handle'),patch('desktop_control.window_bounds',return_value=(100,100,900,700)),patch('desktop_control.pg.moveTo'),patch('windows_api.scroll_at') as scroll:
            result=a.run('sroll down',interaction=target)
        scroll.assert_called_once_with(42,300,300,-5,horizontal=False); self.assertEqual(result,'Scrolled down.')

    def test_click_here_uses_pointer_snapshot(self):
        a=Agent(log=lambda _:None)
        target={'hwnd':42,'title':'Test editor','bounds':(100,100,900,700),'pointer':(300,400)}
        with patch('windows_api.focus_handle'),patch('windows_api.rect',return_value=(100,100,900,700)),patch('desktop_control.window_bounds',return_value=(100,100,900,700)),patch('desktop_control.act') as click:
            a.run('clikc herte',interaction=target)
        self.assertEqual(click.call_args.args[0],{'action':'click','x':250.0,'y':500.0})

    def test_click_here_refuses_moved_window(self):
        a=Agent(log=lambda _:None)
        target={'hwnd':42,'title':'Test editor','bounds':(100,100,900,700),'pointer':(300,400)}
        with patch('windows_api.focus_handle'),patch('windows_api.rect',return_value=(200,100,1000,700)),patch('desktop_control.window_bounds',return_value=(200,100,1000,700)),patch('desktop_control.act') as click:
            result=a.run('click here',interaction=target)
        self.assertIn('window moved',result); click.assert_not_called()

    def test_fragments_never_reach_model_or_mouse(self):
        a=Agent(log=lambda _:None)
        with patch('planner.Planner',side_effect=AssertionError('Must not load')),patch('desktop_control.act') as click:
            for fragment in ('And','Amen','reset','You know Gwen'):
                self.assertIn('complete',a.run(fragment))
        click.assert_not_called()

class VoiceGateTests(unittest.TestCase):
    def test_wake_command_and_persistent_session(self):
        g=VoiceGate(); self.assertIsNone(g.accept('scroll down'))
        self.assertIsNone(g.accept('When we were there'))
        self.assertEqual(g.accept('Gwen, scroll down')['command'],'scroll down')
        self.assertEqual(g.accept('Gwen listen')['control'],'handsfree')
        self.assertEqual(g.accept('scroll up')['command'],'scroll up')
        self.assertEqual(g.accept('click here')['command'],'click here')
        self.assertEqual(g.accept('Gwen sleep')['control'],'sleep')
        self.assertIsNone(g.accept('click here'))

    def test_hotkey_arming_is_one_command(self):
        g=VoiceGate(); g.arm()
        self.assertEqual(g.accept('open store')['command'],'open store')
        self.assertIsNone(g.accept('open chrome'))

    def test_handsfree_ignores_conversational_fragments(self):
        g=VoiceGate(); g.accept('Gwen listen')
        for text in ('And','Amen','You know Gwen'):
            self.assertIsNone(g.accept(text))
        self.assertEqual(g.accept('reset')['command'],'/reset')

    def test_stop_always_interrupts(self):
        self.assertEqual(VoiceGate().accept('please stop scrolling')['control'],'stop')

    def test_energy_segmenter_emits_speech_then_silence(self):
        s=Segmenter(); out=[]
        for _ in range(8): s.add(np.zeros(480,dtype=np.float32))
        for _ in range(15): s.add(np.ones(480,dtype=np.float32)*.04)
        for _ in range(25):
            value=s.add(np.zeros(480,dtype=np.float32))
            if value is not None: out.append(value)
        self.assertEqual(len(out),1); self.assertGreater(len(out[0]),15*480)

    def test_single_instance_signals_existing_owner(self):
        key=str(uuid.uuid4()); first=SingleInstance(key); second=SingleInstance(key)
        try:
            self.assertTrue(first.owner); self.assertFalse(second.owner); self.assertTrue(first.show_requested())
        finally: second.close(); first.close()

if __name__=='__main__': unittest.main(verbosity=2)

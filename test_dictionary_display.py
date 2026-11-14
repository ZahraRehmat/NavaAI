import unittest
from unittest.mock import Mock
from command_dictionary import intent
from command_help_ui import CommandHelp
from grid_overlay import clipped_occlusions
from command_voice import CommandVoice

class DictionaryDisplayTests(unittest.TestCase):
    def help(self):
        help=CommandHelp.__new__(CommandHelp)
        help.enabled=True;help.alpha=.65;help.side='left';help.window=Mock();help.master=None;help.page=0
        help.save=Mock();help.update=Mock();help.state={};help.last=None
        return help

    def test_precise_voice_aliases_do_not_capture_mouse_or_literal_dictation(self):
        for text in ('make dictionary more transparent','dictionary more transparent','commands more transparent'):
            self.assertEqual(intent(text),{'action':'lighter'})
        for text in ('make dictionary more visible','commands more visible'):
            self.assertEqual(intent(text),{'action':'darker'})
        for side in ('left','right'):
            self.assertEqual(intent('move dictionary '+side),{'action':'move_'+side})
        self.assertIsNone(intent('move left'));self.assertIsNone(intent('type move dictionary right'))
        gate=CommandVoice({'handsfree':True});gate.dictating=True
        self.assertEqual(gate.route({'text':'type make dictionary more visible','confidence':1})['text'],'type make dictionary more visible')

    def test_transparency_and_position_keep_assistant_modes_independent(self):
        help=self.help();help.apply({'action':'lighter'});self.assertAlmostEqual(help.alpha,.55)
        help.apply({'action':'darker'});self.assertAlmostEqual(help.alpha,.65)
        for _ in range(20):help.apply({'action':'lighter'})
        self.assertEqual(help.alpha,.30)
        for _ in range(20):help.apply({'action':'darker'})
        self.assertEqual(help.alpha,.95)
        help.apply({'action':'move_right'});self.assertEqual(help.side,'right')
        help.apply({'action':'move_left'});self.assertEqual(help.side,'left')
        help.window.focus_force.assert_not_called()
        for text in ('hide commands','move dictionary right','make dictionary more transparent'):
            gate=CommandVoice({'handsfree':True});gate.dictating=True
            gate.route({'text':text,'confidence':1})
            self.assertTrue(gate.active);self.assertTrue(gate.handsfree);self.assertTrue(gate.dictating)

    def test_popup_suspends_only_dictionary_and_restores_without_changing_preference(self):
        help=self.help();del help.update
        help.updated=0;help.shown=True;help.hwnd=123;help.user=Mock();help.rect=(10,10,300,500)
        help.update({'active':True,'dialog':True},force=True)
        help.user.ShowWindow.assert_called_once_with(123,0)
        self.assertTrue(help.enabled);self.assertFalse(help.shown);self.assertIsNone(help.last)
        self.assertEqual(help.overlay_bounds(),[])
        help.state={'dialog':False};help.shown=True
        self.assertEqual(help.overlay_bounds(),[(10,10,300,500)])

    def test_grid_occlusions_are_local_to_each_monitor_without_changing_targets(self):
        mask=[(-100,10,100,80),(1800,10,2000,90)]
        self.assertEqual(clipped_occlusions((0,0,1920,1080),mask),[(0,10,100,80),(1800,10,1920,90)])
        self.assertEqual(clipped_occlusions((-1920,0,0,1080),mask),[(1820,10,1920,80)])
        self.assertEqual(clipped_occlusions((0,0,1920,1080),[(2000,0,2200,80)]),[])
        self.assertEqual(mask,[(-100,10,100,80),(1800,10,2000,90)])

if __name__=='__main__':unittest.main()

import unittest
from unittest.mock import Mock, patch

from direct_commands import parse_direct
from grid_input import keyboard_command
from command_voice import CommandVoice


class EditingCommands(unittest.TestCase):
    def test_noop_notepad_expand_uses_one_verified_dropdown_click(self):
        from dropdown_control import expand_wrapper
        for role in ('Button','MenuItem'):
            wrapper=Mock();wrapper.element_info.control_type=role
            pattern=wrapper.iface_expand_collapse;pattern.CurrentExpandCollapseState=0
            wrapper.click_input.side_effect=lambda:setattr(pattern,'CurrentExpandCollapseState',1)
            self.assertEqual(expand_wrapper(wrapper,timeout=0),'Dropdown open.')
            wrapper.click_input.assert_called_once();wrapper.iface_invoke.Invoke.assert_not_called()
            wrapper.click_input.reset_mock();pattern.CurrentExpandCollapseState=0
            wrapper.click_input.side_effect=None
            with self.assertRaisesRegex(ValueError,'one observed click'):expand_wrapper(wrapper,timeout=0)
            wrapper.click_input.assert_called_once()

    def test_shortcuts_and_delete_are_distinct_in_all_modes(self):
        cases = {'ctrl+z':['ctrl','z'], 'control z':['ctrl','z'], 'control plus z':['ctrl','z'], 'erase alphabet':['backspace'],
                 'undo last action':['ctrl','z'], 'redo typing':['ctrl','y'],
                 'erase it':['ctrl','backspace'], 'erase letter':['backspace'],
                 'delete last character':['backspace'], 'press backspace':['backspace'],
                 'move cursor up':['up'], 'move cursor down':['down'],
                 'previous line':['up'], 'move to next line':['down'],
                 'go to end of line':['end'], 'go to start of line':['home']}
        for phrase, keys in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(parse_direct(phrase), {'kind':'keys','keys':keys})
                self.assertTrue(keyboard_command(phrase))
                for mode in ('normal','dictation','selection'):
                    voice=CommandVoice({'handsfree':True})
                    voice.dictating=mode=='dictation'; voice.selecting=mode=='selection'
                    result=voice.route({'text':phrase,'confidence':1}, {'grid_active':True,'labels':['A','FH']})
                    self.assertEqual(result['kind'],'command')
                    self.assertEqual(parse_direct(result['text'])['keys'],keys)

    def test_caret_repeat_does_not_change_mouse_or_literal_typing(self):
        self.assertEqual(parse_direct('move cursor down 3 lines'),{'kind':'keys','keys':['down'],'repeat':3})
        self.assertEqual(parse_direct('move caret left two characters')['repeat'],2)
        self.assertEqual(parse_direct('move down two lines')['repeat'],2)
        self.assertIsNone(parse_direct('move left 3'))
        self.assertIsNone(parse_direct('FH'))
        self.assertEqual(parse_direct('type undo')['kind'],'type')
        with self.assertRaises(ValueError):parse_direct('move cursor down 999 lines')

    def test_dropdown_buttons_expand_without_double_clicking(self):
        from smart_grid import AdaptiveGrid
        from grid_test_support import FakeMouse
        from test_smart_grid import row
        from dropdown_choices import candidates
        for role in ('MenuItem','Button'):
            mouse=FakeMouse();mouse.expand=Mock(return_value='Dropdown open.')
            grid=AdaptiveGrid(mouse,lambda:[(0,0,800,600)],observer=lambda:[row('Lists',type=role,expandable=True)])
            try:
                grid.run('open grid')
                for phrase in ('A','double click A','open dropdown A'):
                    self.assertEqual(grid.run(phrase),'Dropdown open.')
                self.assertEqual(mouse.expand.call_count,3)
                self.assertFalse(any(e[0]=='click' for e in mouse.events))
            finally:grid.close()
        rows=candidates([{'id':1,'name':'Lists','type':'Button','expandable':True}])
        self.assertEqual(rows[0]['label'],'Lists')


if __name__=='__main__':unittest.main()

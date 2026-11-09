import unittest
from unittest.mock import Mock,patch
import windows_api as win
from accessibility import NativeControls,named_control_id,ObservationChanged
from label_matching import choose_label,NoLabelMatch,dialog_action
from agent import Agent

class DialogFocusTests(unittest.TestCase):
    def test_disabled_workbook_resolves_to_owned_dialog(self):
        with patch.object(win.user,'IsWindow',return_value=True),patch.object(win.user,'IsWindowEnabled',side_effect=lambda h:h==20),patch.object(win.user,'GetLastActivePopup',return_value=20),patch.object(win.user,'IsWindowVisible',return_value=True),patch.object(win.user,'GetWindow',return_value=10):
            self.assertEqual(win.action_window(10),20)
    def test_unrelated_popup_is_not_followed(self):
        with patch.object(win.user,'IsWindow',return_value=True),patch.object(win.user,'IsWindowEnabled',return_value=False),patch.object(win.user,'GetLastActivePopup',return_value=20),patch.object(win.user,'IsWindowVisible',return_value=True),patch.object(win.user,'GetWindow',return_value=99):
            self.assertEqual(win.action_window(10),10)
    def test_save_does_not_match_opposite_or_autosave(self):
        rows=[{'id':1,'name':'Save','type':'Button'},{'id':2,'name':"Don't Save",'type':'Button'},{'id':3,'name':'AutoSave','type':'Button'}]
        self.assertEqual(named_control_id(rows,'save'),1)
        self.assertEqual(named_control_id(rows,'dont save'),2)
        self.assertEqual(choose_label(rows,'save')['row']['id'],1)
        with self.assertRaises(NoLabelMatch):choose_label([rows[1]],'save')
        self.assertFalse(dialog_action('Save.xlsx'))
    def test_dialog_action_cannot_match_chat_text(self):
        with self.assertRaises(ValueError):named_control_id([{'id':1,'name':"Don't Save",'type':'Text'}],'dont save')
        prose='Click dont save — Gwen tried to focus the workbook instead of its dialog. I confirmed the workbook is currently disabled.'
        with self.assertRaises(NoLabelMatch):choose_label([{'text':prose}],'dont save',key='text')
    def test_native_invoke_reacquires_bound_window(self):
        probe=NativeControls();probe.hwnd=20;probe.bounds=(100,100,400,300);el=Mock();probe.controls={1:el}
        with patch('windows_api.focus_handle',return_value=20) as focus,patch('windows_api.rect',return_value=probe.bounds):probe.act({'action':'ui_click','id':1})
        focus.assert_called_once_with(20,'observed control window');el.iface_invoke.Invoke.assert_called_once()
    def test_new_popup_requires_fresh_observation(self):
        probe=NativeControls();probe.hwnd=20;probe.bounds=(100,100,400,300);probe.controls={1:Mock()}
        with patch('windows_api.focus_handle',return_value=30):
            with self.assertRaises(ObservationChanged):probe.act({'action':'ui_click','id':1})
        probe.controls[1].iface_invoke.Invoke.assert_not_called()
    def test_chat_mention_cannot_beat_real_dialog_button(self):
        a=Agent(log=lambda _:None);a.interaction={'hwnd':10,'title':'Chat window'}
        chat=Mock();chat.observe.return_value=[{'id':1,'name':"Don't Save",'type':'Text'}]
        dialog=Mock();dialog.observe.return_value=[{'id':7,'name':"Don't Save",'type':'Button'}]
        with patch.object(win.user,'IsWindow',return_value=True),patch('windows_api.action_window',side_effect=lambda h:h),patch('windows_api.blocking_dialogs',return_value=[20]),patch('accessibility.NativeControls',side_effect=[chat,dialog]):
            result=a.click_dialog_button('dont save')
        self.assertEqual(result,"Clicked the Don't Save button.")
        chat.act.assert_not_called();dialog.act.assert_called_once_with({'action':'ui_click','id':7});self.assertIsNone(a.visual)

if __name__=='__main__':unittest.main()

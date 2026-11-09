import unittest
from unittest.mock import Mock,patch
from command_voice import CommandVoice
from direct_commands import parse_direct
from selection_commands import range_command
from text_input import span_offsets,FocusedText


class SelectionModeTests(unittest.TestCase):
    def test_stop_dictation_selection_bare_range_and_copy(self):
        for grid in (False,True):
            session=CommandVoice({'handsfree':True});session.dictating=True
            def say(text):return session.route({'text':text,'confidence':1},{'grid_active':grid})
            self.assertEqual(say('stop dictation')['control'],'dictation_off')
            self.assertEqual(say('selection')['control'],'selection_on')
            self.assertTrue(session.selecting);self.assertFalse(session.dictating)
            for spoken in ('Islamabad to Karachi','from Islamabad to Karachi','select from Islamabad to Karachi'):
                result=say(spoken);self.assertEqual(result['kind'],'command')
                self.assertEqual(parse_direct(result['text']),{'kind':'select_text','start':'Islamabad','end':'Karachi','copy':True,'screen':True})
            self.assertEqual(say('paste the stuff')['text'],'paste the stuff')
            self.assertEqual(say('stop selection')['control'],'selection_off')

    def test_selection_arms_next_phrase_without_continuous_listening(self):
        session=CommandVoice();self.assertEqual(session.route({'text':'Gwen selection','confidence':1})['control'],'selection_on')
        self.assertEqual(session.route({'text':'Islamabad to Karachi','confidence':1})['kind'],'command')
        self.assertEqual(session.route({'text':'stop','confidence':1})['control'],'stop');self.assertFalse(session.selecting)

    def test_mode_exits_for_dictation_power_and_low_confidence_does_not_select(self):
        session=CommandVoice({'handsfree':True});session.selecting=True
        self.assertEqual(session.route({'text':'Islamabad to Karachi','confidence':.4})['kind'],'review')
        self.assertEqual(session.route({'text':'start dictation','confidence':1})['control'],'dictation_on');self.assertFalse(session.selecting)
        session.selecting=True;session.route({'text':'Gwen turn off','confidence':1});self.assertFalse(session.selecting)

    def test_literal_payload_is_not_a_selection_command(self):
        self.assertEqual(parse_direct('type Islamabad to Karachi')['kind'],'type')
        self.assertEqual(parse_direct('selection Islamabad to Karachi')['copy'],True)
        self.assertIsNone(range_command('Islamabad to Karachi'))

    def test_spelling_matches_existing_document_and_duplicate_ranges_stop(self):
        text='Hello, I am travelling from Islamabad by train to Karachi tomorrow.'
        left,right=span_offsets(text,'Islamad','Karachi')
        self.assertEqual(text[left:right],'Islamabad by train to Karachi')
        with self.assertRaises(ValueError):span_offsets('Islamabad to Karachi. Islamabad to Karachi.','Islamabad','Karachi')

    def test_native_copy_uses_only_selected_span_and_no_copy_on_failure(self):
        access=FocusedText.__new__(FocusedText);access.check=Mock();access.pattern=Mock()
        from selection_test_support import TextRange
        access.pattern.DocumentRange=TextRange('Hello Islamabad via Lahore to Karachi, goodbye.')
        storage={}
        with patch('pyperclip.copy',side_effect=lambda text:storage.update(text=text)),patch('pyperclip.paste',side_effect=lambda:storage['text']):
            result=access.select('Islamabad','Karachi',copy=True)
        self.assertEqual(storage['text'],'Islamabad via Lahore to Karachi');self.assertIn('copied',result)
        access.pattern.DocumentRange.selected.side_effect=RuntimeError('provider refused')
        with patch('pyperclip.copy') as copy:
            with self.assertRaises(RuntimeError):access.select('Islamabad','Karachi',copy=True)
            copy.assert_not_called()

    def test_selection_recognition_uses_english_but_stop_remains_fast(self):
        from hybrid_speech import HybridRecognizer
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        recognizer.commands.transcribe_result.return_value={'text':'islam about to curry','confidence':1}
        recognizer.english.transcribe_result.return_value={'text':'Islamabad to Karachi','confidence':.99}
        result=recognizer.transcribe_result([],{'selection':True,'grid_active':True,'labels':['A']})
        self.assertEqual(result['text'],'Islamabad to Karachi')
        recognizer.english.reset_mock();recognizer.commands.transcribe_result.return_value={'text':'stop selection','confidence':1}
        self.assertEqual(recognizer.transcribe_result([],{'selection':True})['text'],'stop selection')
        recognizer.english.transcribe_result.assert_not_called()

    def test_selection_ignores_only_a_trailing_sentence_after_complete_range(self):
        from hybrid_speech import HybridRecognizer
        result={'text':'Islamabad to Karachi. Thank you for watching.','confidence':.4,'words':[
            {'word':word,'probability':prob} for word,prob in [('Islamabad',.9),('to',.95),('Karachi.',.99),('Thank',.1),('you',.1),('for',.1),('watching.',.1)]]}
        HybridRecognizer.selection_sentence(result)
        self.assertEqual(result['text'],'Islamabad to Karachi.');self.assertGreater(result['confidence'],.9)
        unchanged={'text':'Hello. Thank you.','confidence':.4,'words':[]}
        HybridRecognizer.selection_sentence(unchanged);self.assertEqual(unchanged['text'],'Hello. Thank you.')

    def test_visible_document_fallback_selects_then_copies_only_matching_span(self):
        from text_input import select_screen_text
        el=Mock();el.CurrentIsOffscreen=False;el.CurrentIsPassword=False;el.CurrentProcessId=2;el.CurrentControlType=50030;el.GetRuntimeId.return_value=[1,2]
        uia=Mock();uia.ElementFromHandle.return_value=el;uia.ControlViewWalker.GetFirstChildElement.return_value=None
        pattern=el.GetCurrentPattern.return_value.QueryInterface.return_value
        visible=pattern.GetVisibleRanges.return_value;visible.Length=1
        from selection_test_support import TextRange
        region=TextRange('Hello Islamabad by road to Karachi goodbye')
        visible.GetElement.return_value=region
        selected='Islamabad by road to Karachi'
        with patch('text_input.FocusedText',side_effect=ValueError('No focused text')),patch('pywinauto.uia_defines.IUIA') as api,patch('windows_api.foreground',return_value=1),patch('pyperclip.copy') as copy,patch('pyperclip.paste',return_value=selected):
            api.return_value.iuia=uia
            self.assertIn('copied',select_screen_text({'hwnd':1,'pid':2},'Islamabad','Karachi',copy=True))
            region.selected.assert_called_once();copy.assert_called_once_with(selected)


if __name__=='__main__':unittest.main()

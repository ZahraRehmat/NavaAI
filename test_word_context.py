import unittest
from unittest.mock import Mock,patch
from word_context import phrases,contextual_candidate,expected_action
from word_commands import recover_word_packet


def packet(text,probs=None,**extra):
    words=text.split();probs=probs or [1]*len(words)
    return {'text':text,'confidence':sum(probs)/len(probs),
            'words':[{'word':w,'probability':p} for w,p in zip(words,probs)],**extra}


class WordContextTests(unittest.TestCase):
    def test_native_text_focus_waits_for_uia_but_never_switches_apps(self):
        from text_input import FocusedText
        old=Mock();old.CurrentProcessId=9
        editor=Mock();editor.CurrentProcessId=2;editor.CurrentIsPassword=False;editor.GetRuntimeId.return_value=[1,2]
        uia=Mock();uia.GetFocusedElement.side_effect=[old,editor]
        with patch('pywinauto.uia_defines.IUIA') as api,patch('windows_api.foreground',return_value=1),patch('time.sleep') as pause:
            api.return_value.iuia=uia
            access=FocusedText({'hwnd':1,'pid':2})
            self.assertEqual(access.identity,(1,2));pause.assert_called_once()
        uia.GetFocusedElement.side_effect=None;uia.GetFocusedElement.return_value=old
        with patch('pywinauto.uia_defines.IUIA') as api,patch('windows_api.foreground',return_value=99),patch('time.sleep') as pause:
            api.return_value.iuia=uia
            with self.assertRaisesRegex(ValueError,'active app changed'):FocusedText({'hwnd':1,'pid':2})
            pause.assert_not_called()

    def test_editor_vocabulary_is_used_only_for_target_pass(self):
        model=Mock();model.vosk_model_find_word.return_value=1
        context={'word_hints':'work testing shall required'}
        grammar=phrases(context,'move',model)
        self.assertIn('move cursor to testing',grammar)
        self.assertNotIn('move cursor to youtube',grammar)
        self.assertEqual(phrases({},'move',model),[])
        original=packet('select work')
        result=contextual_candidate(original,packet('select work'),context)
        self.assertEqual(result['text'],'select word work')
        self.assertIsNone(expected_action(original,{**context,'grid_active':True}))
        self.assertIsNone(expected_action(packet('select all'),context))
        self.assertIs(contextual_candidate(original,packet('select garden'),context),original)
        self.assertIs(contextual_candidate(original,packet('erase word work'),context),original)

    def test_primary_action_anchor_survives_weak_english_cursor(self):
        primary=packet('move cursor to word',word_target_unclear=True)
        result=recover_word_packet(primary,packet('Move cursor to work.',[1,.45,1,.98]))
        self.assertEqual(result['text'],'Move cursor to work.')
        result=recover_word_packet(primary,packet('Move closer to testing.',[1,.9,1,.98]))
        self.assertEqual(result['text'].casefold(),'move cursor to testing.')
        weak=packet('Move cursor to work.',[1,1,1,.3])
        self.assertIs(recover_word_packet(primary,weak),primary)
        result=recover_word_packet(primary,packet('Move cursor to testing. Thank you.',[1,1,1,.98,.1,.1]),hints='work testing')
        self.assertEqual(result['text'].casefold(),'move cursor to testing.')

    def test_editor_grammar_recovers_logged_testing_target_before_english(self):
        from hybrid_speech import HybridRecognizer
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        recognizer.commands.transcribe_result.return_value=packet('move cursor to test link',word_target_unclear=True)
        recognizer.commands.transcribe_word_targets.return_value=packet('move cursor to testing',backend='vosk-editor-word')
        result=recognizer.transcribe_result([],{'word_hints':'work testing shall required'})
        self.assertEqual(result['text'],'move cursor to testing')
        recognizer.english.transcribe_result.assert_not_called()
        recognizer.commands.transcribe_result.return_value=packet('move cursor to work')
        recognizer.commands.transcribe_word_targets.reset_mock()
        recognizer.commands.transcribe_controls.return_value={}
        result=recognizer.transcribe_result([],{'word_hints':'work testing shall required'})
        self.assertEqual(result['text'],'move cursor to work')
        recognizer.commands.transcribe_word_targets.assert_not_called()

    def test_changed_field_is_rejected_before_any_selection_or_deletion(self):
        from text_input import native_word,SelectionResolutionError
        access=Mock();access.identity=(2,)
        with patch('text_input.FocusedText',return_value=access),patch('text_input.select_screen_text') as select,patch('desktop_control.act') as keys:
            for action in ('select','erase','move'):
                with self.assertRaises(SelectionResolutionError):native_word({'hwnd':1,'text_field_id':[1]},'work',action)
            select.assert_not_called();keys.assert_not_called()


if __name__=='__main__':unittest.main()

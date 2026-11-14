import unittest,time
from unittest.mock import Mock,patch
from command_voice import CommandVoice,stale
from dictation_queue import DictationQueue
from speech import LocalRecognizer

class DictationReliabilityTests(unittest.TestCase):
    def test_prose_has_its_own_threshold_without_relaxing_actions(self):
        session=CommandVoice({'handsfree':True});session.dictating=True
        for text in ('Now add a dictionary.','The blue folder is beside the window.'):
            result=session.route({'text':text,'confidence':.66,'backend':'whisper-base.en'})
            self.assertTrue(result['dictation_input']);self.assertTrue(result['text'].startswith('type '))
        for text,ctx in [('press delete',{}),('pause video',{}),('stop dictation',{}),('select cell A2',{'office':'excel'})]:
            self.assertEqual(session.route({'text':text,'confidence':.66,'backend':'whisper-base.en'},ctx)['kind'],'review')
        self.assertEqual(session.route({'text':'uncertain words','confidence':.40,'backend':'whisper-base.en'})['kind'],'review')
        self.assertEqual(session.route({'text':'uncertain words','confidence':.66,'backend':'vosk'})['kind'],'review')
        session.dictating=False
        self.assertEqual(session.route({'text':'open word','confidence':.66,'backend':'whisper-base.en'})['kind'],'review')

    def test_dictation_badge_distinguishes_decoding_rejection_and_ready(self):
        from status_indicator import dictation_state
        self.assertEqual(dictation_state(recognizing=True,review=True)[0],'Decoding text')
        self.assertEqual(dictation_state(review=True)[0],'Not typed · repeat')
        self.assertEqual(dictation_state()[0],'Dictating · say stop')

    def test_uncertain_dictation_gets_one_accuracy_pass_only(self):
        from hybrid_speech import HybridRecognizer
        r=HybridRecognizer.__new__(HybridRecognizer);r.commands=Mock();r.english=Mock()
        r.commands.transcribe_result.return_value={'text':'ordinary spoken words','confidence':1}
        r.english.transcribe_result.side_effect=[{'text':'weak words','confidence':.4},{'text':'clearer words','confidence':.8}]
        result=r.transcribe_result([],{'dictation':True})
        self.assertEqual(result['text'],'clearer words');self.assertEqual(r.english.transcribe_result.call_count,2)
        self.assertTrue(r.english.transcribe_result.call_args.args[1]['dictation_accuracy_pass'])

    def test_unicode_delivery_keeps_characters_separate_and_stops_on_focus_change(self):
        from unicode_keyboard import type_unicode
        sent=[];api=Mock()
        api.SendInput.side_effect=lambda count,buffer,size:sent.append([event.payload.keyboard.scan for event in buffer]) or count
        with patch('unicode_keyboard.ctypes.WinDLL',return_value=api),patch('windows_api.foreground',return_value=1),patch('unicode_keyboard.time.sleep'):
            type_unicode('Ab\U0001f600',1)
        self.assertEqual(sent,[[65,65],[98,98],[0xd83d,0xd83d,0xde00,0xde00]])
        sent.clear()
        with patch('unicode_keyboard.ctypes.WinDLL',return_value=api),patch('windows_api.foreground',side_effect=[1,2]),patch('unicode_keyboard.time.sleep'):
            with self.assertRaisesRegex(ValueError,'Active app changed'):type_unicode('AB',1)
        self.assertEqual(len(sent),1)

    def test_typing_is_confirmed_from_the_actual_caret_without_repeating(self):
        from text_input import native_type
        access=Mock();access.preceding.return_value=('',False)
        ranges=access.pattern.GetSelection.return_value;ranges.Length=1
        caret=ranges.GetElement.return_value;caret.GetText.return_value=''
        caret.Clone.return_value.GetText.return_value='hello'
        with patch('text_input.FocusedText',return_value=access),patch('unicode_keyboard.type_unicode') as type_input:
            self.assertIn('verified',native_type('hello',{'hwnd':1}))
            type_input.assert_called_once()
        caret.Clone.return_value.GetText.return_value='ooooo'
        with patch('text_input.FocusedText',return_value=access),patch('unicode_keyboard.type_unicode') as type_input,patch('time.monotonic',side_effect=[0,1]):
            with self.assertRaisesRegex(ValueError,'did not confirm'):native_type('hello',{'hwnd':1})
            type_input.assert_called_once()

    def test_dictation_stop_and_start_aliases(self):
        session=CommandVoice({'handsfree':True})
        self.assertEqual(session.route({'text':'dictation start','confidence':1})['control'],'dictation_on')
        self.assertEqual(session.route({'text':'dictation stop','confidence':1})['control'],'dictation_off')

    def test_grid_refresh_does_not_cancel_prose_but_still_cancels_labels(self):
        old={'interaction':{'hwnd':1,'pid':2,'text_field_id':[3]},'grid_active':True,'grid_version':1}
        new={**old,'grid_version':2}
        self.assertFalse(stale(old,new,text_input=True))
        self.assertTrue(stale(old,new,'A'))
        self.assertTrue(stale(old,{**new,'interaction':{'hwnd':8,'pid':2}},text_input=True))
        self.assertTrue(stale(old,{**new,'interaction':{'hwnd':1,'pid':2,'text_field_id':[4]}},text_input=True))
        self.assertFalse(stale(old,{**new,'grid_active':False},text_input=True))

    def test_dictation_queue_keeps_text_bound_to_the_original_field(self):
        q=DictationQueue();old={'interaction':{'hwnd':1,'pid':2,'text_field_id':[3]}}
        q.push('type text',old,1)
        with self.assertRaisesRegex(ValueError,'field changed'):q.pop({'interaction':{'hwnd':1,'pid':2,'text_field_id':[4]}},1)
        self.assertFalse(q.items)

    def test_greedy_dictation_preserves_stricter_general_decoder_configuration(self):
        recognizer=LocalRecognizer.__new__(LocalRecognizer);recognizer.config={'beam_size':3};recognizer.model=Mock()
        recognizer.model.transcribe.return_value=([],None)
        recognizer.transcribe_result([],{'dictation':True})
        self.assertEqual(recognizer.model.transcribe.call_args.kwargs['beam_size'],1)
        self.assertEqual(recognizer.model.transcribe.call_args.kwargs['max_new_tokens'],128)
        recognizer.transcribe_result([],{})
        self.assertEqual(recognizer.model.transcribe.call_args.kwargs['beam_size'],3)

if __name__=='__main__':unittest.main()

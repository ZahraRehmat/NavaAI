import unittest
from unittest.mock import Mock,patch
from hybrid_speech import HybridRecognizer
from command_voice import CommandVoice
from selection_recognition import fast_range,endpoint_error
from selection_commands import range_command

def packet(text,probabilities=None):
    words=text.split();probabilities=probabilities or [.97]*len(words)
    return {'text':text,'words':[{'word':word,'probability':p} for word,p in zip(words,probabilities)],'confidence':sum(probabilities)/len(probabilities)}

class SelectionRecognitionTests(unittest.TestCase):
    context={'selection':True,'selection_hints':'scrolling working testing required words Islamabad Karachi'}

    def test_replay_logged_low_confidence_head_is_not_part_of_endpoint(self):
        result=packet('Select from scrolling to required Head.',[.9369,.9099,.9889,.9899,.8527,.0816])
        HybridRecognizer.selection_sentence(result,self.context)
        self.assertEqual(range_command(result['text'],mode=True)['end'],'required')
        session=CommandVoice({'handsfree':True});session.selecting=True
        route=session.route(result,self.context)
        self.assertEqual(route['text'],'select and copy from scrolling to required')
        self.assertEqual(route['kind'],'command')

    def test_unreliable_start_does_not_execute_because_average_confidence_passed(self):
        result=packet('Select from when to see Thank you.',[.9136,.9446,.277,.9888,.9138,.0598,.983])
        session=CommandVoice({'handsfree':True});session.selecting=True
        route=session.route(result,self.context)
        self.assertEqual(route['kind'],'review');self.assertIn('start words',route['reason'])

    def test_known_literal_and_confident_suffixes_are_never_cut(self):
        for hints,probabilities in [('scrolling required head',[.97]*5+[.08]),('scrolling required',[.97]*6)]:
            result=packet('select from scrolling to required head',probabilities)
            HybridRecognizer.selection_sentence(result,{'selection_hints':hints})
            self.assertEqual(range_command(result['text'],mode=True)['end'],'required head')

    def test_no_current_app_hints_means_no_tail_guessing(self):
        result=packet('select from scrolling to required head',[.97]*5+[.08])
        HybridRecognizer.selection_sentence(result,{})
        self.assertEqual(result['text'],'select from scrolling to required head')

    def test_fast_path_only_for_clear_endpoints_present_in_current_app(self):
        p=packet('select from scrolling to required')
        self.assertTrue(fast_range(p,self.context))
        self.assertFalse(fast_range(p,{'selection_hints':'Different window content'}))
        self.assertFalse(fast_range(packet('select from scrolling to required',[.97]*4+[.3]),self.context))
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        recognizer.commands.transcribe_result.return_value=p
        recognizer.commands.transcribe_controls.return_value={'text':'[unk]','confidence':0}
        recognizer.english.transcribe_result.side_effect=AssertionError('Clear current-app endpoints should not run Whisper')
        self.assertEqual(recognizer.transcribe_result([],self.context)['text'],p['text'])
        recognizer.english.transcribe_result.assert_not_called()

    def test_whisper_selection_is_bounded_without_changing_dictation(self):
        from speech import LocalRecognizer
        r=object.__new__(LocalRecognizer);r.config={'beam_size':3};r.model=Mock()
        r.model.transcribe.return_value=([],None)
        r.transcribe_result([],{'selection':True,'selection_hints':'scrolling required'})
        kwargs=r.model.transcribe.call_args.kwargs
        self.assertEqual((kwargs['beam_size'],kwargs['max_new_tokens']),(1,48))
        r.transcribe_result([],{'dictation':True});kwargs=r.model.transcribe.call_args.kwargs
        self.assertEqual((kwargs['beam_size'],kwargs['max_new_tokens']),(3,256))

    def test_natural_finish_aliases_end_selection_instead_of_closing_an_app(self):
        for phrase in ('close selection','selection off','turn off selection','stop selecting'):
            voice=CommandVoice({'handsfree':True});voice.selecting=True
            result=voice.route(packet(phrase),self.context)
            self.assertEqual(result['control'],'selection_off');self.assertFalse(voice.selecting)

if __name__=='__main__':unittest.main()

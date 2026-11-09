import unittest
from unittest.mock import Mock
from command_voice import CommandVoice
from hybrid_speech import HybridRecognizer
from voice_controls import DICTATION_ON,DICTATION_OFF


def heard(text,confidence=1,backend='vosk'):
    return {'text':text,'confidence':confidence,'words':[{'word':word,'probability':confidence} for word in text.split()],'backend':backend}


class VoiceControlRecognitionTests(unittest.TestCase):
    def recognizer(self,primary,compact):
        r=HybridRecognizer.__new__(HybridRecognizer);r.commands=Mock();r.english=Mock()
        r.commands.transcribe_result.return_value=primary;r.commands.transcribe_controls.return_value=compact
        r.english.transcribe_result.side_effect=AssertionError('Ordinary controls must not use Whisper')
        return r

    def test_all_dictation_aliases_change_mode_instead_of_typing_them(self):
        session=CommandVoice({'handsfree':True})
        for phrase in DICTATION_ON:
            self.assertEqual(session.route(heard(phrase))['control'],'dictation_on',phrase)
            self.assertTrue(session.dictating)
        for phrase in DICTATION_OFF:
            session.dictating=True
            self.assertEqual(session.route(heard(phrase))['control'],'dictation_off',phrase)
            self.assertFalse(session.dictating)

    def test_compact_vocabulary_recovers_start_dictation_from_competing_catalog_words(self):
        r=self.recognizer(heard('start nation',.6),heard('start dictation',.98,'vosk-controls'))
        result=r.transcribe_result([],{})
        self.assertEqual(result['text'],'start dictation');self.assertEqual(result['primary_text'],'start nation')
        self.assertEqual(CommandVoice({'handsfree':True}).route(result)['control'],'dictation_on')

    def test_compact_controls_need_shared_words_and_confidence(self):
        for primary,compact in [(heard('I am from Islamabad'),heard('start dictation')),(heard('start nation',.5),heard('start dictation',.5)),(heard('start nation',.5),heard('start dictation [unk]'))]:
            self.assertEqual(HybridRecognizer.prefer_control(primary,compact),primary)

    def test_unrecognized_commands_do_not_turn_into_whisper_sentences(self):
        r=self.recognizer(heard('start nation',.5),heard('[unk]',0))
        result=r.transcribe_result([],{})
        self.assertEqual(result['text'],'start nation');r.english.transcribe_result.assert_not_called()
        self.assertEqual(CommandVoice({'handsfree':True}).route(result)['kind'],'review')

    def test_type_payload_can_keep_clear_vosk_text_when_whisper_is_unclear(self):
        r=self.recognizer(heard('type wikipedia',.98),heard('[unk]',0))
        r.english.transcribe_result.side_effect=None
        r.english.transcribe_result.return_value=heard('Type, Wikipedia. media.',.18,'whisper-base.en')
        self.assertEqual(r.transcribe_result([],{})['text'],'type wikipedia')


if __name__=='__main__':unittest.main()

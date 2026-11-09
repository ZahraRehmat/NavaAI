import unittest
from unittest.mock import Mock
from dialog_voice import answer,grammar
from hybrid_speech import HybridRecognizer
from vosk_speech import vocabulary


class DialogVoiceTests(unittest.TestCase):
    def test_selection_uses_grid_letters_for_displayed_index_and_grammar(self):
        from smart_labels import smart_label
        labels=[smart_label(i) for i in range(9)]
        self.assertEqual(labels,list('AFHILMOQR'))
        self.assertEqual(answer('foxtrot',9,labels=labels),1)
        self.assertEqual(answer('click hotel',9,labels=labels),2)
        self.assertIsNone(answer('bravo',9,labels=labels))
        self.assertIsNone(answer('delta',9,labels=labels))
        phrases=grammar({'dialog_count':9,'dialog_labels':labels})
        self.assertIn('foxtrot',phrases);self.assertIn('click hotel',phrases)
        self.assertNotIn('bravo',phrases);self.assertNotIn('delta',phrases)

    def test_letters_and_nato_with_natural_prefixes(self):
        for text,expected in [('B',1),('bravo',1),('select D',3),('click delta',3),
                              ('press a',0),('Gwen choose charlie',2),('option alpha',0),('letter b',1)]:
            self.assertEqual(answer(text,4),expected,text)
        for text in ('b. Okay. Okay.','select d okay','open word','father to sun','E','bravo delta',''):
            self.assertIsNone(answer(text,4),text)

    def test_confirmation_and_cancel(self):
        self.assertEqual(answer('confirm',2,'confirm'),0)
        self.assertEqual(answer('no',2,'confirm'),1)
        self.assertIsNone(answer('bravo',2,'confirm'))
        self.assertEqual(answer('cancel selection',4),'cancel')

    def test_small_grammar_tracks_current_choices(self):
        model=Mock();model.vosk_model_find_word.return_value=1
        choices=vocabulary({'dialog_active':True,'dialog_count':4},model)
        for phrase in ('b','bravo','select d','click delta','cancel','gwen turn off','[unk]'):
            self.assertIn(phrase,choices)
        for phrase in ('echo','open chrome','select e','father to sun'):
            self.assertNotIn(phrase,choices)
        self.assertNotIn('bravo',grammar({'dialog_kind':'confirm'}))

    def test_dialog_supersedes_selection_dictation_and_busy(self):
        for context in ({'selection':True},{'dictation':True},{'selection':True,'busy':True}):
            recognizer=HybridRecognizer.__new__(HybridRecognizer)
            recognizer.commands=Mock();recognizer.english=Mock()
            heard={'text':'select d','confidence':1,'backend':'vosk'}
            recognizer.commands.transcribe_result.return_value=heard
            self.assertIs(recognizer.transcribe_result([],{'dialog_active':True,'dialog_count':4,**context}),heard)
            recognizer.english.transcribe_result.assert_not_called()
            recognizer.commands.transcribe_controls.assert_not_called()
            self.assertFalse(recognizer.commands.transcribe_result.call_args.args[1]['dictation'])


if __name__=='__main__':unittest.main()

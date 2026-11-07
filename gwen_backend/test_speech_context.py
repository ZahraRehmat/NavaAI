import unittest
from speech_context import correct,codes
from command_voice import CommandVoice,stale

class SpeechContextTests(unittest.TestCase):
    def test_observed_voice_phrases_route_without_planner(self):
        from grid_commands import parse
        session=CommandVoice({'handsfree':True})
        for spoken in ('gwen grid on','gwen listen grid on','gwen listen gwen grid on'):
            result=session.route({'text':spoken,'confidence':1})
            self.assertEqual(result['kind'],'command',result)
            self.assertEqual(parse(result['text']),[{'action':'smart_unavailable'}])
        self.assertEqual(session.route({'text':'gwen listen type hello','confidence':1})['text'],'type hello')
        self.assertEqual(session.route({'text':'hey gwen listen gwen','confidence':1})['control'],'handsfree')
        result=session.route({'text':'gwen open exit','confidence':.84,'words':[
            {'word':'gwen','probability':1},{'word':'open','probability':1},{'word':'exit','probability':.51}]})
        self.assertEqual(result['kind'],'review');self.assertTrue(result['confirmable'])
    def test_app_vocabulary_and_spoken_wifi(self):
        from vosk_speech import vocabulary
        class Model:
            def vosk_model_find_word(self,word):return 1
        words=vocabulary({},Model())
        for word in ('notepad','wifi','bluetooth','open notepad'):self.assertIn(word,words)
        self.assertEqual(correct('click y fi').text,'click wifi')
        self.assertEqual(correct('type y fi').text,'type y fi')
        self.assertEqual(correct('click y five',{'grid_active':True,'labels':['Y5']}).text,'click Y5')
    def test_cells_spelled_phonetically(self):
        for text in ('Cell A2','cell a two','cell ay to','select cell alpha two'):
            self.assertEqual(correct(text,{'office':'excel'}).text,'select cell A2')
        self.assertEqual(correct('cell echo five').text,'select cell E5')
        self.assertTrue(correct('cell eighty two').review)
        self.assertEqual(correct('cell alpha twenty three').text,'select cell A23')
        self.assertEqual(correct('cell b one two').text,'select cell B12')
        self.assertEqual(correct('cell echo one hundred and two').text,'select cell E102')
        self.assertTrue(correct('cell the two').review)
        self.assertEqual(correct('make cell echo five bold',{'office':'excel'}).text,'make E5 bold')
    def test_grid_letters_numbers_and_case(self):
        ctx={'grid_active':True,'labels':['FG','6MJ','A2','AB']}
        for text,wanted in (('click six em jay','click 6MJ'),('click 6MJ','click 6MJ'),('eff gee','FG'),('scroll down from eff gee','scroll down from FG'),('double click alpha bravo','double click AB')):
            result=correct(text,ctx);self.assertEqual(result.text,wanted);self.assertFalse(result.review)
    def test_ambiguous_oh_never_guesses(self):
        self.assertTrue(correct('click oh',{'grid_active':True,'labels':['O','0']}).review)
        self.assertEqual(correct('click oh',{'grid_active':True,'labels':['O']}).text,'click O')
    def test_invalid_code_not_snapped_to_visible_neighbor(self):
        result=correct('click eff gee',{'grid_active':True,'labels':['FB','EG']})
        self.assertTrue(result.review);self.assertIn('not a currently visible',result.reason)
    def test_literal_text_and_names_preserved(self):
        ctx={'grid_active':True,'labels':['FG']}
        self.assertEqual(correct('type four seas and why',ctx).text,'type four seas and why')
        self.assertEqual(correct('click Microsoft Store',ctx).text,'click Microsoft Store')
        self.assertEqual(correct('please click eff gee',ctx).text,'click FG')
        self.assertEqual(correct('please type four seas and why.',ctx).text,'type four seas and why.')
        self.assertEqual(CommandVoice().route({'text':'Gwen type Hello world.','confidence':.99})['text'],'type Hello world.')
    def test_silence_no_wake_and_conversation_do_not_execute(self):
        gate=CommandVoice()
        for text in ('','click FG','when we were there','the six people went home'):
            self.assertEqual(gate.route({'text':text,'confidence':.99})['kind'],'ignore')
    def test_wake_handsfree_sleep_and_bare_label(self):
        gate=CommandVoice();ctx={'grid_active':True,'labels':['FG']}
        self.assertEqual(gate.route({'text':'Gwen listen','confidence':.99})['control'],'handsfree')
        self.assertEqual(gate.route({'text':'eff gee','confidence':.99},ctx)['text'],'FG')
        self.assertEqual(gate.route({'text':'Gwen sleep','confidence':.99})['control'],'sleep')
        self.assertEqual(gate.route({'text':'click FG','confidence':.99},ctx)['kind'],'ignore')
        self.assertEqual(gate.route({'text':'stop','confidence':.99})['control'],'stop')
    def test_low_confidence_and_missing_targets_review_only(self):
        gate=CommandVoice();ctx={'grid_active':True,'labels':['FG']}
        self.assertEqual(gate.route({'text':'Gwen click FG','confidence':.5},ctx)['kind'],'review')
        self.assertFalse(gate.route({'text':'Gwen click FB','confidence':.99},ctx)['confirmable'])
        self.assertTrue(gate.route({'text':'Gwen click FG','confidence':.8},ctx)['confirmable'])
    def test_grid_activation_and_cell_command(self):
        gate=CommandVoice()
        self.assertEqual(gate.route({'text':'Gwen grid','confidence':.99})['text'],'gwen grid')
        self.assertEqual(gate.route({'text':'Gwen cell a two','confidence':.99},{'office':'excel'})['text'],'select cell A2')
    def test_stale_label_reuse_and_busy_audio_rejected(self):
        gate=CommandVoice();ctx={'grid_active':True,'grid_version':1,'labels':['FG'],'label_keys':{'FG':'first'},'busy':True}
        self.assertEqual(gate.route({'text':'Gwen click FG','confidence':.99},ctx)['kind'],'review')
        self.assertTrue(stale(ctx,{**ctx,'label_keys':{'FG':'second'}},'FG'))
        self.assertTrue(stale(ctx,{**ctx,'grid_version':2},'FG'))
    def test_malformed_chain_returns_review_instead_of_throwing(self):
        gate=CommandVoice()
        result=gate.route({'text':'Gwen click FG then something unrecognized','confidence':.99},{'grid_active':True,'labels':['FG']})
        self.assertEqual(result['kind'],'review')
    def test_recognizer_epoch_discards_old_audio(self):
        import threading,time
        from unittest.mock import patch,Mock
        from speech import VoiceEngine
        got=[];accepted=threading.Event();recognizer=Mock()
        recognizer.transcribe_result.return_value={'text':'Gwen grid','confidence':.99}
        engine=VoiceEngine(lambda packet,ctx:(got.append((packet,ctx)),accepted.set()),lambda _:None,lambda:{},detailed=True)
        engine.epoch=2
        with patch('speech.LocalRecognizer',return_value=recognizer):
            thread=threading.Thread(target=engine._recognize);thread.start();engine.ready.wait(2)
            engine.utterances.put(([],{'old':True},1));engine.utterances.put(([],{'new':True},2))
            self.assertTrue(accepted.wait(2));engine.close();thread.join(2)
        self.assertEqual(len(got),1);self.assertEqual(got[0][1],{'new':True});self.assertEqual(recognizer.transcribe_result.call_count,1)

if __name__=='__main__':unittest.main()

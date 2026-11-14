import unittest
from command_voice import CommandVoice,power_intent
from voice_gate import VoiceGate
from command_dictionary import intent
from grid_commands import toggle_intent
from direct_commands import parse_direct
from branding import strip_wake

class NavaBrandingTests(unittest.TestCase):
    def test_only_nava_can_wake_standby(self):
        for text in ('Gwen turn on','Glen turn on','NavaAI turn on','Nava AI turn on','Naval turn on'):
            self.assertIsNone(power_intent(text))
            self.assertEqual(CommandVoice({'assistant_active':False}).route({'text':text,'confidence':1})['kind'],'ignore')
        for text in ('Nava turn on','Hey Nava, turn on','NAVA switch on'):
            self.assertEqual(CommandVoice({'assistant_active':False}).route({'text':text,'confidence':1})['control'],'power_on')
    def test_obsolete_names_cannot_execute_in_handsfree_mode(self):
        for text in ('Gwen open Chrome','NavaAI open Word','Nava AI click A'):
            self.assertEqual(CommandVoice({'handsfree':True}).route({'text':text,'confidence':1})['kind'],'ignore')
            gate=VoiceGate();gate.handsfree=True;self.assertIsNone(gate.accept(text))
    def test_nava_routes_each_existing_command_family(self):
        session=CommandVoice({'handsfree':True})
        self.assertEqual(session.route({'text':'Nava open Chrome','confidence':1})['text'],'open Chrome')
        self.assertEqual(intent('Nava show dictionary'),{'action':'show'})
        self.assertEqual(intent('Nava move dictionary right'),{'action':'move_right'})
        self.assertEqual(toggle_intent('Nava grid'),'smart_unavailable')
        self.assertEqual(parse_direct('Nava press enter'),{'kind':'keys','keys':['enter']})
    def test_literal_text_is_not_rebranded_or_stripped(self):
        for payload in ('Gwen is a name','Nava AI is the product','NavaAI','Nava turn off'):
            self.assertEqual(parse_direct('type '+payload),{'kind':'type','text':payload})
        self.assertEqual(strip_wake('Nava, open Word'),'open Word')
        self.assertEqual(strip_wake('naval architecture'),'naval architecture')

if __name__=='__main__':unittest.main()

import unittest
from unittest.mock import Mock
from command_dictionary import intent,contextual,search,app_scopes,ENTRIES
from command_voice import CommandVoice

class CommandDictionaryTests(unittest.TestCase):
    def test_help_phrases_are_exact_and_payload_is_literal(self):
        for phrase in ('show commands','open dictionary','Gwen show dictionary'):
            self.assertEqual(intent(phrase),{'action':'show'})
        self.assertEqual(intent('hide commands'),{'action':'hide'})
        self.assertEqual(intent('open full dictionary'),{'action':'master'})
        self.assertEqual(intent('search dictionary for font size'),{'action':'search','query':'font size'})
        for phrase in ('type show commands','the dictionary is open','open Word','click A','show font dropdown'):
            self.assertIsNone(intent(phrase))

    def test_app_modes_and_youtube_are_additive_not_global(self):
        rows=contextual({'active':True,'target':{'title':'(1) Example - YouTube - Google Chrome'}})
        scopes={r.scope for r in rows};self.assertTrue({'youtube','browser','general'}<=scopes)
        self.assertEqual(rows[0].scope,'youtube');self.assertNotIn('excel',scopes)
        rows=contextual({'active':True,'target':{'title':'Untitled - Notepad'},'dictating':True,'grid':True})
        self.assertTrue({'notepad','dictation','grid','general'}<={r.scope for r in rows})
        self.assertNotIn('dictation on',[r.command for r in rows])
        self.assertEqual(contextual({'active':False}),[])
        self.assertEqual(app_scopes({'title':'Budget - Excel','class_name':'XLMAIN'}),['excel'])

    def test_master_searches_command_description_and_app(self):
        self.assertTrue(search('font size'))
        self.assertTrue(all(r.scope=='excel' for r in search('table','excel')))
        self.assertFalse(search('nonsensewordzzzz'))
        self.assertGreater(len(ENTRIES),150)
        self.assertEqual(len(ENTRIES),len({(r.scope,r.command) for r in ENTRIES}))

    def test_help_does_not_change_modes_and_can_be_opened_in_standby(self):
        for active in (False,True):
            for dictating in (False,True):
                session=CommandVoice({'assistant_active':active,'handsfree':active});session.dictating=dictating
                result=session.route({'text':'show commands','confidence':1})
                self.assertEqual(result['control'],'command_help')
                self.assertEqual(session.active,active);self.assertEqual(session.dictating,dictating)
        session=CommandVoice({'handsfree':True});session.dictating=True
        self.assertEqual(session.route({'text':'type show commands','confidence':1})['text'],'type show commands')
        self.assertEqual(session.route({'text':'hide commands','confidence':.5})['kind'],'review')

    def test_compact_recognizer_cannot_turn_prose_into_help(self):
        from hybrid_speech import HybridRecognizer
        primary={'text':'I want to show commands in my essay','confidence':.8}
        compact={'text':'show commands','confidence':1,'words':[{'word':'show','probability':1},{'word':'commands','probability':1}]}
        self.assertIs(HybridRecognizer.prefer_control(primary,compact),primary)

    def test_catalog_office_examples_have_actual_parsers(self):
        from office_control import parse_office
        from excel_commands import parse
        from direct_commands import parse_direct
        from dropdown_control import dropdown_intent
        for row in ENTRIES:
            if row.scope in ('word','excel','powerpoint'):
                self.assertTrue(parse_office(row.command) or parse_direct(row.command) or dropdown_intent(row.command) or (row.scope=='excel' and parse(row.command)),row.command)

if __name__=='__main__':unittest.main()

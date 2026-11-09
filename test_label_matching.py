import unittest,tempfile
from pathlib import Path
from label_matching import choose_label,normalize_label,AmbiguousLabel,NoLabelMatch
from accessibility import named_control_id
from visual_targets import choose_text_target
from file_control import resolve_file
from office_control import parse_office,office_kind
from unittest.mock import Mock,patch
from agent import Agent

class LabelMatchingTests(unittest.TestCase):
    def test_user_example_reordered_optional_extension_and_year_warning(self):
        row={'name':'Datesheet+2023-Mahnoor_Karachi.Pdf'}
        match=choose_label([row],'2024 datesheet mahnoor')
        self.assertIs(match['row'],row);self.assertTrue(match['warnings'])
        self.assertIs(choose_label([row],'mahnoor date sheet')['row'],row)
    def test_exact_year_beats_near_year_and_ties_ask(self):
        rows=[{'name':f'Datesheet-{year}-Mahnoor.pdf'} for year in (2023,2024)]
        self.assertEqual(choose_label(rows,'2024 datesheet mahnoor')['row']['name'],rows[1]['name'])
        with self.assertRaises(AmbiguousLabel):choose_label(rows,'datesheet mahnoor')
    def test_apostrophe_alias_typo_and_partial_long_title(self):
        self.assertEqual(normalize_label("Don't save"),normalize_label('dont save'))
        self.assertEqual(choose_label([{'name':'Share'}],'sheare')['row']['name'],'Share')
        self.assertEqual(choose_label([{'name':'Assessment Sheet (6) - Karachi campus'}],'assesment sheet 6')['row']['name'],'Assessment Sheet (6) - Karachi campus')
    def test_numeric_non_year_conflict_and_unrelated_candidates_rejected(self):
        with self.assertRaises(NoLabelMatch):choose_label([{'name':'Assessment Sheet (5)'}],'assessment sheet 6')
        with self.assertRaises(NoLabelMatch):choose_label([{'name':'Cancel'}],'apply')
        with self.assertRaises(NoLabelMatch):choose_label([{'name':'red.jpg'}],'red.png')
    def test_native_and_ocr_share_dictionary(self):
        row={'id':4,'name':"Don't Save",'type':'Button','bounds':[0,0,100,40]}
        self.assertEqual(named_control_id([row],'dont save'),4)
        ocr={'text':'Datesheet+2023-Mahnoor_Karachi.Pdf','score':.99,'bounds':[0,0,200,40]}
        self.assertIs(choose_text_target([ocr],'mahnoor datesheet'),ocr)
    def test_file_partial_reordered_and_extension_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'Datesheet+2023-Mahnoor_Karachi.Pdf';path.touch()
            self.assertEqual(resolve_file('2024 datesheet mahnoor',[[Path(tmp)]])[0],path)
    def test_office_natural_commands_and_literal_typing(self):
        self.assertEqual(parse_office('bold Mahnoor')['target'],'Mahnoor')
        self.assertEqual(parse_office('make it bold')['style'],'bold')
        self.assertEqual(parse_office('insert a table with three rows and four columns')['rows'],3)
        self.assertEqual(parse_office('insert 3 by 4 table')['columns'],4)
        self.assertEqual(parse_office('type Hello World.')['text'],'Hello World.')
        self.assertEqual(parse_office('write hello in A1')['range'],'A1')
        self.assertEqual(office_kind({'class_name':'XLMAIN','title':'Book1 - Excel'}),'excel')
        self.assertIsNone(office_kind({'title':'Word tutorial - Google Chrome'}))
    def test_bold_command_reaches_native_office_before_fragment_guard(self):
        agent=Agent(log=lambda _:None);agent._focus_native=Mock()
        with patch('office_control.execute_office',return_value='Applied bold.') as execute,patch('planner.Planner',side_effect=AssertionError('Do not use VLM')):
            result=agent.run('bold Mahnoor',interaction={'hwnd':1,'title':'Scratch - Word','class_name':'OpusApp'})
        self.assertEqual(result,'Applied bold.');self.assertEqual(execute.call_args.args[1]['target'],'Mahnoor')

if __name__=='__main__':unittest.main()

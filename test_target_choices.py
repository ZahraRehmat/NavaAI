import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from target_choices import select_target,rank_targets,SelectionCancelled
from label_matching import NoLabelMatch
from file_control import resolve_file,open_requested_file
from folder_control import resolve_folder

class ConfidenceChoices(unittest.TestCase):
    def test_spacing_reordered_and_partial_words(self):
        for query,label in [('signin','Sign in'),('log in google','Sign in with Google'),('funny cat','Funny cats playing'),('mahnoor datesheet','Datesheet+2023-Mahnoor_Karachi.Pdf')]:
            with self.subTest(query=query):
                row={'name':label};match=select_target([row],query,chooser=lambda *_:0)
                self.assertEqual(match['row'],row)
    def test_high_confidence_unique_is_automatic(self):
        chooser=Mock(side_effect=AssertionError('No popup needed'))
        self.assertEqual(select_target([{'name':'Sign in with Google'}],'google sign in',chooser=chooser)['row']['name'],'Sign in with Google')
    def test_multiple_matches_show_letter_options(self):
        rows=[{'name':f'Funny cats {verb}','id':n} for n,verb in enumerate(('playing','sleeping'))];chooser=Mock(return_value=1)
        result=select_target(rows,'funny cats',chooser=chooser)
        self.assertEqual(result['row']['id'],1);self.assertEqual(len(chooser.call_args.args[1]),2)
        self.assertTrue(all('match_score' in row for row in chooser.call_args.args[1]))
    def test_low_confidence_single_still_asks(self):
        chooser=Mock(return_value=0);select_target([{'name':'Instagram'}],'insta',chooser=chooser);chooser.assert_called_once()
    def test_cancel_never_selects_a_candidate(self):
        with self.assertRaises(SelectionCancelled):select_target([{'name':'Cats playing'},{'name':'Cats sleeping'}],'cats',chooser=lambda *_:None)
    def test_save_opposites_and_extension_conflicts(self):
        with self.assertRaises(NoLabelMatch):select_target([{'name':"Don't Save"}],'save',chooser=Mock())
        with self.assertRaises(NoLabelMatch):select_target([{'name':'red.jpg'}],'red.png',chooser=Mock())
        with self.assertRaises(NoLabelMatch):select_target([{'name':'Assessment 5'}],'assessment 6',chooser=Mock())
    def test_duplicate_file_names_use_popup_selected_full_path(self):
        with tempfile.TemporaryDirectory() as temp:
            a=Path(temp)/'one';b=Path(temp)/'two';a.mkdir();b.mkdir();(a/'report.pdf').touch();(b/'report.pdf').touch()
            picker=Mock(return_value=1)
            path,_=resolve_file('report.pdf',[[a,b]],chooser=picker)
            self.assertEqual(path,b/'report.pdf');self.assertIn(str(b),picker.call_args.args[1][1]['detail'])
            with patch('file_control.file_scopes',return_value=[[a,b]]),patch('file_control.os.startfile') as opened:
                open_requested_file('open report.pdf',threading.Event(),lambda _:None,chooser=lambda *_:1)
            opened.assert_called_once_with(str(b/'report.pdf'),'open')
    def test_duplicate_folders_use_choice(self):
        with tempfile.TemporaryDirectory() as temp:
            a=Path(temp)/'one';b=Path(temp)/'two';a.mkdir();b.mkdir();(a/'reports').mkdir();(b/'reports').mkdir()
            self.assertEqual(resolve_folder('reports',[a,b],chooser=lambda *_:1),b/'reports')
    def test_overlapping_native_text_and_button_are_one_choice(self):
        rows=[dict(name='Search',type='Text',bounds=[10,10,80,30]),dict(name='Search',type='Button',bounds=[0,0,100,40])]
        ranked=rank_targets(rows,'Search',merge_overlaps=True)
        self.assertEqual(len(ranked),1);self.assertEqual(ranked[0]['row']['type'],'Button')

if __name__=='__main__':unittest.main()

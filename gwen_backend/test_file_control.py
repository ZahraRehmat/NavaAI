import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from file_control import resolve_file,open_requested_file
from windows_api import usable_target
from agent import Agent

class FileControlTests(unittest.TestCase):
    def test_exact_pdf_stem_and_punctuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('Canva certificate.pdf','Marketing certificate 1 ( Easil).pdf','task_after_1.png','README.md'):(root/name).touch()
            for label,wanted in [('Canva certificate.pdf','Canva certificate.pdf'),('canva certificate','Canva certificate.pdf'),('task after 1','task_after_1.png'),('README.md','README.md')]:
                self.assertEqual(resolve_file(label,[[root]])[0],root/wanted)
            path,suggestions=resolve_file('canva marketing certificate',[[root]])
            self.assertIsNone(path);self.assertEqual(len(suggestions),2)
    def test_current_explorer_scope_wins_and_duplicates_do_not_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';a.mkdir();b.mkdir()
            (a/'README.md').touch();(b/'README.md').touch()
            self.assertEqual(resolve_file('README.md',[[b],[a,b]])[0],b/'README.md')
            with self.assertRaisesRegex(ValueError,'Multiple files'):resolve_file('README.md',[[a,b]])
    def test_file_request_precedes_fuzzy_app_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'README.md';path.touch();agent=Agent(log=lambda _:None)
            agent.catalog.launch=Mock(side_effect=AssertionError('Must not launch Readme app'))
            with patch('file_control.file_scopes',return_value=[[Path(tmp)]]),patch('file_control.os.startfile') as launch,patch('planner.Planner',side_effect=AssertionError('Must not load model')):
                result=agent.run('open README.md')
            launch.assert_called_once_with(str(path),'open');self.assertIn(str(path),result)
    def test_missing_local_pdf_can_use_visible_item_fallback(self):
        with patch('file_control.file_scopes',return_value=[]),patch('file_control.os.startfile') as launch:
            result=open_requested_file('open missing.pdf',threading.Event(),lambda r:None)
            self.assertIsNone(result);launch.assert_not_called()
    def test_tray_and_gwen_cannot_replace_target(self):
        for context in ({'title':'System tray overflow window.'},{'title':'','class_name':'Shell_TrayWnd'},{'title':'Gwen Doer - Type commands'}):self.assertFalse(usable_target(context))
        self.assertTrue(usable_target({'title':'Program Manager','class_name':'Progman'}))
        self.assertTrue(usable_target({'title':'screenshots - File Explorer','class_name':'CabinetWClass'}))

if __name__=='__main__':unittest.main()

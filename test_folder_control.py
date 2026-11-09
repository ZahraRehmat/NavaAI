import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from folder_control import folder_request,resolve_folder,open_requested_folder

class FolderTests(unittest.TestCase):
    def test_exact_name_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'desktop';b=root/'docs';a.mkdir();b.mkdir()
            (a/'FYP').mkdir();(a/'FYP reports').mkdir()
            self.assertEqual(resolve_folder('fyp',[a,a]),a/'FYP')
            self.assertIsNone(resolve_folder('FY',[a]))
            (b/'FYP').mkdir()
            with self.assertRaisesRegex(ValueError,'Multiple folders'):resolve_folder('FYP',[a,b])
    def test_explicit_missing_never_falls_to_model(self):
        with tempfile.TemporaryDirectory() as tmp,patch('folder_control.known_roots',return_value=[Path(tmp)]),patch('folder_control.explorer_folders',return_value=[]):
            self.assertIn('Could not find',open_requested_folder('open FYP folder',threading.Event(),lambda row:None))
            self.assertIsNone(open_requested_folder('open chrome',threading.Event(),lambda row:None))
    def test_verified_launch_uses_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'FYP';path.mkdir();records=[]
            with patch('folder_control.known_roots',return_value=[Path(tmp)]),patch('folder_control.explorer_folders',side_effect=[[],[(7,path)]]),patch('folder_control.os.startfile') as launch:
                self.assertEqual(open_requested_folder('open FYP folder',threading.Event(),records.append),'Opened folder: '+str(path))
                launch.assert_called_once_with(str(path),'explore')
                self.assertTrue(records[-1].get('folder_open_verified'))
    def test_commands(self):
        self.assertEqual(folder_request('open FYP folder'),('FYP',True))
        self.assertEqual(folder_request('open folder "FYP"'),('FYP',True))
        self.assertIsNone(folder_request('click on FYP'))

if __name__=='__main__':unittest.main()

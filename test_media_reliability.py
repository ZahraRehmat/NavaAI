"""Metadata and fake model tests only: no media is viewed or played."""
import ctypes,json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
import numpy as np
import windows_api as win
from file_control import resolve_file
from planner import Planner,requested_open_target

class MediaReliabilityTests(unittest.TestCase):
    def test_video_stem_and_extension_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/'bandicam 2025-12-09 09-09-51-593.mp4';video.touch()
            for label in (video.stem,video.name):self.assertEqual(resolve_file(label,[[root]])[0],video)
    def test_dates_alone_do_not_suggest_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('CamScanner 12-09-2026 12.17.pdf','ChatGPT Image Oct 21 2025.png'):(root/name).touch()
            self.assertEqual(resolve_file('bandicam 2025-12-09 09-09-51-593',[[root]]),(None,[]))
    def test_wrong_extension_is_not_silently_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'red.jpg';path.touch()
            found,suggestions=resolve_file('red.png',[[root]])
            self.assertIsNone(found);self.assertEqual(suggestions,[path])
    def test_explicit_target_does_not_inherit_previous_filename(self):
        p=Planner.__new__(Planner);p.config={};p.stop=threading.Event();p.gc=Mock();p.tokenizer=Mock()
        p.tokenizer.encode.return_value.input_ids=np.zeros((1,100))
        p._generate=Mock(side_effect=[Mock(texts=['{"action":"double_click","target":"previous-video.mp4"}']),Mock(texts=['{"x":200,"y":300}'])])
        with tempfile.TemporaryDirectory() as tmp:
            result=p.next('open current-video',{'mode':'desktop'},Image.new('RGB',(800,600)),[],[{'task':'open previous-video.mp4','result':'failed'}],trace_dir=tmp)
            data=json.loads((Path(tmp)/'model-input.json').read_text())
            self.assertNotIn('previous-video',data['prompt'])
            self.assertIn('current-video',p._generate.call_args_list[1].args[0])
            self.assertNotIn('previous-video',p._generate.call_args_list[1].args[0])
            self.assertEqual(result,{'action':'double_click','x':200,'y':300})
            variants=data['schema']['anyOf'];entry=next(v for v in variants if v['properties']['action']['enum']==['double_click'])
            self.assertEqual(entry['properties']['target']['enum'],['current-video'])
        self.assertEqual(requested_open_target('open red.png'),'red.png')
        self.assertIsNone(requested_open_target('open one then open two'))
    def test_closed_player_is_skipped_for_living_explorer(self):
        current={'hwnd':1,'title':'Gwen Doer - Type commands'}
        player={'hwnd':2,'title':'Media Player'};explorer={'hwnd':3,'title':'Folder - File Explorer'}
        with patch('windows_api.target_alive',side_effect=lambda c:c['hwnd']==3):self.assertEqual(win.choose_target(current,[player,explorer]),explorer)
    def test_closed_handle_reports_stale_target_not_permission(self):
        with patch.object(win.user,'IsWindow',return_value=False):
            with self.assertRaisesRegex(ValueError,'closed'):win.ensure_input_allowed(999)
    def test_reused_handle_with_different_pid_is_rejected(self):
        def pid(hwnd,p):
            ctypes.cast(p,ctypes.POINTER(ctypes.c_ulong)).contents.value=222
            return 1
        with patch.object(win.user,'IsWindow',return_value=True),patch.object(win.user,'IsWindowVisible',return_value=True),patch.object(win.user,'GetWindowThreadProcessId',side_effect=pid):
            self.assertFalse(win.target_alive({'hwnd':7,'pid':111}))

if __name__=='__main__':unittest.main()

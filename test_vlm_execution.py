import unittest
from unittest.mock import Mock,patch
from PIL import Image
from agent import Agent

class VlmExecutionTests(unittest.TestCase):
    def test_single_requested_click_never_loops(self):
        a=Agent(log=lambda _:None);a.planner=Mock();a.planner.next.return_value={'action':'click','x':500,'y':500}
        with patch('desktop_control.foreground_title',return_value='Fixture'),patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.window_bounds',return_value=(0,0,800,600)),patch('desktop_control.capture',return_value=Image.new('RGB',(800,600))),patch('desktop_control.act') as act:
            result=a.run('Select BETA using a single click.',step_limit=5)
        self.assertIn('Clicked',result);a.planner.next.assert_called_once();act.assert_called_once()
    def test_later_observation_follows_opened_window(self):
        a=Agent(log=lambda _:None);a.planner=Mock();a.planner.next.side_effect=[{'action':'double_click','x':500,'y':500},{'action':'done','message':'Document opened'}]
        a.catalog.resolve=Mock(side_effect=ValueError('No app'));a._focus_native=Mock()
        with patch('folder_control.open_requested_folder',return_value=None),patch('desktop_control.foreground_title',side_effect=['Original app','Original app','New document','New document']),patch('desktop_control.foreground_handle',side_effect=[1,1,2]),patch('desktop_control.window_bounds',return_value=(0,0,800,600)),patch('desktop_control.capture',return_value=Image.new('RGB',(800,600))),patch('desktop_control.act'):
            result=a.run('Open the first document then read its title.',interaction={'hwnd':1,'title':'Original app'},step_limit=3)
        self.assertEqual(result,'Document opened');a._focus_native.assert_called_once()
        self.assertEqual(a.planner.next.call_args_list[1].args[1]['foreground_window'],'New document')
    def test_visual_open_uses_whole_screen_not_offset_window_crop(self):
        a=Agent(log=lambda _:None);a.planner=Mock();a.planner.next.return_value={'action':'double_click','x':800,'y':900}
        a.catalog.resolve=Mock(side_effect=ValueError('No app'))
        full=Image.new('RGB',(1920,1200))
        with patch('file_control.open_requested_file',return_value=None),patch('folder_control.open_requested_folder',return_value=None),patch('desktop_control.foreground_title',return_value='Small popup'),patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.window_bounds',return_value=(400,250,900,800)),patch('desktop_control.screen_bounds',return_value=(0,0,1920,1200)),patch('desktop_control.capture',return_value=full) as capture,patch('desktop_control.act') as act:
            result=a.run('open SAMPLE.pdf')
        capture.assert_called_once_with(resize=False)
        self.assertIs(a.planner.next.call_args.args[2],full)
        self.assertEqual(act.call_args.kwargs['bounds'],(0,0,1920,1200))
        self.assertIn('Double-clicked',result);a.planner.next.assert_called_once()

if __name__=='__main__':unittest.main()

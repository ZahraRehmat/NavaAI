import unittest
from unittest.mock import Mock,patch
from PIL import Image
from agent import Agent
from routing import open_chat_intent
from visual_targets import choose_text_target
from desktop_control import map_point

class VisualTargetTests(unittest.TestCase):
    def test_open_chat_intent(self):
        self.assertEqual(open_chat_intent('open kashaf uni chat'),'kashaf uni')
        self.assertEqual(open_chat_intent('open Kashaf Uni chat in WhatsApp'),'Kashaf Uni')
        self.assertIsNone(open_chat_intent('open whatsapp'))

    def test_named_text_case_and_spaces(self):
        row={'text':'Kashaf Uni','score':.98,'bounds':[10,10,100,30]}
        self.assertIs(choose_text_target([row],'kashaf uni'),row)
        with self.assertRaises(ValueError): choose_text_target([row,row],'kashaf uni')
        with self.assertRaises(ValueError): choose_text_target([dict(row,score=.5)],'kashaf uni')

    def test_window_relative_mapping(self):
        self.assertEqual(map_point(500,500,(100,200,900,800)),(500,500))
        self.assertEqual(map_point(1000,1000,(100,200,900,800)),(899,799))

    def test_chat_uses_ocr_if_native_tree_is_incomplete(self):
        a=Agent(log=lambda _:None); a.active_target='WhatsApp'; a.native=Mock(); a.native.observe.return_value=[]
        a.visual=Mock(); a.visual.find.return_value={'text':'Kashaf Uni','score':.98,'bounds':[100,200,200,240]}
        with patch('planner.Planner',side_effect=AssertionError('Must not load')),patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.foreground_title',return_value='WhatsApp'),patch('desktop_control.window_bounds',return_value=(100,100,900,700)),patch('desktop_control.capture',return_value=Image.new('RGB',(800,600))),patch('desktop_control.act') as click:
            result=a.run('open kashaf uni chat')
        self.assertIn('Clicked the visible kashaf uni text',result)
        self.assertEqual(click.call_count,1)
        self.assertEqual(click.call_args.kwargs['bounds'],(100,100,900,700))
        a.native.act.assert_not_called()

    def test_com_failure_does_not_block_ocr(self):
        a=Agent(log=lambda _:None); a.active_target='WhatsApp'; a.native=Mock()
        a.native.observe.side_effect=RuntimeError('An event was unable to invoke any of the subscribers')
        a.visual=Mock(); a.visual.find.return_value={'text':'Gull','score':.98,'bounds':[100,200,200,240]}
        with patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.foreground_title',return_value='WhatsApp'),patch('desktop_control.window_bounds',return_value=(100,100,900,700)),patch('desktop_control.capture',return_value=Image.new('RGB',(800,600))),patch('desktop_control.act') as click:
            result=a.run('opengull chat')
        self.assertIn('Clicked the visible gull',result); self.assertEqual(click.call_count,1)

    def test_observation_failure_is_not_reported_as_model_failure(self):
        a=Agent(log=lambda _:None); a.active_target='Word'; a.native=Mock(); a.planner=Mock()
        with patch('desktop_control.foreground_title',return_value='Word'),patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.window_bounds',side_effect=ValueError('Window unavailable')):
            result=a.run('open first file on word')
        self.assertIn('Qwen was not called',result); a.planner.next.assert_not_called()

if __name__=='__main__': unittest.main(verbosity=2)

import unittest
from unittest.mock import Mock,patch
from routing import normalize_launch_verb,named_click_intent
from accessibility import named_control_id
from agent import Agent

class NativeRoutingTests(unittest.TestCase):
    def test_launch_verb_typos(self):
        for word in ('oepn','opne','opn','open'):
            self.assertEqual(normalize_launch_verb(word+' store'),'open store')
        self.assertEqual(normalize_launch_verb('search store'),'search store')

    def test_typo_launch_does_not_load_model(self):
        a=Agent(log=lambda _:None)
        a.catalog.launch=Mock(return_value='Microsoft Store')
        with patch('planner.Planner',side_effect=AssertionError('Must not load')),patch('agent.time.sleep'):
            a.run('oepn store')
        a.catalog.launch.assert_called_once_with('store')

    def test_named_click(self):
        self.assertEqual(named_click_intent('click on netflix app'),'netflix')
        self.assertEqual(named_click_intent('click the Search button'),'Search')
        self.assertIsNone(named_click_intent('click Search and type hello'))

    def test_visible_control_names(self):
        controls=[{'id':1,'name':'Netflix','bounds':[0,0,100,100]},{'id':2,'name':'Netflix Free','bounds':[5,5,95,95]}]
        self.assertEqual(named_control_id(controls,'netflix'),1)
        with self.assertRaisesRegex(ValueError,'Nothing was clicked'): named_control_id(controls,'WhatsApp')

    def test_ambiguous_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'More than one'):
            named_control_id([{'id':1,'name':'Netflix','bounds':[0,0,10,10]},{'id':2,'name':'Netflix','bounds':[20,20,30,30]}],'netflix')

    def test_native_click_uses_observed_id_and_app_focus(self):
        a=Agent(log=lambda _:None); a.active_target='Microsoft Store'; a.native=Mock()
        a.native.observe.return_value=[{'id':7,'name':'Netflix','bounds':[10,10,100,100]}]
        with patch('planner.Planner',side_effect=AssertionError('Must not load')): a.run('click on netflix app')
        a.native.focus_app.assert_called_once_with('Microsoft Store')
        a.native.act.assert_called_once_with({'action':'ui_click','id':7})

    def test_missing_native_target_does_not_fallback_to_coordinates(self):
        a=Agent(log=lambda _:None); a.active_target='Microsoft Store'; a.native=Mock(); a.native.observe.return_value=[]
        a.visual=Mock(); a.visual.find.side_effect=ValueError('No visible text matches netflix. Nothing was clicked.')
        with patch('planner.Planner',side_effect=AssertionError('Must not load')),patch('desktop_control.foreground_handle',return_value=1),patch('desktop_control.foreground_title',return_value='Microsoft Store'),patch('desktop_control.window_bounds',return_value=(0,0,100,100)),patch('desktop_control.capture',return_value=Mock()),patch('desktop_control.act') as click:
            result=a.run('click on netflix app')
        self.assertIn('No visible text matches netflix',result); a.native.act.assert_not_called(); click.assert_not_called()

if __name__=='__main__': unittest.main(verbosity=2)

"""Regressions from the user's failing commands; no desktop input."""
import unittest
from unittest.mock import Mock,patch
from routing import search_intent
from actions import validate_action, fingerprint
from agent import Agent

class RegressionTests(unittest.TestCase):
    def test_browser_search_routes_from_native_app(self):
        r=search_intent('search youtube on chrome','Task Manager')
        self.assertEqual(r['kind'],'browser_search')
        self.assertEqual(r['url'],'https://www.google.com/search?q=youtube')

    def test_url_routes_directly(self):
        self.assertEqual(search_intent('search youtube.com on chrome')['url'],'https://youtube.com')

    def test_store_typo_and_encoding(self):
        self.assertEqual(search_intent('search instgarm on store')['query'],'instagram')
        self.assertEqual(search_intent('search instagram on store')['query'],'instagram')
        self.assertIn('query=a%20%26%20b',search_intent('search a & b on store')['uri'])

    def test_follow_up_uses_active_app(self):
        self.assertEqual(search_intent('search instagram','Microsoft Store')['kind'],'store_search')
        self.assertEqual(search_intent('search weather','edge')['channel'],'msedge')
        self.assertEqual(search_intent('search whatsapp','Task Manager')['kind'],'native_search')

    def test_bad_coordinates_rejected(self):
        for x in ([184,455],float('nan'),float('inf'),True,'100',-1,1001):
            with self.subTest(x=x), self.assertRaises(ValueError): validate_action({'action':'click','x':x,'y':455})

    def test_invalid_action_never_reaches_mouse(self):
        import desktop_control
        with patch.object(desktop_control.pg,'click') as click:
            with self.assertRaises(ValueError): desktop_control.act({'action':'click','x':[184,455],'y':455})
            click.assert_not_called()

    def test_repeat_fingerprint_ignores_explanation(self):
        self.assertEqual(fingerprint({'action':'click','x':100,'y':500,'reason':'a'}),fingerprint({'action':'click','x':100,'y':500,'reason':'b'}))

    def test_search_never_loads_vlm_or_mouse(self):
        a=Agent(log=lambda _:None); a.browser=Mock(); a.browser.page.url='https://youtube.com/'
        a.mode='desktop'; a.active_target='Task Manager'
        with patch('planner.Planner',side_effect=AssertionError('VLM must not load')),patch('desktop_control.act',side_effect=AssertionError('Desktop must not run')):
            a.run('search youtube.com on chrome',background=True)
        self.assertEqual(a.mode,'browser')
        a.browser.act.assert_called_once_with({'action':'navigate','url':'https://youtube.com'})

    def test_store_never_clicks_or_loads_model(self):
        a=Agent(log=lambda _:None)
        with patch('agent.os.startfile') as launch,patch('planner.Planner',side_effect=AssertionError('VLM must not load')):
            a.run('search instgarm on store')
        launch.assert_called_once_with('ms-windows-store://search/?query=instagram')
        self.assertIsNone(a.planner)

if __name__=='__main__': unittest.main(verbosity=2)

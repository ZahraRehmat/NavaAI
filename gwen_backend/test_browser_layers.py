"""Real Chromium tests for covered controls, frame controls and stale observations."""
import unittest
from browser_control import Browser
from agent import Agent
from unittest.mock import Mock,patch

class BrowserLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=Browser(profile_name='layer-verification'); cls.b.open('chrome',True)

    @classmethod
    def tearDownClass(cls): cls.b.close()

    def test_owned_browser_process_is_identified(self):
        self.assertIsInstance(self.b.process_id,int)
        self.assertGreater(self.b.process_id,0)

    def test_native_dom_tab_commands_and_fuzzy_switching(self):
        original=self.b.page;original.set_content('<title>Original cats page</title>')
        try:
            self.b.command({'action':'tab_new'});second=self.b.page;second.set_content('<title>Project reference document</title>')
            self.b.command({'action':'tab_switch','target':'original cats'})
            self.assertIs(self.b.page,original)
            self.b.command({'action':'tab_switch','target':'project reference'})
            self.assertIs(self.b.page,second)
            self.b.command({'action':'tab_close'});self.assertTrue(second.is_closed());self.assertIs(self.b.page,original)
        finally:
            self.b.selected=original

    def test_video_pause_resume_are_idempotent(self):
        self.b.page.set_content('<canvas id="c" width="100" height="100"></canvas><video id="v" muted width="320" height="200"></video>')
        self.b.page.evaluate('''async()=>{const canvas=document.querySelector('canvas');canvas.getContext('2d').fillRect(0,0,50,50);const v=document.querySelector('video');v.srcObject=canvas.captureStream(10);await v.play()}''')
        self.b.command({'action':'media_pause'});self.assertTrue(self.b.page.locator('video').evaluate('v=>v.paused'))
        self.b.command({'action':'media_pause'});self.assertTrue(self.b.page.locator('video').evaluate('v=>v.paused'))
        self.b.command({'action':'media_play'});self.assertFalse(self.b.page.locator('video').evaluate('v=>v.paused'))
        self.b.command({'action':'media_play'});self.assertFalse(self.b.page.locator('video').evaluate('v=>v.paused'))

    def test_closed_managed_browser_reopens(self):
        b=self.b;old=b.context;old.close()
        b.open('chrome',True)
        self.assertIsNot(b.context,old)
        b.page.set_content('<title>Recovered</title>')
        self.assertEqual(b.page.title(),'Recovered')

    def test_popup_controls_are_exposed_instead_of_covered_buttons(self):
        self.b.page.set_content('''<button aria-label="Log in" onclick="document.body.dataset.login='yes'">Log in</button><div id="overlay" style="position:fixed;inset:0;z-index:100;background:#eee"><button onclick="document.body.dataset.accepted='yes';document.getElementById('overlay').remove()">I understand</button></div>''')
        obs=self.b.observe()
        self.assertIn('I understand',[e['text'] for e in obs['elements']])
        self.assertNotIn('Log in',[e['text'] for e in obs['elements']])
        self.b.click_named('i understand')
        self.assertEqual(self.b.page.locator('body').get_attribute('data-accepted'),'yes')
        self.assertIsNone(self.b.page.locator('body').get_attribute('data-login'))
        self.assertIn('Log in',[e['text'] for e in self.b.observe()['elements']])

    def test_ambiguous_browser_choices_are_marked_and_selected(self):
        self.b.page.set_content('''<button onclick="document.body.dataset.chosen='A'">Funny cats playing</button><button onclick="document.body.dataset.chosen='B'">Funny cats sleeping</button>''')
        def choose(query,options,preview=None):
            self.assertEqual(len(options),2);self.assertTrue(preview.startswith(b'\x89PNG'))
            self.assertEqual(self.b.page.locator('#gwen-target-choices b').all_text_contents(),['A','B'])
            return 1
        self.b.click_named('funny cats',chooser=choose)
        self.assertEqual(self.b.page.locator('body').get_attribute('data-chosen'),'B')
        self.assertEqual(self.b.page.locator('#gwen-target-choices').count(),0)

    def test_cancel_browser_choice_cleans_marks_and_clicks_nothing(self):
        from target_choices import SelectionCancelled
        self.b.page.set_content('<button onclick="document.body.dataset.clicked=1">Cats playing</button><button>Cats sleeping</button>')
        with self.assertRaises(SelectionCancelled):self.b.click_named('cats',chooser=lambda *_,**kw:None)
        self.assertIsNone(self.b.page.locator('body').get_attribute('data-clicked'))
        self.assertEqual(self.b.page.locator('#gwen-target-choices').count(),0)

    def test_chosen_browser_label_is_revalidated(self):
        self.b.page.set_content('<button onclick="document.body.dataset.clicked=1">Instagram</button>')
        def choose(*_,**kw):self.b.page.locator('button').evaluate("e=>e.textContent='Different action'");return 0
        with self.assertRaisesRegex(ValueError,'label changed'):self.b.click_named('insta',chooser=choose)
        self.assertIsNone(self.b.page.locator('body').get_attribute('data-clicked'))

    def test_named_request_does_not_click_a_different_label(self):
        self.b.page.set_content('<button aria-label="Log in" onclick="document.body.dataset.clicked=1">Log in</button>')
        with self.assertRaisesRegex(ValueError,'No reachable control'): self.b.click_named('Sign in with Google')
        self.assertIsNone(self.b.page.locator('body').get_attribute('data-clicked'))
    def test_dictionary_matches_apostrophe_and_alias(self):
        self.b.page.set_content('''<button onclick="document.body.dataset.clicked='yes'">Don't Save</button>''')
        self.b.click_named('dont save')
        self.assertEqual(self.b.page.locator('body').get_attribute('data-clicked'),'yes')

    def test_controls_inside_frames_are_reachable(self):
        self.b.page.set_content('''<iframe style="width:500px;height:300px" srcdoc="<button onclick='document.body.dataset.clicked=1'>I understand</button>"></iframe>''')
        self.b.page.frames[-1].locator('button').wait_for()
        self.b.click_named('I understand')
        self.assertEqual(self.b.page.frames[-1].locator('body').get_attribute('data-clicked'),'1')

    def test_previous_attributes_do_not_leave_duplicate_ids(self):
        self.b.page.set_content('<button id="a">A</button><button id="b">B</button>')
        self.b.observe(); self.b.page.locator('#a').evaluate("e=>e.style.display='none'")
        obs=self.b.observe()
        self.assertEqual([e['text'] for e in obs['elements']],['B'])
        self.assertEqual(self.b.page.locator('[data-gwen-id="0"]').count(),1)

    def test_stale_observation_cannot_click_replacement_control(self):
        self.b.page.set_content('<button>Old</button>'); self.b.observe()
        self.b.page.set_content('<button onclick="document.body.dataset.clicked=1">Replacement</button>')
        with self.assertRaises(Exception): self.b.act({'action':'browser_click','id':0})
        self.assertIsNone(self.b.page.locator('body').get_attribute('data-clicked'))

    def test_direct_typing_uses_owned_background_browser(self):
        self.b.page.set_content('<input aria-label="Name">'); self.b.page.locator('input').focus()
        a=Agent(log=lambda _:None); a.browser=self.b; a.mode='browser'; a.active_target='chrome'
        with patch('desktop_control.act',side_effect=AssertionError('Must not use physical keyboard')):
            a.run('type "Gwen voice text"',background=True,interaction={'hwnd':42,'title':'Other app'})
        self.assertEqual(self.b.page.locator('input').input_value(),'Gwen voice text')

class NativeSearchTests(unittest.TestCase):
    def test_task_manager_search_uses_the_field_not_model_clicks(self):
        a=Agent(log=lambda _:None); a.active_target='Task Manager'; a.native=Mock()
        a.native.observe.return_value=[{'id':4,'type':'Edit','name':'Type a name, publisher, or PID','automation_id':'SearchBox'}]
        with patch('planner.Planner',side_effect=AssertionError('Must not load model')):
            result=a.run('search whatsapp')
        a.native.act.assert_called_once_with({'action':'ui_fill','id':4,'text':'whatsapp'})
        self.assertIn('search field',result)

    def test_elevated_target_stops_before_model_or_input(self):
        a=Agent(log=lambda _:None); a.active_target='Task Manager'; a.native=Mock()
        a.native.focus_app.side_effect=PermissionError('higher Windows integrity level')
        with patch('planner.Planner',side_effect=AssertionError('Must not load model')):
            result=a.run('search whatsapp')
        self.assertIn('higher Windows integrity',result); a.native.act.assert_not_called()

if __name__=='__main__': unittest.main(verbosity=2)

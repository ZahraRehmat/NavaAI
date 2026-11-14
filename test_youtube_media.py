import base64,io,threading,unittest,wave
from unittest.mock import Mock,patch
from browser_commands import intent
from grid_input import keyboard_command

CHROME={'hwnd':1,'pid':2,'title':'Fixture - YouTube - Google Chrome'}


class MediaRoutingTests(unittest.TestCase):
    def test_media_phrases_do_not_change_tabs_typing_or_navigation(self):
        for phrase in ('pause video','pause youtube','pause the youtube video'):
            self.assertEqual(intent(phrase,True)['action'],'media_pause')
        for phrase in ('resume video','play youtube','unpause video'):
            self.assertEqual(intent(phrase,True)['action'],'media_play')
        for phrase,seconds in [('forward 5 seconds',5),('fast forward ten seconds',10),('rewind five seconds',-5),('go back 10 seconds',-10)]:
            self.assertEqual(intent(phrase,True)['seconds'],seconds)
            self.assertTrue(keyboard_command(phrase,CHROME))
        self.assertEqual(intent('play next video')['action'],'media_next')
        self.assertEqual(intent('play previous video')['action'],'media_previous')
        self.assertEqual(intent('next tab'),{'action':'tab_switch','target':'next'})
        for phrase in ('forward email','type pause video','move cursor forward','rewind account','click next'):
            self.assertIsNone(intent(phrase,True))
        self.assertTrue(keyboard_command('pause',CHROME))
        self.assertFalse(keyboard_command('pause',{'title':'Document - Word'}))
        from command_voice import CommandVoice
        for kind in ('normal','dictation','selection'):
            voice=CommandVoice({'handsfree':True});voice.dictating=kind=='dictation';voice.selecting=kind=='selection'
            self.assertEqual(voice.route({'text':'pause','confidence':1},{'interaction':CHROME})['kind'],'command')

    def test_open_website_on_new_tab_does_not_become_tab_title_search(self):
        for phrase in ('open you tube on new tab','open youtube in a new tab','visit youtube.com on new tab'):
            self.assertEqual(intent(phrase,True),{'action':'tab_open_url','url':'https://www.youtube.com/' if 'youtube.com' not in phrase else 'https://youtube.com'})
        from native_browser import command
        with patch('native_browser.keys') as keys,patch('native_browser.navigate_window',return_value='Navigation requested') as nav:
            command(CHROME,{'action':'tab_open_url','url':'https://www.youtube.com/'},threading.Event())
            keys.assert_called_once_with(CHROME,['ctrl','t'],unittest.mock.ANY)
            nav.assert_called_once_with(CHROME,'https://www.youtube.com/',unittest.mock.ANY)

    def test_native_pause_checks_state_and_never_toggles_twice(self):
        from native_media import command
        element=Mock();element.element_info.runtime_id=[1,2]
        paused={'element':element,'name':'Play (k)','state':'play','visible':True}
        playing={**paused,'name':'Pause (k)','state':'pause'}
        with patch('system_media.command',return_value=None),patch('native_media.check_active'),patch('native_media.controls',side_effect=[[playing],[playing],[paused]]),patch('native_browser.focused'),patch('native_media.focus_control'),patch('native_media.click_control') as click:
            self.assertEqual(command(CHROME,{'action':'media_pause'},threading.Event()),'Video paused.')
            click.assert_called_once()
        with patch('system_media.command',return_value=None),patch('native_media.check_active'),patch('native_media.controls',return_value=[paused]),patch('native_browser.focused'),patch('native_media.click_control') as click:
            self.assertIn('already paused',command(CHROME,{'action':'media_pause'},threading.Event()))
            click.assert_not_called()
        with patch('system_media.command',return_value=None),patch('native_media.check_active'),patch('native_media.controls',return_value=[playing]),patch('native_browser.focused'),patch('native_media.focus_control'),patch('native_media.click_control') as click,patch('native_media.time.monotonic',side_effect=[0,0,0,2]):
            with self.assertRaisesRegex(ValueError,'No second toggle'):command(CHROME,{'action':'media_pause'},threading.Event())
            click.assert_called_once()

    def test_native_seek_keys_are_scoped_to_observed_player_focus(self):
        from native_media import command
        row={'element':Mock(),'name':'Play (k)','state':'play','visible':True}
        with patch('system_media.command',return_value=None),patch('native_media.check_active'),patch('native_media.controls',return_value=[row]),patch('native_browser.focused'),patch('native_media.focus_control',return_value=(3,4)),patch('pywinauto.uia_defines.IUIA') as api,patch('native_browser.keys') as keys:
            api.return_value.iuia.GetFocusedElement.return_value.GetRuntimeId.return_value=[3,4]
            for seconds,expected in ((5,['right']),(-5,['left']),(10,['l']),(-10,['j'])):
                command(CHROME,{'action':'media_seek','seconds':seconds},threading.Event())
                self.assertEqual(keys.call_args.args[1],expected)
            api.return_value.iuia.GetFocusedElement.return_value.GetRuntimeId.return_value=[99]
            keys.reset_mock()
            with self.assertRaisesRegex(ValueError,'focus changed'):command(CHROME,{'action':'media_seek','seconds':5},threading.Event())
            keys.assert_not_called()


class RealDomMediaTests(unittest.TestCase):
    channel="chrome"
    def test_finite_media_seeking_pause_resume_and_next_previous(self):
        from browser_control import Browser
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(1);wav.setframerate(8000);wav.writeframes(bytes([128])*8000*30)
        src='data:audio/wav;base64,'+base64.b64encode(buffer.getvalue()).decode()
        browser=Browser(profile_name='media-verification-'+self.channel);browser.open(self.channel,True)
        try:
            page=browser.page
            html='<title>YouTube media fixture</title><audio controls muted src="'+src+'"></audio><button class="ytp-next-button" onclick="document.body.dataset.next=1">Next</button><button class="ytp-prev-button" onclick="document.body.dataset.prev=1">Previous</button>'
            page.route('https://www.youtube.com/**',lambda route:route.fulfill(content_type='text/html',body=html))
            page.goto('https://www.youtube.com/watch?v=fixture')
            page.wait_for_function('Number.isFinite(document.querySelector("audio").duration)')
            audio=page.locator('audio');audio.evaluate('e=>e.currentTime=12')
            for seconds,expected in ((5,17),(-10,7),(-10,0),(10,10)):
                browser.command({'action':'media_seek','seconds':seconds,'site':'youtube'})
                self.assertAlmostEqual(audio.evaluate('e=>e.currentTime'),expected,delta=.1)
            for _ in range(2):browser.command({'action':'media_pause'})
            self.assertTrue(audio.evaluate('e=>e.paused'))
            browser.command({'action':'media_play'});browser.command({'action':'media_play'})
            self.assertFalse(audio.evaluate('e=>e.paused'))
            browser.command({'action':'media_pause'})
            for op in ('media_next','media_previous'):browser.command({'action':op,'site':'youtube'})
            self.assertEqual(page.locator('body').get_attribute('data-next'),'1')
            self.assertEqual(page.locator('body').get_attribute('data-prev'),'1')
        finally:browser.close()


class EdgeDomMediaTests(RealDomMediaTests):
    channel='msedge'


if __name__=='__main__':unittest.main()

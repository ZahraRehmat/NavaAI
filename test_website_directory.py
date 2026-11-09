import unittest,json,time
from unittest.mock import patch,Mock
from urllib.parse import urlsplit
from website_directory import directory,spoken_domain
from routing import website_intent,browser_channel
from agent import Agent
from test_existing_browser import CHROME


class WebsiteDirectoryTests(unittest.TestCase):
    def test_ten_thousand_domains_and_offline_cached_lookup(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('Lookup must stay offline')):
            d=directory();self.assertGreaterEqual(len(d.domains),10000)
            self.assertIs(d,directory())
            for _,domain in d.domains:self.assertIsNotNone(d.lookup(domain,allow_reserved=True),domain)

    def test_common_websites_both_browser_channels_and_spoken_domains(self):
        cases=[('open wikipedia','wikipedia.org','chrome'),('open stack overflow on edge','stackoverflow.com','msedge'),
               ('open you tube dot com in chrome','youtube.com','chrome'),('open google meet on edge','meet.google.com','msedge'),
               ('visit git hub website on chrome','github.com','chrome'),('open wikpedia website','wikipedia.org','chrome'),
               ('open linked in on edge','www.linkedin.com','msedge'),('open bbc news','www.bbc.com','chrome')]
        for task,host,channel in cases:
            route=website_intent(task)
            self.assertIsNotNone(route,task);self.assertEqual(route['channel'],channel,task)
            self.assertEqual(urlsplit(route['url']).hostname.removeprefix('www.'),host.removeprefix('www.'),task)
        self.assertEqual(spoken_domain('google dot co dot uk'),'google.co.uk')

    def test_documents_and_plain_reserved_targets_keep_existing_routes(self):
        for task in ('open README.md','open photo.png','open FYP folder','open current','open screenshots','open tab','open Word','open C:\\google.com'):
            self.assertIsNone(website_intent(task),task)
        self.assertIsNone(website_intent('open a completely invented website named gobbledygook'))
        self.assertIsNotNone(website_intent('open wikipedia website.'))

    def test_known_websites_bypass_grid_mouse_matching(self):
        from grid_input import keyboard_command
        self.assertTrue(keyboard_command('open wikipedia on edge'))
        self.assertTrue(keyboard_command('open stack overflow'))
        self.assertFalse(keyboard_command('open AF'))

    def test_unicode_edge_title_is_recognized(self):
        self.assertEqual(browser_channel({'title':'New tab - Microsoft\u200b Edge'}),'msedge')

    def test_named_site_uses_existing_other_browser_window(self):
        edge=dict(CHROME,hwnd=45,title='New tab - Microsoft\u200b Edge',process='msedge')
        agent=Agent(log=lambda _:None)
        try:
            agent.interaction=CHROME
            with patch('window_commands.running_windows',return_value=[edge]),patch('native_browser.navigate_window',return_value='OK') as navigate,patch.object(agent.browser,'open',side_effect=AssertionError('Reuse existing Edge')):
                result=agent._navigate_browser(website_intent('open wikipedia on edge'),False)
                self.assertEqual(result,'OK');self.assertEqual(navigate.call_args.args[0],edge)
        finally:agent.close()

    def test_agent_routes_known_sites_before_local_file_search_and_no_qwen(self):
        agent=Agent(log=lambda _:None)
        try:
            with patch.object(agent.catalog,'resolve',side_effect=ValueError('No installed app')),patch.object(agent,'_navigate_browser',return_value='Opened website') as navigate,patch('file_control.open_requested_file',side_effect=AssertionError('Website must not become a file')),patch('planner.Planner',side_effect=AssertionError('No Qwen')):
                self.assertEqual(agent.run('open stack overflow on edge',interaction=CHROME),'Opened website')
                self.assertEqual(navigate.call_args.args[0]['url'],'https://stackoverflow.com/')
        finally:agent.close()

    def test_website_words_and_commands_are_in_voice_vocabulary(self):
        from vosk_speech import vocabulary
        model=Mock();model.vosk_model_find_word.return_value=1
        words=vocabulary({},model)
        for name in ('wikipedia','youtube','dot','open you tube on edge','open google meet on chrome'):
            self.assertIn(name,words)

    def test_explicit_browser_website_request_precedes_fuzzy_app_matching(self):
        agent=Agent(log=lambda _:None)
        try:
            with patch.object(agent.catalog,'resolve',side_effect=AssertionError('Explicit website must bypass app resolution')),patch.object(agent,'_navigate_browser',return_value='Website opened'):
                self.assertEqual(agent.run('open instagram on edge',interaction=CHROME),'Website opened')
        finally:agent.close()

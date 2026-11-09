import unittest
from catalog import Catalog,ALIASES
from window_commands import intent,match_window
from command_voice import CommandVoice
from app_identity import alias_value


def directory():
    c=Catalog.__new__(Catalog);c.aliases=dict(ALIASES)
    c.entries=[{'name':'ChatGPT','kind':'app','target':'OpenAI.Test!ChatGPT'},
               {'name':'WhatsApp','kind':'app','target':'Whats.Test!App'},
               {'name':'Microsoft SQL Server Management Studio','kind':'exe','target':r'C:\Test\Ssms.exe'},
               {'name':'Visual Studio Code','kind':'exe','target':r'C:\Test\Code.exe'}]
    return c


class AppIdentityTests(unittest.TestCase):
    def test_open_and_close_share_spaced_names(self):
        c=directory()
        rows=[dict(hwnd=1,title='ChatGPT',process='ChatGPT'),dict(hwnd=2,title='WhatsApp',process='WhatsApp.Root')]
        for query,expected in (('chat gpt',1),('chat g p t',1),('chatgpt',1),('whats app',2),('whatdapp',2),('w h a t s a p p',2)):
            installed=c.resolve(query)
            self.assertEqual(match_window(rows,query,c)['hwnd'],expected)
            self.assertIn(installed['name'].lower(),c.identities(query))

    def test_long_name_can_resolve_executable_even_without_product_title(self):
        c=directory();row=dict(hwnd=1,title='query.sql',process='ssms')
        for query in ('Microsoft SQL Server Management Studio','microsoftsqlservermanagementstudio','SQL Server Management Studio'):
            self.assertEqual(match_window([row],query,c)['hwnd'],1)

    def test_packaged_app_id_can_match_generic_host(self):
        row=dict(hwnd=1,title='Untitled',process='ApplicationFrameHost',app_id='OpenAI.Test!ChatGPT')
        self.assertEqual(match_window([row],'chat g p t',directory())['hwnd'],1)

    def test_multiple_matching_windows_still_need_choice(self):
        rows=[dict(hwnd=n,title='ChatGPT',process='ChatGPT') for n in (1,2)]
        with self.assertRaisesRegex(ValueError,'Several running'):match_window(rows,'chat gpt',directory())

    def test_custom_directory_alias_and_close_phrase(self):
        c=directory();c.aliases['my coding app']='visual studio code'
        target=dict(hwnd=1,title='Untitled',process='Code')
        self.assertEqual(intent('close my coding app',c)['name'],'my coding app')
        self.assertEqual(match_window([target],'my coding app',c)['hwnd'],1)
        self.assertEqual(alias_value('chatgpt',{'chatgpt':'custom','chat gpt':'default'}),'custom')
        session=CommandVoice({'handsfree':True})
        for spoken in ('close chat g p t','quit whats app','close microsoft sql server management studio'):
            result=session.route({'text':spoken,'confidence':1})
            self.assertEqual(result['kind'],'command');self.assertIsNotNone(intent(result['text']))


if __name__=='__main__':unittest.main()

"""App/file collisions and user-style names; no app launches or desktop input."""
import unittest
from unittest.mock import Mock,patch
from catalog import Catalog,launch_request,AmbiguousApp,ALIASES
from agent import Agent

def fixture():
    catalog=Catalog.__new__(Catalog);catalog.aliases=dict(ALIASES)
    catalog.entries=[{'name':n,'kind':'exe','target':n+'.exe'} for n in ('Word','Excel','PowerPoint','Google Chrome','Microsoft Store','Visual Studio Code','Visual Studio 2026','WhatsApp','Steam','Task Manager','File Explorer')]
    return catalog

class AppLaunchPriority(unittest.TestCase):
    def test_nicknames_and_typing_errors(self):
        c=fixture()
        for query,wanted in [('microsoft word','Word'),('ms excel','Excel'),('power point','PowerPoint'),('ppt','PowerPoint'),('whats app','WhatsApp'),('steem','Steam'),('task manger','Task Manager'),('vs studio','Visual Studio 2026'),('vs code','Visual Studio Code'),('microsof word','Word'),('browser','Google Chrome')]:
            with self.subTest(query=query):self.assertEqual(c.resolve(query)['name'],wanted)
    def test_launch_phrase(self):
        for phrase in ('open the Word app','launch application Word','start Word.exe','open "Word"'):
            self.assertEqual(launch_request(phrase),'Word')
        self.assertEqual(launch_request('open file explorer'),'file explorer')
        self.assertEqual(launch_request('open whats app'),'whats app')
        for phrase in ('open Word.pdf','open Word folder','open folder Word','open file Word','open C:\\data\\Word','open this app','open the first folder'):
            with self.subTest(phrase=phrase):self.assertIsNone(launch_request(phrase))
    def test_app_wins_before_file_dictionary(self):
        a=Agent(log=lambda _:None);a.catalog=fixture();a.dispatch=Mock(return_value='Launch requested for Word')
        with patch('file_control.open_requested_file',side_effect=AssertionError('File matcher must not intercept a known app')),patch('planner.Planner',side_effect=AssertionError('No model')):
            self.assertEqual(a.run('open microsoft word'),'Launch requested for Word')
        a.dispatch.assert_called_once_with({'action':'open_app','name':'microsoft word'},False)
    def test_explicit_file_keeps_file_route(self):
        a=Agent(log=lambda _:None);a.catalog=fixture();a.dispatch=Mock(side_effect=AssertionError('Must not launch Word'))
        with patch('file_control.open_requested_file',return_value='Opened Word.pdf') as files:
            self.assertEqual(a.run('open Word.pdf'),'Opened Word.pdf')
        files.assert_called_once()
    def test_browser_alias_uses_managed_browser(self):
        a=Agent(log=lambda _:None);a.catalog=fixture();a.dispatch=Mock(return_value='chrome ready')
        with patch('file_control.open_requested_file',side_effect=AssertionError('No file matcher')):a.run('open google browser')
        a.dispatch.assert_called_once_with({'action':'open_browser','channel':'chrome'},False)
    def test_ambiguous_app_does_not_launch_or_open_file(self):
        a=Agent(log=lambda _:None);a.catalog=fixture();a.catalog.entries.extend([{'name':n,'kind':'exe','target':n} for n in ('Android Studio','OBS Studio')]);a.dispatch=Mock()
        with patch('file_control.open_requested_file',side_effect=AssertionError('No file fallback')):
            self.assertIn('Ambiguous app',a.run('open studio'))
        a.dispatch.assert_not_called()
    def test_visual_studio_is_not_code_when_ide_absent(self):
        c=fixture();c.entries=[e for e in c.entries if e['name']!='Visual Studio 2026']
        with self.assertRaises(ValueError):c.resolve('vs studio')

if __name__=='__main__':unittest.main()

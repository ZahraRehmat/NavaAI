import unittest
from unittest.mock import patch
from startup import startup_voice_config,expected
from command_voice import CommandVoice
from app_runtime import SingleInstance

class StartupWakeTests(unittest.TestCase):
    def test_sign_in_recovers_from_previous_voice_off_without_changing_device(self):
        original={'enabled':False,'assistant_active':False,'handsfree':True,'device':7,'minimum_confidence':.83}
        config=startup_voice_config(original)
        self.assertFalse(original['enabled'])
        self.assertTrue(config['enabled']);self.assertTrue(config['start_hidden'])
        self.assertEqual(config['device'],7);self.assertEqual(config['minimum_confidence'],.83)
        session=CommandVoice(config)
        self.assertTrue(session.active);self.assertFalse(session.handsfree)
        self.assertEqual(session.route({'text':'open Word','confidence':1})['kind'],'ignore')
        self.assertEqual(session.route({'text':'Nava listen','confidence':1})['control'],'handsfree')
        self.assertEqual(session.route({'text':'open Word','confidence':1})['kind'],'command')
    def test_shortcut_uses_startup_mode(self):
        self.assertTrue(expected()['arguments'].endswith('nava.py" --startup'))
        self.assertTrue(expected()['target'].endswith('pythonw.exe'))
    def test_duplicate_sign_in_launch_never_shows_panel(self):
        with patch('win32api.GetLastError',return_value=183),patch('win32event.CreateMutex'),patch('win32event.CreateEvent'),patch('win32event.SetEvent') as show:
            instance=SingleInstance(show_existing=False)
            self.assertFalse(instance.owner);show.assert_not_called()
            SingleInstance();show.assert_called_once()

if __name__=='__main__':unittest.main()

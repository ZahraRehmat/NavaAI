import tempfile,unittest
from pathlib import Path
from command_voice import CommandVoice
from folder_control import resolve_folder
from smart_grid import AdaptiveGrid
from grid_test_support import FakeMouse


class FailedRunRepairs(unittest.TestCase):
    def test_unobserved_app_and_explicit_folder_return_to_agent_with_grid_on(self):
        grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[])
        try:
            for enable in ('gwen grid','gwen full grid'):
                grid.run(enable)
                for task in ('open chat g p t','open gwen three folder','open FYP','search youtube','make E5 bold'):
                    self.assertIsNone(grid.run(task),task);self.assertTrue(grid.active)
        finally:grid.close()

    def test_number_word_folder_and_desktop_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'Desktop';root.mkdir()
            target=root/'gwen 3';target.mkdir()
            self.assertEqual(resolve_folder('gwen three',[root]),target)
            self.assertEqual(resolve_folder('gwen3',[root]),target)
            self.assertEqual(resolve_folder('Desktop',[root]),root)
            other=root/'reports by agent B';other.mkdir()
            self.assertEqual(resolve_folder('reports by agent bee',[root],chooser=lambda *_:0),other)

    def test_type_enters_dictation_and_text_is_literal_until_explicit_stop(self):
        session=CommandVoice({'handsfree':True})
        self.assertEqual(session.route({'text':'type','confidence':1})['control'],'dictation_on')
        self.assertTrue(session.dictating)
        for text in ('hello world','new mail','close word','yes'):
            result=session.route({'text':text,'confidence':1})
            self.assertEqual(result['text'],'type '+text);self.assertEqual(result['kind'],'command')
        self.assertEqual(session.route({'text':'stop dictation','confidence':1})['control'],'dictation_off')
        self.assertFalse(session.dictating)
        self.assertEqual(session.route({'text':'close word','confidence':1})['text'],'close word')

    def test_busy_dictation_is_marked_for_the_target_bound_queue(self):
        session=CommandVoice({'handsfree':True});session.dictating=True
        result=session.route({'text':'hello','confidence':1},{'busy':True})
        self.assertEqual(result['kind'],'command');self.assertTrue(result['dictation_input'])
        self.assertEqual(session.route({'text':'stop','confidence':1})['control'],'stop')
        self.assertFalse(session.dictating)

    def test_wake_once_can_start_dictation_without_continuous_commands(self):
        session=CommandVoice({'handsfree':False})
        self.assertEqual(session.route({'text':'Gwen type','confidence':1})['control'],'dictation_on')
        self.assertEqual(session.route({'text':'hello world','confidence':1})['text'],'type hello world')
        self.assertEqual(session.route({'text':'stop dictation','confidence':1})['control'],'dictation_off')
        self.assertFalse(session.handsfree)


if __name__=='__main__':unittest.main()

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from project_state import SessionStore, read_backend_info
from workbench_ui import NavaAIWindow
from target_policy import select_request_target


class TargetTests(unittest.TestCase):
    def test_selected_window_survives_foreground_change(self):
        selected = {'hwnd': 1, 'pid': 20}
        underneath = {'hwnd': 2, 'pid': 30}
        self.assertEqual(select_request_target(selected, underneath, False, lambda x: True, lambda x: True), selected)

    def test_app_launch_and_grid_ignore_old_window(self):
        self.assertIsNone(select_request_target({'hwnd': -1}, None, True, lambda x: False, lambda x: False))

    def test_closed_selected_window_does_not_fall_back_to_another_app(self):
        with self.assertRaisesRegex(ValueError, 'no action was sent'):
            select_request_target({'hwnd': -1}, {'hwnd': 2}, False, lambda x: True, lambda x: x['hwnd'] == 2)


class StorageTests(unittest.TestCase):
    def test_complete_transcript_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sessions.json'
            store = SessionStore(path)
            session = store.new()
            store.add(session, 'You', 'اردو and English')
            store.add(session, 'NavaAI', 'Backend result')
            restored = SessionStore(path).sessions[0]
            self.assertEqual(restored['messages'][1]['text'], 'Backend result')
            self.assertEqual(restored['title'], 'اردو and English')
            self.assertIn('time', restored['messages'][0])

    def test_corrupt_history_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sessions.json'
            path.write_text('broken', encoding='utf-8')
            store = SessionStore(path)
            with self.assertRaises(OSError):
                store.add(store.new(), 'You', 'test')
            self.assertEqual(path.read_text(), 'broken')

    def test_runtime_info_reads_evidence_without_interpreting_as_training(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.json').write_text(json.dumps({'model': 'models/test', 'device': 'GPU'}))
            (root / 'TESTING.md').write_text('Historical report')
            info = read_backend_info(root)
            self.assertFalse(info['model_exists'])
            self.assertEqual(info['reports'], ['TESTING.md'])


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = NavaAIWindow(connect=False, store=SessionStore(Path(self.temp.name) / 'sessions.json'))
        self.sent = []
        self.window.write = lambda **message: self.sent.append(message)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_no_execution_until_connected(self):
        self.window.input.setText('type hello')
        self.window.send_message()
        self.assertEqual(self.sent, [])

    def test_command_is_sent_once_and_ui_hides_until_result(self):
        self.window.ready = True
        self.window.show()
        self.window.input.setText('open store')
        self.window.send_message()
        self.window.input.setText('second command')
        self.window.send_message()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]['text'], 'open store')
        self.assertFalse(self.window.isVisible())
        self.assertTrue(self.window.busy)
        self.window.on_event({'kind': 'result', 'message': 'Launch requested; inspect app'})
        self.assertFalse(self.window.busy)
        self.assertTrue(self.window.isVisible())
        self.assertIn('check the result', self.window.phase.text())
        self.assertEqual(self.window.session['messages'][-1]['text'], 'Launch requested; inspect app')

    def test_stop_does_not_allow_a_second_task_before_backend_returns(self):
        self.window.ready = self.window.busy = True
        self.window.stop_task()
        self.assertTrue(self.window.busy)
        self.assertEqual(self.sent[-1], {'op': 'stop'})

    def test_disconnect_records_uncertain_outcome(self):
        self.window.busy = True
        self.window.backend_finished()
        self.assertFalse(self.window.ready)
        self.assertIn('Inspect the target app', self.window.session['messages'][-1]['text'])

    def test_history_renders_user_text_as_plain_text(self):
        self.window.add_message('You', '<b>literal command</b>')
        self.window.refresh_history()
        self.window.show_history(0)
        self.assertIn('<b>literal command</b>', self.window.history_text.toPlainText())

    def test_chosen_window_is_not_overwritten_by_focus_events(self):
        self.window.target = {'hwnd': 10, 'title': 'Chosen document'}
        self.window.target_locked = True
        self.window.on_event({'kind': 'target', 'target': {'hwnd': 20, 'title': 'Other app'}})
        self.assertEqual(self.window.target['hwnd'], 10)
        self.window.use_recent_window()
        self.assertEqual(self.window.target['hwnd'], 20)


if __name__ == '__main__':
    unittest.main()

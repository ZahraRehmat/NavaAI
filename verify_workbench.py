"""Real Qt-to-Gwen IPC smoke check. No model inference or physical input."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from project_state import SessionStore
from workbench_ui import NavaAIWindow


def main():
    launch_store = '--launch-store' in sys.argv
    app = QApplication([])
    temporary = tempfile.TemporaryDirectory()
    window = NavaAIWindow(connect=False, store=SessionStore(Path(temporary.name) / 'sessions.json'))
    events = []
    handler = window.on_event
    phase = 'connecting'
    started = time.monotonic()
    outcome = {'passed': False, 'checks': []}

    def receive(event):
        nonlocal phase
        events.append(event['kind'])
        if event['kind'] == 'windows':
            assert all(w['pid'] != os.getpid() for w in event['windows'])
            assert all(w['hwnd'] for w in event['windows'])
            outcome['checks'].append('Window chooser lists external windows and excludes Nava')
            phase = 'apps'
            window.input.setText('/apps'); window.send_message()
            return
        handler(event)
        if event['kind'] == 'fatal':
            outcome['error'] = event['message']; window.close()
        elif event['kind'] == 'ready':
            outcome['checks'].append('Real runtime connected with voice off')
            outcome['model'] = event['model']
            phase = 'windows'
            window.write(op='windows')
        elif event['kind'] == 'result' and phase == 'apps':
            assert 'Chrome' in event['message'] or 'Microsoft' in event['message'], event['message']
            outcome['checks'].append('App catalog returned through persistent IPC')
            if launch_store:
                phase = 'store'
                window.target = {'hwnd': -1, 'pid': 0}
                window.input.setText('open store'); window.send_message()
                return
            phase = 'reset'
            window.input.setText('/reset'); window.send_message()
        elif event['kind'] == 'result' and phase == 'store':
            assert not event.get('error') and 'Microsoft Store' in event['message'], event['message']
            outcome['checks'].append('Store launch request bypassed a stale target')
            window.target = None
            phase = 'reset'
            window.input.setText('/reset'); window.send_message()
        elif event['kind'] == 'result' and phase == 'reset':
            assert event['message'] == 'Conversation context cleared.', event['message']
            assert len(window.session['messages']) == (6 if launch_store else 4)
            restored = SessionStore(window.store.path)
            assert len(restored.sessions[0]['messages']) == (6 if launch_store else 4)
            outcome['checks'].extend(['Second turn reused the runtime', 'Complete transcript persisted', 'Clean shutdown requested'])
            outcome['passed'] = True
            window.close()

    window.on_event = receive
    def timeout():
        if time.monotonic() - started > 45:
            outcome['error'] = 'Integration deadline exceeded'; window.close()
    timer = QTimer()
    timer.timeout.connect(timeout); timer.start(500)
    window.connect_backend()
    app.exec()
    outcome['events'] = events
    outcome['seconds'] = round(time.monotonic() - started, 2)
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    temporary.cleanup()
    return 0 if outcome['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

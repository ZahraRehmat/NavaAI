"""Exercise the real bridge's typing route against a disposable Tk fixture only."""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fixture(path):
    import tkinter as tk
    import ctypes
    from ctypes import wintypes
    root = tk.Tk()
    root.title('NavaAI disposable input fixture')
    root.geometry('650x180+60+80')
    root.attributes('-topmost', True)
    tk.Label(root, text='NavaAI integration test · disposable text only').pack(pady=15)
    entry = tk.Entry(root, width=65)
    entry.pack(padx=20, pady=15)
    entry.focus_set()
    def focus_request():
        root.lift(); root.focus_force(); entry.focus_set()
    root.after(250, focus_request)
    def publish():
        if path.with_suffix('.stop').exists():
            root.destroy(); return
        if path.with_suffix('.focus').exists():
            path.with_suffix('.focus').unlink()
            focus_request()
        user = ctypes.windll.user32
        user.GetParent.argtypes = [wintypes.HWND]
        user.GetParent.restype = wintypes.HWND
        hwnd = user.GetParent(root.winfo_id()) or root.winfo_id()
        target = dict(hwnd=hwnd, pid=os.getpid(), title=root.title(), class_name='TkTopLevel',
                      bounds=[root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height()],
                      pointer=[entry.winfo_rootx()+10, entry.winfo_rooty()+10])
        path.write_text(json.dumps({'text': entry.get(), 'target': target}), encoding='utf-8')
        root.after(100, publish)
    root.after(400, publish)
    root.mainloop()


def main():
    from project_state import discover_backend
    backend = Path(discover_backend())
    result = {'passed': False, 'checks': []}
    stage = 'fixture startup'
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'fixture.json'
        test_window = subprocess.Popen([sys.executable, str(Path(__file__)), '--fixture', str(path)], creationflags=subprocess.CREATE_NO_WINDOW)
        bridge = None
        try:
            deadline = time.monotonic() + 10
            while not path.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            assert path.exists(), 'Fixture did not start'
            bridge = subprocess.Popen([str(backend / '.venv/Scripts/python.exe'), '-u', str(ROOT / 'backend_bridge.py'),
                                       '--backend', str(backend), '--frontend-pid', str(os.getpid()), '--diagnostic'],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
            events = queue.Queue()
            def read():
                for line in bridge.stdout:
                    events.put(json.loads(line))
            threading.Thread(target=read, daemon=True).start()
            errors = []
            threading.Thread(target=lambda: errors.append(bridge.stderr.read()), daemon=True).start()
            def send(**data):
                bridge.stdin.write(json.dumps(data) + '\n'); bridge.stdin.flush()
            observed_target = None
            def wait(kind, timeout=20):
                nonlocal observed_target
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    event = events.get(timeout=max(.1, deadline-time.monotonic()))
                    if event['kind'] == 'target':
                        observed_target = event['target']
                    if event['kind'] == 'fatal':
                        raise AssertionError(event['message'])
                    if event['kind'] == kind:
                        return event
                raise TimeoutError(kind)
            stage = 'backend startup'
            wait('ready')
            stage = 'fixture focus'
            path.with_suffix('.focus').touch()
            target = json.loads(path.read_text(encoding='utf-8'))['target']
            assert target, 'Fixture did not receive focus; no input sent'
            stage = 'changed-target guard'
            send(op='run', text='type must not execute', background=False, expected_target=dict(target, hwnd=-1))
            refused = wait('result')
            assert refused.get('error') and 'no action was sent' in refused['message'], refused
            assert json.loads(path.read_text(encoding='utf-8'))['text'] == ''
            result['checks'].append('Unavailable selected window was refused before any input')
            send(op='run', text='/apps', expected_target=dict(target, hwnd=-1))
            catalog_result = wait('result')
            assert not catalog_result.get('error') and 'Microsoft' in catalog_result['message']
            result['checks'].append('App list works even when the old selected window is unavailable')
            stage = 'typing'
            send(op='run', text='type NavaAI integration check', background=False, expected_target=target)
            event = wait('result')
            assert not event.get('error'), event
            deadline = time.monotonic() + 3
            actual = ''
            while time.monotonic() < deadline:
                try:
                    actual = json.loads(path.read_text(encoding='utf-8'))['text']
                except (ValueError, OSError):
                    pass
                if actual == 'NavaAI integration check':
                    break
                time.sleep(.1)
            assert actual == 'NavaAI integration check', (actual, event)
            result['checks'].append('Real Unicode typing reached only the selected disposable fixture')
            stage = 'full grid'
            send(op='run', text='Gwen full grid', background=False, expected_target=dict(target, hwnd=-1))
            event = wait('result')
            assert event.get('grid'), event
            result['checks'].append('Full grid starts despite a stale selected window')
            stage = 'reset during grid'
            send(op='run', text='/reset')
            event = wait('result')
            assert not event['grid'] and event['message'] == 'Conversation context cleared.', event
            result['checks'].append('New conversation resets context and exits grid')
            send(op='run', text='Gwen full grid', background=False, expected_target=target)
            event = wait('result')
            assert event.get('grid'), event
            send(op='stop')
            wait('stopping')
            event = wait('grid')
            assert not event['active'], event
            result['checks'].append('Stop disabled the grid and released held buttons')
            send(op='quit')
            bridge.wait(timeout=12)
            assert bridge.returncode == 0
            result['checks'].append('Backend exited cleanly')
            result['passed'] = True
        except Exception as exc:
            result['error'] = stage + ': ' + (str(exc) or type(exc).__name__)
        finally:
            if bridge and bridge.poll() is None:
                try:
                    bridge.stdin.write('{"op":"quit"}\n'); bridge.stdin.flush()
                    bridge.wait(timeout=12)
                except Exception:
                    bridge.kill(); bridge.wait()
            if not result['passed'] and bridge:
                result['diagnostic'] = ''.join(errors)
            path.with_suffix('.stop').touch()
            try:
                test_window.wait(timeout=4)
            except subprocess.TimeoutExpired:
                test_window.terminate(); test_window.wait()
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    if '--fixture' in sys.argv:
        fixture(Path(sys.argv[-1]))
    else:
        sys.exit(main())

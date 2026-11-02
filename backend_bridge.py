"""JSON-lines adapter for the existing Gwen Doer runtime; voice stays off.

Run with Gwen's Python so its OpenVINO, browser and Windows dependencies remain
isolated from the Qt frontend. Tk owns the original grid/choice overlays.
"""
import argparse
import faulthandler
import json
import os
import queue
import sys
import threading
import traceback
from pathlib import Path


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', required=True)
    parser.add_argument('--frontend-pid', type=int, required=True)
    parser.add_argument('--diagnostic', action='store_true')
    args = parser.parse_args()
    root_path = Path(args.backend).resolve()
    sys.path.insert(0, str(root_path))
    os.chdir(root_path)
    protocol = sys.stdout
    sys.stdout = sys.stderr  # Third-party prints cannot corrupt the protocol.
    output_lock = threading.Lock()

    def emit(kind, **data):
        with output_lock:
            protocol.write(json.dumps(dict(kind=kind, **data), ensure_ascii=False, default=str) + '\n')
            protocol.flush()

    try:
        from grid_display import enable_dpi_awareness
        enable_dpi_awareness()
        from app_runtime import SingleInstance
        instance = SingleInstance()
        if not instance.owner:
            emit('fatal', message='Gwen Doer is already running. Quit its existing panel, then reconnect here.')
            instance.close()
            return
        import tkinter as tk
        import windows_api as win
        from agent import Agent
        # Load native image/input DLLs on the main thread before Tk starts.
        # NumPy/OpenCV initialization from a worker can block behind Tk on Windows.
        import desktop_control
        from grid_overlay import GridOverlay
        from grid_mouse import GridMouse
        from smart_grid import AdaptiveGrid, AccessibleTargets, check_target
        from grid_display import monitors
        from grid_commands import parse as parse_grid
        from target_policy import independent_request, select_request_target
        root = tk.Tk()
        root.withdraw()
        events = queue.Queue()
        work = queue.Queue()
        replies = queue.Queue()
        stop = threading.Event()
        closing = threading.Event()
        last_target = None
        busy = False
        overlay = GridOverlay(root)
        key_down = False

        # Also exclude Qt's whole process from backend fallback target selection.
        original_usable = win.usable_target
        win.usable_target = lambda ctx: bool(ctx and ctx.get('pid') != args.frontend_pid and original_usable(ctx))

        def ask(kind, **payload):
            while not replies.empty():
                replies.get_nowait()
            emit(kind, **payload)
            while not stop.is_set() and not closing.is_set():
                try:
                    return replies.get(timeout=.1)
                except queue.Empty:
                    pass
            return False

        def choose(query, options, preview=None):
            answer = queue.Queue()
            events.put(('choose', (query, options, preview, answer)))
            while not stop.is_set() and not closing.is_set():
                try:
                    return answer.get(timeout=.1)
                except queue.Empty:
                    pass
            return None

        grid = AdaptiveGrid(GridMouse(), monitors, render=lambda picture: events.put(('grid', picture)),
                            stop=stop, observer=AccessibleTargets(lambda: last_target),
                            target_check=check_target, chooser=choose)

        def halt():
            stop.set()
            grid.emergency_stop()
            emit('stopping', message='Stop requested. Held mouse buttons released; waiting for the backend to return.')

        def read_input():
            try:
                for line in sys.stdin:
                    try:
                        message = json.loads(line)
                        if message.get('op') == 'stop':
                            halt()
                        elif message.get('op') == 'reply':
                            replies.put(message.get('value', False))
                        elif message.get('op') == 'quit':
                            halt(); closing.set(); work.put(None); return
                        else:
                            events.put(('request', message))
                    except Exception as exc:
                        emit('log', message='Invalid frontend request: ' + str(exc))
            finally:
                stop.set(); closing.set(); work.put(None)

        def worker():
            agent = None
            try:
                agent = Agent(log=lambda text: emit('log', message=str(text)),
                              confirm=lambda message: bool(ask('confirm', message=message)), stop=stop, choose=choose)
                # Forward original evidence without inventing verification stages.
                record = agent.record
                def record_event(data):
                    record(data)
                    emit('evidence', data=data)
                agent.record = record_event
                config = agent.config
                model = root_path / config['model']
                emit('ready', backend=str(root_path), model=str(model), model_exists=model.is_dir(),
                     device=config.get('device'), apps=len(agent.catalog.entries), logfile=str(agent.logfile), pid=os.getpid())
                while True:
                    request = work.get()
                    if request is None:
                        break
                    try:
                        if args.diagnostic:
                            faulthandler.dump_traceback_later(10)
                        task = request['text']
                        independent = independent_request(task, agent.catalog, grid.active)
                        target = select_request_target(request.get('expected_target'), request.get('target'), independent,
                                                       win.usable_target, win.target_alive)
                        if independent and grid.active and (task.startswith('/') or parse_grid(task, True) is None):
                            grid.emergency_stop()
                        if task == '/reset':
                            grid.emergency_stop()
                            agent.context = []
                            result = 'Conversation context cleared.'
                        elif task.startswith('/'):
                            result = None
                        else:
                            result = grid.run(task)
                        if result is not None:
                            if task != '/reset':
                                agent.record({'manual_grid': task, 'result': result, 'active': grid.active})
                        elif task == '/apps':
                            result = '\n'.join(sorted({entry['name'] for entry in agent.catalog.entries}))
                        elif task.startswith('/office'):
                            from office_catalog import summary, search_controls
                            from office_control import office_kind
                            from office_language import tools_for
                            kind = office_kind(request.get('expected_target') or request.get('target')) or 'word'
                            query = task[len('/office'):].strip().removeprefix('search ')
                            result = ('\n'.join(c['id'] + ' (' + c['type'] + ')' for c in search_controls(kind, query))
                                      if query else 'Native ' + kind + ' tools: ' + ', '.join(tools_for(kind)) + '\n' + str(summary()))
                        else:
                            if independent and grid.active:
                                grid.emergency_stop()
                            result = agent.run(task, request.get('background', False), interaction=target)
                        response = dict(message=result or 'Backend returned without a result. Inspect the target application.',
                                        stopped=stop.is_set(), grid=grid.active, logfile=str(agent.logfile))
                    except Exception as exc:
                        agent.record({'bridge_error': traceback.format_exc()})
                        response = dict(message='Task failed: ' + str(exc), error=True, stopped=stop.is_set(), grid=grid.active)
                    finally:
                        if args.diagnostic:
                            faulthandler.cancel_dump_traceback_later()
                        events.put(('finished', response))
            except Exception:
                emit('fatal', message=traceback.format_exc())
            finally:
                if agent:
                    agent.close()
                events.put(('closed', None))

        def poll():
            nonlocal last_target, busy, key_down
            current = win.snapshot()
            if win.usable_target(current) and win.target_alive(current):
                if not last_target or (current['hwnd'], current['title']) != (last_target['hwnd'], last_target['title']):
                    emit('target', target=current)
                last_target = current
            down = bool(win.user.GetAsyncKeyState(0x77) & 0x8000)
            if down and not key_down:
                halt()
            key_down = down
            try:
                while True:
                    kind, value = events.get_nowait()
                    if kind == 'grid':
                        overlay.draw(value)
                        emit('grid', active=value['active'], mode=value.get('mode'), count=value.get('count', 0), error=value.get('error', ''))
                    elif kind == 'choose':
                        from choice_ui import TargetChooser
                        query, options, preview, answer = value
                        emit('choosing', message='Choose the matching target in the lettered popup: ' + query)
                        TargetChooser(root, query, options, answer.put, stop, preview)
                    elif kind == 'request':
                        if value.get('op') == 'windows':
                            windows = []
                            @win.ENUM
                            def collect(hwnd, unused):
                                try:
                                    import ctypes
                                    from ctypes import wintypes
                                    pid = wintypes.DWORD()
                                    win.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                                    name = ctypes.create_unicode_buffer(256)
                                    win.user.GetClassNameW(hwnd, name, len(name))
                                    item = dict(hwnd=hwnd, pid=pid.value, title=win.title(hwnd), class_name=name.value,
                                                bounds=win.rect(hwnd), pointer=win.cursor())
                                    if win.usable_target(item) and win.target_alive(item):
                                        windows.append(item)
                                except (OSError, ValueError):
                                    pass
                                return True
                            win.user.EnumWindows(collect, 0)
                            emit('windows', windows=windows)
                        if value.get('op') == 'run' and not busy and not closing.is_set():
                            # Freeze the selected identity. Hiding Qt may reveal a different
                            # window; that is not a user request to change the target.
                            target = win.choose_target(current, [last_target])
                            busy = True; stop.clear()
                            work.put(dict(value, target=target))
                    elif kind == 'finished':
                        busy = False
                        emit('result', **value)
                    elif kind == 'closed':
                        grid.close(); overlay.close(); root.destroy(); return
            except queue.Empty:
                pass
            root.after(80, poll)

        threading.Thread(target=read_input, daemon=True).start()
        threading.Thread(target=worker, daemon=True).start()
        poll()
        root.mainloop()
        instance.close()
    except Exception:
        emit('fatal', message=traceback.format_exc())


if __name__ == '__main__':
    main()

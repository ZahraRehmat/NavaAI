"""Local session storage and discovery. No model training is implied by reports."""
import json
import os
from datetime import datetime
from pathlib import Path


def backend_candidates():
    home = Path.home()
    return [home / 'OneDrive' / 'Desktop' / 'Gwen doer', home / 'Desktop' / 'Gwen doer']


def discover_backend():
    return next((str(p) for p in backend_candidates() if (p / 'agent.py').is_file()), '')


class SessionStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'NavaAI' / 'workbench_sessions.json'
        self.sessions = []
        self.error = ''
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, list) or any(not isinstance(s, dict) or not isinstance(s.get('messages'), list) for s in data):
                    raise ValueError('Invalid session format')
                self.sessions = data
            except (ValueError, OSError) as exc:
                # Do not overwrite an unreadable file with an empty session.
                self.error = str(exc)

    def save(self):
        if self.error:
            raise OSError('Existing history could not be read: ' + self.error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.sessions, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def new(self):
        session = {'created': datetime.now().astimezone().isoformat(timespec='seconds'), 'title': 'New conversation', 'messages': []}
        self.sessions.append(session)
        return session

    def add(self, session, role, text, **extra):
        session['messages'].append(dict(role=role, text=text, time=datetime.now().astimezone().isoformat(timespec='seconds'), **extra))
        if role == 'You' and session['title'] == 'New conversation':
            session['title'] = text[:65]
        self.save()


def read_backend_info(path):
    root = Path(path)
    config = json.loads((root / 'config.json').read_text(encoding='utf-8-sig'))
    model = root / config['model']
    reports = [name for name in ('TESTING.md', 'DIAGNOSIS.md', 'verification.txt', 'runtime-verification.txt',
                                'voice-verification.json', 'live-input-verification.json', 'CHECKPOINT_VERIFICATION.json')
               if (root / name).is_file()]
    diagnostics = root / 'diagnostics'
    if diagnostics.is_dir():
        reports.extend('diagnostics/' + p.name for p in sorted(diagnostics.glob('*.json')))
    return {'config': config, 'model': str(model), 'model_exists': model.is_dir(), 'reports': reports}

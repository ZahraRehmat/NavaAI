"""One resident GUI process; subsequent launches reveal the existing chat."""
import hashlib
from pathlib import Path

class SingleInstance:
    def __init__(self,key_suffix=''):
        import win32event,win32api,win32con
        key=hashlib.sha256((str(Path(__file__).resolve().parent).lower()+key_suffix).encode()).hexdigest()[:16]
        self.mutex=win32event.CreateMutex(None,False,'Local\\GwenDoer-'+key)
        self.owner=win32api.GetLastError()!=183
        self.show_event=win32event.CreateEvent(None,False,False,'Local\\GwenShow-'+key)
        if not self.owner: win32event.SetEvent(self.show_event)

    def show_requested(self):
        import win32event
        return win32event.WaitForSingleObject(self.show_event,0)==0

    def close(self):
        self.show_event.Close(); self.mutex.Close()

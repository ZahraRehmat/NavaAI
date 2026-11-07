"""Read-only Windows change notifications. Callbacks never inspect UIA or send input."""
import ctypes,threading,time,os
from ctypes import wintypes as w

class ScreenChanges:
    def __init__(self,notify=lambda:None):
        self.notify=notify;self.dirty=set();self.lock=threading.Lock();self.ready=threading.Event();self.thread_id=None
        self.thread=threading.Thread(target=self._pump,daemon=True,name='Smart grid screen events');self.thread.start();self.ready.wait(1)

    def consume(self):
        with self.lock:result=self.dirty;self.dirty=set();return result

    def close(self):
        if self.thread_id:ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x12,0,0)

    def _pump(self):
        u=ctypes.WinDLL('user32');k=ctypes.WinDLL('kernel32')
        callback_type=ctypes.WINFUNCTYPE(None,w.HANDLE,w.DWORD,w.HWND,w.LONG,w.LONG,w.DWORD,w.DWORD)
        u.SetWinEventHook.argtypes=[w.DWORD,w.DWORD,w.HMODULE,callback_type,w.DWORD,w.DWORD,w.DWORD];u.SetWinEventHook.restype=w.HANDLE
        u.UnhookWinEvent.argtypes=[w.HANDLE];u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
        u.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
        self.thread_id=k.GetCurrentThreadId();last_notice=0
        @callback_type
        def changed(hook,event,hwnd,obj,child,thread,timestamp):
            nonlocal last_notice
            if not hwnd or obj==-9:return # Cursor movement is not a changed control.
            pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value in (os.getpid(),os.getppid()):return # Scanner and Gwen overlays/chat.
            root=u.GetAncestor(hwnd,2) or hwnd
            with self.lock:self.dirty.add(int(root))
            now=time.monotonic()
            if now-last_notice>.04:
                last_notice=now
                try:self.notify()
                except Exception:pass
        hooks=[u.SetWinEventHook(a,b,None,changed,0,0,0) for a,b in ((3,3),(6,7),(0x8000,0x800e))]
        self.ready.set();msg=w.MSG()
        while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:u.TranslateMessage(ctypes.byref(msg));u.DispatchMessageW(ctypes.byref(msg))
        for hook in hooks:
            if hook:u.UnhookWinEvent(hook)

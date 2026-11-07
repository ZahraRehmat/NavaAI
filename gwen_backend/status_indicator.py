"""Small passive resident badge. No focus, pointer, or input operations."""
import ctypes
from ctypes import wintypes as w
import tkinter as tk


def indicator_state(*, ready, busy, enabled, microphone, handsfree, armed=False,
                    review=False, error=False, recognizing=False):
    if not ready: return 'Starting', '#94a3b8'
    if busy: return 'Working', '#fbbf24'
    if review: return 'Needs reply', '#fbbf24'
    if enabled and error: return 'Mic error · F10', '#fb7185'
    if not enabled: return 'Voice off · F9', '#94a3b8'
    if not microphone: return 'Mic starting', '#94a3b8'
    if recognizing: return 'Hearing you', '#c4b5fd'
    if handsfree or armed: return 'Listening', '#4ade80'
    return 'Say Gwen listen', '#67e8f9'


class StatusIndicator:
    def __init__(self, root):
        self.window=tk.Toplevel(root); self.window.withdraw()
        self.window.title('Gwen Doer - Status')
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True, '-transparentcolor', '#010203')
        self.canvas=tk.Canvas(self.window,width=184,height=36,bg='#172033',highlightthickness=1,highlightbackground='#475569')
        self.canvas.pack()
        self.dot=self.canvas.create_oval(10,11,24,25,fill='#94a3b8',outline='')
        self.canvas.create_text(33,10,text='GWEN',anchor='w',fill='#e2e8f0',font=('Segoe UI',-10,'bold'))
        self.caption=self.canvas.create_text(33,24,text='Starting',anchor='w',fill='#94a3b8',font=('Segoe UI',-12))
        self.canvas.create_rectangle(167,7,175,29,fill='#334155',outline='')
        self.meter=self.canvas.create_rectangle(167,29,175,29,fill='#4ade80',outline='')
        self.window.update_idletasks()
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.user.GetParent.argtypes=[w.HWND];self.user.GetParent.restype=w.HWND
        self.user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];self.user.GetWindowLongW.restype=w.LONG
        self.user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];self.user.SetWindowLongW.restype=w.LONG
        self.user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        self.user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        self.user.SystemParametersInfoW.argtypes=[w.UINT,w.UINT,ctypes.c_void_p,w.UINT]
        self.hwnd=self.user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        # LAYERED | TRANSPARENT | TOOLWINDOW | NOACTIVATE, just like the cursor halo.
        self.user.SetWindowLongW(self.hwnd,-20,self.user.GetWindowLongW(self.hwnd,-20)|0x080800a0)
        self.user.SetWindowDisplayAffinity.argtypes=[w.HWND,w.DWORD]
        self.user.SetWindowDisplayAffinity(self.hwnd,0x11)
        self.last=None;self.position=None
        # Tk deiconify may activate a newly mapped window despite NOACTIVATE.
        self.user.ShowWindow(self.hwnd,4)  # SW_SHOWNOACTIVATE
        self.update(('Starting','#94a3b8'))

    def update(self, state, level=0):
        import math
        amount=max(0,min(1,(20*math.log10(max(float(level),1e-6))+65)/45))
        self.canvas.coords(self.meter,167,29-round(22*amount),175,29)
        if state!=self.last:
            text,color=state
            self.canvas.itemconfigure(self.dot,fill=color)
            self.canvas.itemconfigure(self.caption,text=text,fill=color)
            self.last=state
        area=w.RECT()
        if self.user.SystemParametersInfoW(0x30,0,ctypes.byref(area),0):
            position=(max(area.left,area.right-196),area.top+12)
            if position!=self.position:
                self.user.SetWindowPos(self.hwnd,w.HWND(-1),*position,184,36,0x10|0x40)
                self.position=position

    def close(self):
        self.window.destroy()

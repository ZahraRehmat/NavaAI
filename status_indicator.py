"""Small passive resident badge. No focus, pointer, or input operations."""
import ctypes,time
from ctypes import wintypes as w
import tkinter as tk


def indicator_state(*, ready, busy, enabled, microphone, handsfree, armed=False,
                    review=False, error=False, recognizing=False):
    if not ready: return 'Starting', '#94a3b8'
    if busy: return 'Working', '#fbbf24'
    if review: return 'Confirm or repeat', '#fbbf24'
    if enabled and error: return 'Mic error · F10', '#fb7185'
    if not enabled: return 'Voice off · F9', '#94a3b8'
    if not microphone: return 'Mic starting', '#94a3b8'
    if recognizing: return 'Hearing you', '#c4b5fd'
    if handsfree or armed: return 'Listening', '#4ade80'
    return 'Say Nava listen', '#67e8f9'


def dictation_state(*,recognizing=False,review=False):
    if recognizing:return 'Decoding text', '#c4b5fd'
    if review:return 'Not typed · repeat', '#fbbf24'
    return 'Dictating · say stop', '#c4b5fd'


class StatusIndicator:
    def __init__(self, root, visible=True):
        self.window=tk.Toplevel(root); self.window.withdraw()
        self.window.title('NAVA AI - Status')
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True, '-transparentcolor', '#010203')
        self.canvas=tk.Canvas(self.window,width=248,height=40,bg='#172033',highlightthickness=1,highlightbackground='#475569')
        self.canvas.pack()
        self.dot=self.canvas.create_oval(10,3,23,16,fill='#94a3b8',outline='')
        self.canvas.create_text(35,9,text='NAVA AI',anchor='w',fill='#e2e8f0',font=('Segoe UI',-12,'bold'))
        self.caption=self.canvas.create_text(8,26,text='Starting',anchor='w',fill='#94a3b8',font=('Segoe UI',-14))
        self.meter_back=self.canvas.create_rectangle(231,4,239,17,fill='#334155',outline='')
        self.meter=self.canvas.create_rectangle(231,17,239,17,fill='#4ade80',outline='')
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
        self.user.SetWindowDisplayAffinity(self.hwnd,0) # Visible to desktop/remote capture.
        from taskbar_status import TaskbarAnchor
        self.anchor=TaskbarAnchor()
        self.last=None;self.position=None;self.last_raise=0;self.visible=bool(visible)
        # Tk deiconify may activate a newly mapped window despite NOACTIVATE.
        self.user.ShowWindow(self.hwnd,4 if self.visible else 0)  # SW_SHOWNOACTIVATE
        self.update(('Starting','#94a3b8'))

    def update(self, state, level=0, *, help_hidden=False, prompt=""):
        if not self.visible:return
        import math
        hint=bool(help_hidden);layout=(hint,prompt)
        if layout!=getattr(self,'help_layout',(False,'')):
            self.help_layout=layout
            self.canvas.delete('quick_help');height=28 if hint and not prompt else 40
            if prompt:
                item=self.canvas.create_text(8,47,text=prompt,anchor='nw',width=232,fill='#fbbf24',font=('Segoe UI',-12),tags='quick_help')
                height=self.canvas.bbox(item)[3]+6
            if hint:
                for index,text in enumerate(('show dictionary','nava turn off · open grid')):
                    self.canvas.create_text(8,height+15+index*16,text=text,anchor='w',fill='#c4b5fd',font=('Segoe UI',-12),tags='quick_help')
                height+=40
            self.badge_height=height
            self.canvas.configure(height=height);self.position=None
        amount=max(0,min(1,(20*math.log10(max(float(level),1e-6))+65)/45))
        self.audio_amount=amount
        if state!=self.last:
            text,color=state
            self.canvas.itemconfigure(self.dot,fill=color)
            self.canvas.itemconfigure(self.caption,text=text,fill=color)
            self.last=state
        area=w.RECT()
        if self.user.SystemParametersInfoW(0x30,0,ctypes.byref(area),0):
            x,y,width,height=self.anchor.layout((area.left,area.top,area.right,area.bottom),248,getattr(self,'badge_height',40))
            position=(x,y,width,height)
            self.canvas.configure(width=width)
            self.canvas.coords(self.meter_back,width-17,4,width-9,17)
            self.canvas.coords(self.meter,width-17,17-round(13*amount),width-9,17)
            now=time.monotonic()
            # Owned Tk tool windows can lose their effective Z-order when a
            # sibling overlay is hidden, even with WS_EX_TOPMOST still set.
            # Reassert the passive topmost position without activating it.
            if position!=self.position or now-self.last_raise>=.5:
                self.user.SetWindowPos(self.hwnd,w.HWND(-1),*position,0x10|0x200)
                self.position=position;self.last_raise=now

    def close(self):
        self.anchor.close();self.window.destroy()

    def set_visible(self,value):
        self.visible=bool(value)
        self.position=None;self.last_raise=0
        self.user.ShowWindow(self.hwnd,4 if self.visible else 0)

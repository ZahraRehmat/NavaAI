"""App-local, click-through pointer halo. Never changes Windows cursor settings."""
import ctypes
import tkinter as tk

class CursorMarker:
    def __init__(self,root,visible=True):
        self.root=root; self.alive=True;self.visible=bool(visible);self.timer=None
        self.window=tk.Toplevel(root); self.window.withdraw()
        self.window.title('Gwen Doer Cursor'); self.window.overrideredirect(True)
        self.window.configure(bg='#010203')
        self.window.attributes('-transparentcolor','#010203','-topmost',True)
        self.canvas=tk.Canvas(self.window,width=64,height=64,bg='#010203',highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(8,8,56,56,outline='#111827',width=8)
        self.ring=self.canvas.create_oval(8,8,56,56,outline='#67e8f9',width=4)
        self.window.update_idletasks()
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetParent.argtypes=[ctypes.c_void_p]; user.GetParent.restype=ctypes.c_void_p
        user.GetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int]; user.GetWindowLongW.restype=ctypes.c_long
        user.SetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_long]; user.SetWindowLongW.restype=ctypes.c_long
        self.hwnd=user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        self.user=user;user.ShowWindow.argtypes=[ctypes.c_void_p,ctypes.c_int]
        # LAYERED + TRANSPARENT + TOOLWINDOW + NOACTIVATE: input passes through.
        user.SetWindowLongW(self.hwnd,-20,user.GetWindowLongW(self.hwnd,-20)|0x080800a0)
        # Allow desktop capture so remote collaborators can see Gwen's cursor.
        user.SetWindowDisplayAffinity.argtypes=[ctypes.c_void_p,ctypes.c_uint]
        user.SetWindowDisplayAffinity(self.hwnd,0)
        self.tick()

    def working(self,value):
        self.canvas.itemconfigure(self.ring,outline='#fbbf24' if value else '#67e8f9')

    def tick(self):
        if not self.alive:return
        if self.timer:
            try:self.root.after_cancel(self.timer)
            except tk.TclError:pass
        if self.visible:
            from windows_api import cursor
            x,y=cursor(); self.window.geometry(f'64x64+{max(0,x-32)}+{max(0,y-32)}')
            self.user.ShowWindow(self.hwnd,4) # SW_SHOWNOACTIVATE; never take the edit caret.
        self.timer=self.root.after(20,self.tick)

    def close(self):
        self.alive=False
        if self.timer:
            try:self.root.after_cancel(self.timer)
            except tk.TclError:pass
        self.window.destroy()

    def set_visible(self,value):
        self.visible=bool(value)
        self.user.ShowWindow(self.hwnd,4 if self.visible else 0)

"""Physical mouse backend, including reliable release at screen corners."""
import ctypes,time
from ctypes import wintypes as w
import windows_api as win

class GridMouse:
    def __init__(self):
        self.user=ctypes.WinDLL('user32',use_last_error=True);self.held=set();self.hold_windows=set()
        self.user.SetCursorPos.argtypes=[ctypes.c_int,ctypes.c_int];self.user.SetCursorPos.restype=w.BOOL
        self.user.WindowFromPoint.argtypes=[w.POINT];self.user.WindowFromPoint.restype=w.HWND
        self.user.GetAncestor.argtypes=[w.HWND,w.UINT];self.user.GetAncestor.restype=w.HWND
        self.user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];self.user.GetWindowLongW.restype=w.LONG
        self.user.mouse_event.argtypes=[w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.WPARAM];self.user.mouse_event.restype=None

    def position(self):return win.cursor()

    def target_at(self,point):
        hwnd=self.user.WindowFromPoint(w.POINT(*point));hwnd=self.user.GetAncestor(hwnd,2) if hwnd else None
        def usable(handle):
            if not win.user.IsWindowVisible(handle) or win.cloaked(handle):return False
            if win.title(handle).startswith('Gwen Doer'):return False
            if self.user.GetWindowLongW(handle,-20)&0x20:
                # Shell CoreWindow surfaces can use transparent parent windows
                # with interactive children; cursor/annotation layers cannot.
                name=ctypes.create_unicode_buffer(256)
                win.user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int];win.user.GetClassNameW.restype=ctypes.c_int
                win.user.GetClassNameW(handle,name,len(name))
                from grid_roots import interactive_shell
                if not interactive_shell(name.value):return False
            l,t,r,b=win.rect(handle);return l<=point[0]<r and t<=point[1]<b
        if hwnd and usable(hwnd):return hwnd
        found=[]
        @win.ENUM
        def visit(handle,_):
            try:
                if usable(handle):found.append(handle);return False
            except OSError:pass
            return True
        win.user.EnumWindows(visit,0)
        if not found:raise ValueError('No accessible input window is present at this screen point.')
        return found[0]

    def guard(self,point):
        hwnd=self.target_at(point);win.ensure_input_allowed(hwnd)
        for source in self.hold_windows:
            if win.user.IsWindow(source):win.ensure_input_allowed(source)
        return hwnd

    def move(self,point):
        if self.held:self.guard(point)
        if not self.user.SetCursorPos(*map(int,point)):raise ctypes.WinError(ctypes.get_last_error())
        if self.position()!=tuple(map(int,point)):raise ValueError('Windows could not reach that display point. The display layout may have changed.')

    def down(self,button='left'):
        if button in self.held:return
        hwnd=self.guard(self.position())
        self.user.mouse_event({'left':0x2,'right':0x8,'middle':0x20}[button],0,0,0,0)
        self.held.add(button);self.hold_windows.add(hwnd)

    def release(self):
        # Do not use a corner-sensitive automation library for emergency release.
        for button in tuple(self.held):self.user.mouse_event({'left':0x4,'right':0x10,'middle':0x40}[button],0,0,0,0)
        self.held.clear();self.hold_windows.clear()

    def click(self,button='left',count=1,stop=None):
        if self.held:raise ValueError('A mouse button is held. Say release before clicking.')
        for i in range(count):
            if stop and stop.is_set():raise InterruptedError('Stopped')
            try:self.down(button)
            finally:self.release()
            if i+1<count:
                if stop:stop.wait(.08)
                else:time.sleep(.08)

    def scroll(self,direction,amount):
        point=self.position();hwnd=self.guard(point)
        self.user.ScreenToClient.argtypes=[w.HWND,ctypes.POINTER(w.POINT)];self.user.ScreenToClient.restype=w.BOOL
        self.user.ChildWindowFromPointEx.argtypes=[w.HWND,w.POINT,w.UINT];self.user.ChildWindowFromPointEx.restype=w.HWND
        self.user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.user.PostMessageW.restype=w.BOOL
        child=hwnd
        for _ in range(24):
            local=w.POINT(*point)
            if not self.user.ScreenToClient(child,ctypes.byref(local)):break
            found=self.user.ChildWindowFromPointEx(child,local,7)
            if not found or found==child:break
            child=found
        delta=amount*120*(1 if direction in ('up','right') else -1)
        packed=((delta&0xffff)<<16)|sum({'left':1,'right':2,'middle':16}[b] for b in self.held)
        location=(point[0]&0xffff)|((point[1]&0xffff)<<16)
        if not self.user.PostMessageW(child,0x20e if direction in ('left','right') else 0x20a,packed,location):raise ctypes.WinError(ctypes.get_last_error())

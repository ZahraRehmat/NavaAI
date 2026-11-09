"""Physical-monitor geometry and process-local DPI setup."""
import ctypes
from ctypes import wintypes as w

class ScreenBounds:
    """Clamp a pointer to physical monitors without creating grid cells."""
    def __init__(self,monitors):
        self.monitors=[tuple(box) for box in monitors]
        if not self.monitors or any(r<=l or b<=t for l,t,r,b in self.monitors):raise ValueError('No valid display bounds.')
    def nearest(self,x,y):
        points=[(max(l,min(r-1,round(x))),max(t,min(b-1,round(y)))) for l,t,r,b in self.monitors]
        return min(points,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)

def enable_dpi_awareness():
    user=ctypes.WinDLL('user32',use_last_error=True)
    try:
        user.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p];user.SetProcessDpiAwarenessContext.restype=w.BOOL
        if user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):return
    except AttributeError:pass
    user.SetProcessDPIAware()

def monitors():
    user=ctypes.WinDLL('user32',use_last_error=True)
    class Info(ctypes.Structure):_fields_=[('size',w.DWORD),('monitor',w.RECT),('work',w.RECT),('flags',w.DWORD)]
    callback=ctypes.WINFUNCTYPE(w.BOOL,w.HMONITOR,w.HDC,ctypes.POINTER(w.RECT),w.LPARAM)
    user.GetMonitorInfoW.argtypes=[w.HMONITOR,ctypes.POINTER(Info)];user.GetMonitorInfoW.restype=w.BOOL
    user.EnumDisplayMonitors.argtypes=[w.HDC,ctypes.POINTER(w.RECT),callback,w.LPARAM];user.EnumDisplayMonitors.restype=w.BOOL
    rows=[]
    @callback
    def collect(handle,dc,rect,data):
        info=Info();info.size=ctypes.sizeof(info)
        if user.GetMonitorInfoW(handle,ctypes.byref(info)):
            r=info.monitor;rows.append((bool(info.flags&1),(r.left,r.top,r.right,r.bottom)))
        return True
    if not user.EnumDisplayMonitors(None,None,collect,0) or not rows:raise OSError('Cannot enumerate displays')
    rows.sort(key=lambda r:(not r[0],r[1][0],r[1][1]));return list(dict.fromkeys(r[1] for r in rows))

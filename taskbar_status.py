"""Read-only taskbar geometry, sampled off the UI thread."""
import ctypes,threading,time
from ctypes import wintypes as w


def badge_position(work,bar,occupied,width,height):
    """Fit wholly inside a free horizontal taskbar gap; otherwise sit above it."""
    l,t,r,b=work
    fallback=(l+8,max(t,b-height-6))
    if not bar:return fallback
    bl,bt,br,bb=bar
    if br-bl<bb-bt or bt<b-8:return fallback # Vertical/hidden taskbar.
    if height+4>bb-bt:return fallback
    intervals=[]
    for x1,y1,x2,y2 in occupied:
        if y2>bt and y1<bb and x2>bl and x1<br:
            intervals.append((max(bl,x1-5),min(br,x2+5)))
    cursor=bl+8;gaps=[]
    for x1,x2 in sorted(intervals):
        if x1-cursor>=width:gaps.append((cursor,x1))
        cursor=max(cursor,x2)
    if br-8-cursor>=width:gaps.append((cursor,br-8))
    if not gaps:return fallback
    # The gap immediately left of the centered app group is normally closest.
    center=(bl+br)/2
    a,z=min(gaps,key=lambda gap:abs(min(max(center-width/2,gap[0]),gap[1]-width)+width/2-center))
    x=min(max(center-width/2,a),z-width)
    return (round(x),bt+(bb-bt-height)//2)


def badge_layout(work,bar,occupied,width,height):
    """Shrink the panel to an available taskbar gap before using the fallback."""
    if bar and bar[2]-bar[0]>bar[3]-bar[1] and bar[1]>=work[3]-8 and height+4<=bar[3]-bar[1]:
        bl,bt,br,bb=bar;cursor=bl+8;gaps=[]
        intervals=sorted((max(bl,a-5),min(br,c+5)) for a,b,c,d in occupied if d>bt and b<bb and c>bl and a<br)
        for a,c in intervals:
            if a>cursor:gaps.append(a-cursor)
            cursor=max(cursor,c)
        gaps.append(max(0,br-8-cursor))
        available=max(gaps,default=0)
        if available>=156:width=min(width,available)
    x,y=badge_position(work,bar,occupied,width,height)
    return x,y,width,height


class TaskbarAnchor:
    def __init__(self):
        self.snapshot=None;self.stop=threading.Event()
        threading.Thread(target=self.sample,daemon=True,name='NAVA AI taskbar position').start()

    def position(self,work,width,height):
        snapshot=self.snapshot
        if not snapshot or time.monotonic()-snapshot[0]>10:return badge_position(work,None,[],width,height)
        return badge_position(work,snapshot[1],snapshot[2],width,height)

    def layout(self,work,width,height):
        snapshot=self.snapshot
        if not snapshot or time.monotonic()-snapshot[0]>10:return badge_layout(work,None,[],width,height)
        return badge_layout(work,snapshot[1],snapshot[2],width,height)

    def close(self):self.stop.set()

    def sample(self):
        import pythoncom
        pythoncom.CoInitializeEx(0)
        try:
            import comtypes.client
            from comtypes.gen.UIAutomationClient import CUIAutomation8,IUIAutomation2
            client=comtypes.client.CreateObject(CUIAutomation8,interface=IUIAutomation2)
            client.ConnectionTimeout=500;client.TransactionTimeout=700
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.FindWindowW.argtypes=[w.LPCWSTR,w.LPCWSTR];user.FindWindowW.restype=w.HWND
            user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
            request=client.CreateCacheRequest()
            for prop in (30001,30003,30022):request.AddProperty(prop)
            request.TreeScope=1;request.AutomationElementMode=0
            # Ignore broad containers; reserve actionable controls, including
            # Start, search, apps, widgets and the notification area.
            roles={50000,50002,50003,50004,50005,50007,50011,50013,50015,50019,50031}
            while not self.stop.is_set():
                try:
                    hwnd=user.FindWindowW('Shell_TrayWnd',None);rect=w.RECT()
                    if not hwnd or not user.GetWindowRect(hwnd,ctypes.byref(rect)):raise OSError('No taskbar')
                    controls=client.ElementFromHandle(hwnd).FindAllBuildCache(4,client.CreateTrueCondition(),request)
                    occupied=[]
                    for index in range(controls.Length):
                        el=controls.GetElement(index)
                        if el.CachedIsOffscreen or el.CachedControlType not in roles:continue
                        box=el.CachedBoundingRectangle
                        if box.right>box.left and box.bottom>box.top:occupied.append((box.left,box.top,box.right,box.bottom))
                    # No geometry means the provider failed, not an empty bar.
                    self.snapshot=(time.monotonic(),(rect.left,rect.top,rect.right,rect.bottom),occupied) if occupied else None
                except Exception:self.snapshot=None
                self.stop.wait(3)
        except Exception:self.snapshot=None
        finally:pythoncom.CoUninitialize()

"""Typed, private Win32 bindings; no UI Automation/COM needed for focus or bounds."""
import ctypes,time
from ctypes import wintypes as w

user=ctypes.WinDLL('user32',use_last_error=True)
user.GetForegroundWindow.argtypes=[]; user.GetForegroundWindow.restype=w.HWND
user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]; user.GetWindowRect.restype=w.BOOL
user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]; user.GetWindowTextW.restype=ctypes.c_int
user.IsWindowVisible.argtypes=[w.HWND]; user.IsWindowVisible.restype=w.BOOL
user.IsWindow.argtypes=[w.HWND];user.IsWindow.restype=w.BOOL
user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)];user.GetWindowThreadProcessId.restype=w.DWORD
user.IsIconic.argtypes=[w.HWND]; user.IsIconic.restype=w.BOOL
user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]; user.ShowWindow.restype=w.BOOL
user.SetForegroundWindow.argtypes=[w.HWND]; user.SetForegroundWindow.restype=w.BOOL
ENUM=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
user.EnumWindows.argtypes=[ENUM,w.LPARAM]; user.EnumWindows.restype=w.BOOL
user.IsWindowEnabled.argtypes=[w.HWND];user.IsWindowEnabled.restype=w.BOOL
user.GetLastActivePopup.argtypes=[w.HWND];user.GetLastActivePopup.restype=w.HWND
user.GetWindow.argtypes=[w.HWND,w.UINT];user.GetWindow.restype=w.HWND

def action_window(hwnd):
    """Follow only visible owned popups of a disabled owner, never arbitrary apps."""
    seen=set()
    while hwnd and hwnd not in seen and user.IsWindow(hwnd):
        seen.add(hwnd)
        if user.IsWindowEnabled(hwnd):return hwnd
        popup=user.GetLastActivePopup(hwnd)
        if not popup or popup==hwnd or not user.IsWindowVisible(popup):return hwnd
        if user.GetWindow(popup,4)!=hwnd:return hwnd
        hwnd=popup
    return hwnd

def blocking_dialogs():
    result=[]
    @ENUM
    def collect(hwnd,_):
        if not user.IsWindowVisible(hwnd):return True
        owner=user.GetWindow(hwnd,4)
        if owner and user.IsWindow(owner) and not user.IsWindowEnabled(owner) and action_window(owner)==hwnd:result.append(hwnd)
        return True
    user.EnumWindows(collect,0)
    return list(dict.fromkeys(result))

def foreground(): return user.GetForegroundWindow()

def cloaked(hwnd):
    """DWM-cloaked windows can report visible while drawing nothing."""
    try:
        dwm=ctypes.WinDLL('dwmapi');query=dwm.DwmGetWindowAttribute
        query.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD];query.restype=ctypes.c_long
        value=w.DWORD()
        return query(hwnd,14,ctypes.byref(value),ctypes.sizeof(value))==0 and bool(value.value)
    except (AttributeError,OSError):return False

def title(hwnd):
    buf=ctypes.create_unicode_buffer(2048); user.GetWindowTextW(hwnd,buf,len(buf)); return buf.value

def rect(hwnd):
    if not hwnd: raise ValueError('No foreground window is available yet')
    value=w.RECT()
    if not user.GetWindowRect(hwnd,ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return value.left,value.top,value.right,value.bottom

def focus(name):
    from catalog import norm
    query=norm(name); candidates=[]
    @ENUM
    def collect(hwnd,_):
        if user.IsWindowVisible(hwnd) and query in norm(title(hwnd)): candidates.append(hwnd)
        return True
    user.EnumWindows(collect,0)
    if len(candidates)!=1: raise ValueError('Could not identify one visible '+name+' window. Found '+str(len(candidates))+'.')
    hwnd=candidates[0]
    return focus_handle(hwnd,name)

def current_thread_id():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentThreadId.restype=w.DWORD
    return kernel.GetCurrentThreadId()


def activate_with_input_queues(hwnd):
    """Temporarily join input queues for a user-requested window activation.

    Background voice workers otherwise often get only a flashing taskbar icon.
    No artificial Alt/Enter presses or foreground-lock settings are used.
    """
    user.PeekMessageW.argtypes=[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT,w.UINT];user.PeekMessageW.restype=w.BOOL
    user.AttachThreadInput.argtypes=[w.DWORD,w.DWORD,w.BOOL];user.AttachThreadInput.restype=w.BOOL
    user.BringWindowToTop.argtypes=[w.HWND];user.BringWindowToTop.restype=w.BOOL
    message=w.MSG();user.PeekMessageW(ctypes.byref(message),None,0,0,0)
    own=current_thread_id();attached=[]
    threads=[user.GetWindowThreadProcessId(handle,None) for handle in (foreground(),hwnd) if handle]
    try:
        for other in dict.fromkeys(threads):
            if other and other!=own and user.AttachThreadInput(own,other,True):attached.append(other)
        user.BringWindowToTop(hwnd);user.SetForegroundWindow(hwnd)
        for _ in range(6):
            if foreground()==hwnd:return True
            time.sleep(.05)
        return False
    finally:
        for other in reversed(attached):user.AttachThreadInput(own,other,False)


def focus_handle(hwnd,name='target app'):
    hwnd=action_window(hwnd)
    ensure_input_allowed(hwnd)
    if foreground()==hwnd and not user.IsIconic(hwnd):return hwnd
    if user.IsIconic(hwnd):
        user.ShowWindowAsync.argtypes=[w.HWND,ctypes.c_int];user.ShowWindowAsync.restype=w.BOOL
        user.ShowWindowAsync(hwnd,9)
    user.SetForegroundWindow(hwnd)
    for _ in range(5):
        if foreground()==hwnd: return hwnd
        time.sleep(.05)
    if activate_with_input_queues(hwnd) and foreground()==hwnd:return hwnd
    raise ValueError('Windows refused to activate '+name+'. Its window was not brought to the foreground.')

def cursor():
    point=w.POINT()
    user.GetCursorPos.argtypes=[ctypes.POINTER(w.POINT)]; user.GetCursorPos.restype=w.BOOL
    if not user.GetCursorPos(ctypes.byref(point)): raise ctypes.WinError(ctypes.get_last_error())
    return point.x,point.y

def snapshot():
    hwnd=foreground()
    if not hwnd: return None
    try:
        user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int];user.GetClassNameW.restype=ctypes.c_int
        buf=ctypes.create_unicode_buffer(256);user.GetClassNameW(hwnd,buf,len(buf))
        pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        return {'hwnd':hwnd,'pid':pid.value,'title':title(hwnd),'class_name':buf.value,'bounds':rect(hwnd),'pointer':cursor()}
    except (OSError,ValueError): return None

def usable_target(context):
    if not context:return False
    name=context.get('title','').strip();kind=context.get('class_name','')
    if name.startswith('Gwen Doer'):return False
    if name.lower().rstrip('.')=='system tray overflow window':return False
    if kind in ('Shell_TrayWnd','Shell_SecondaryTrayWnd','NotifyIconOverflowWindow','TopLevelWindowForOverflowXamlIsland','tooltips_class32'):return False
    return bool(name) or kind in ('Progman','WorkerW','NUIDialog','#32770')

def target_alive(context):
    if not context or not user.IsWindow(context.get('hwnd',0)):return False
    if not user.IsWindowVisible(context['hwnd']):return False
    pid=w.DWORD()
    if not user.GetWindowThreadProcessId(context['hwnd'],ctypes.byref(pid)) or not pid.value:return False
    return not context.get('pid') or context['pid']==pid.value

def choose_target(current,remembered):
    for candidate in [current,*remembered]:
        if usable_target(candidate) and target_alive(candidate):return dict(candidate)
    return None

def restore_launch_focus(previous,own_pid=None):
    """Undo Tk initialization taking focus; never replace another app's focus."""
    import os
    current=snapshot()
    if not previous or not usable_target(previous) or not target_alive(previous):return False
    if not current or current.get('pid')!=(own_pid if own_pid is not None else os.getpid()):return False
    if current['hwnd']==previous['hwnd']:return False
    user.SetForegroundWindow(previous['hwnd'])
    return foreground()==previous['hwnd']

def scroll_at(hwnd,x,y,steps,horizontal=False):
    """Deliver wheel input to the visible pane under the pointer, not a focused toolbar button."""
    ensure_input_allowed(hwnd)
    user.WindowFromPoint.argtypes=[w.POINT]; user.WindowFromPoint.restype=w.HWND
    user.GetAncestor.argtypes=[w.HWND,w.UINT]; user.GetAncestor.restype=w.HWND
    user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]; user.PostMessageW.restype=w.BOOL
    child=user.WindowFromPoint(w.POINT(int(x),int(y)))
    if not child or user.GetAncestor(child,2)!=user.GetAncestor(hwnd,2): raise ValueError('Another window covers the scroll target. No wheel input was sent.')
    delta=int(steps)*120
    packed=((delta & 0xffff)<<16)
    point=(int(x)&0xffff)|((int(y)&0xffff)<<16)
    if not user.PostMessageW(child,0x20e if horizontal else 0x20a,packed,point): raise ctypes.WinError(ctypes.get_last_error())

def stable_foreground():
    for _ in range(10):
        hwnd=foreground()
        if hwnd:
            try: rect(hwnd); return hwnd
            except (ValueError,OSError): pass
        time.sleep(.05)
    raise ValueError('No stable foreground window was available for capture')

def ensure_input_allowed(hwnd):
    """Windows UIPI blocks input into higher-integrity processes; never auto-elevate."""
    if not user.IsWindow(hwnd):raise ValueError('The selected window has closed. Select the app again; no input was attempted.')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    adv=ctypes.WinDLL('advapi32',use_last_error=True)
    user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]; user.GetWindowThreadProcessId.restype=w.DWORD
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]; kernel.OpenProcess.restype=w.HANDLE
    kernel.GetCurrentProcess.argtypes=[]; kernel.GetCurrentProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]; kernel.CloseHandle.restype=w.BOOL
    adv.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]; adv.OpenProcessToken.restype=w.BOOL
    adv.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD)]; adv.GetTokenInformation.restype=w.BOOL
    adv.GetSidSubAuthorityCount.argtypes=[w.LPVOID]; adv.GetSidSubAuthorityCount.restype=ctypes.POINTER(ctypes.c_ubyte)
    adv.GetSidSubAuthority.argtypes=[w.LPVOID,w.DWORD]; adv.GetSidSubAuthority.restype=ctypes.POINTER(w.DWORD)
    class LABEL(ctypes.Structure): _fields_=[('sid',w.LPVOID),('attributes',w.DWORD)]
    def level(process):
        token=w.HANDLE()
        if not adv.OpenProcessToken(process,8,ctypes.byref(token)): raise ctypes.WinError(ctypes.get_last_error())
        try:
            size=w.DWORD(); adv.GetTokenInformation(token,25,None,0,ctypes.byref(size))
            buf=ctypes.create_string_buffer(size.value)
            if not adv.GetTokenInformation(token,25,buf,size,ctypes.byref(size)): raise ctypes.WinError(ctypes.get_last_error())
            sid=ctypes.cast(buf,ctypes.POINTER(LABEL)).contents.sid
            return adv.GetSidSubAuthority(sid,adv.GetSidSubAuthorityCount(sid)[0]-1)[0]
        finally: kernel.CloseHandle(token)
    pid=w.DWORD()
    if not user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid)) or not pid.value:raise ValueError('The selected window is no longer available; no input was attempted.')
    process=kernel.OpenProcess(0x1000,False,pid.value)
    if not process:
        error=ctypes.get_last_error()
        if not user.IsWindow(hwnd):raise ValueError('The selected window closed before input; no input was attempted.')
        raise PermissionError(f'Cannot inspect target process permissions (Windows error {error}, PID {pid.value}, window {hwnd}). No input was attempted.')
    try:
        if level(process)>level(kernel.GetCurrentProcess()):
            raise PermissionError('The target app runs at a higher Windows integrity level than Gwen. Windows blocks this input; no action was attempted. Handle this step manually in that app.')
    finally: kernel.CloseHandle(process)

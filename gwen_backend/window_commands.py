"""Bounded existing-window switching and one-confirmation graceful closing."""
import ctypes,re,time
from ctypes import wintypes as w
from pathlib import PureWindowsPath
from rapidfuzz import fuzz
from catalog import norm,core_name,ALIASES
from app_identity import compact_name,alias_value
import windows_api as win

CLASS_APPS={'OpusApp':'Word','XLMAIN':'Excel','PPTFrameClass':'PowerPoint','CabinetWClass':'File Explorer','ExploreWClass':'File Explorer'}

def intent(task,catalog=None):
    clean=re.sub(r'^(?:please\s+|can you\s+|could you\s+)','',task.strip(),flags=re.I).rstrip('.!')
    clean=re.sub(r'\s+please$','',clean,flags=re.I)
    if re.match(r'switch\s+(?:back\s+)?to\s+(?:sheet|slide|tab|cell)\b',clean,re.I):return None
    if re.fullmatch(r'close\s+(?:(?:this|the|current|active|selected)\s+)?(?:window|app|application)',clean,re.I):return {'action':'close_window'}
    if clean.lower() in ('quit','exit','close this','close it'):return {'action':'close_window'}
    close=re.fullmatch(r'(force\s+(?:close|quit|stop)|kill|terminate|close|quit|exit|stop)\s+(?:the\s+)?(.+)',clean,re.I)
    if close:
        verb,name=close.groups()
        if re.fullmatch(r'(?:(?:this|current|active|selected)\s+)?(?:browser\s+)?tab|(?:smart |full )?grid|listening|task|the task|now|video|playback|media|scrolling',name,re.I):return None
        force=verb.lower().startswith('force ') or verb.lower() in ('kill','terminate')
        if re.fullmatch(r'(?:(?:this|current|active|selected)\s+)?(?:window|app|application)',name,re.I):
            return {'action':'force_close_window' if force else 'close_window'}
        # "whats app" is an alias, not the name "whats" with an app suffix.
        known=norm(name) in ALIASES
        if not known and catalog:
            try:catalog.resolve(name);known=True
            except ValueError:pass
        if not known:
            name=re.sub(r'^(?:app|application)\s+','',name,flags=re.I)
            if norm(name) not in ALIASES:name=re.sub(r'\s+(?:app|application|window)$','',name,flags=re.I)
        return {'action':'force_close_named' if force else 'close_named','name':name}
    match=re.fullmatch(r'bring\s+(.+?)\s+to\s+(?:the\s+)?(?:front|foreground)',clean,re.I)
    if match:return {'action':'switch_window','name':match[1]}
    match=re.fullmatch(r'(?:switch(?:\s+(?:back\s+)?to)?|bring(?:\s+up)?|focus)\s+(?:the\s+)?(.+)',clean,re.I)
    if match:
        name=match[1]
        if norm(name) not in ALIASES:name=re.sub(r'\s+(?:window|app)$','',name,flags=re.I)
        return {'action':'switch_window','name':name}
    return None

def process_name(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];kernel.QueryFullProcessImageNameW.restype=w.BOOL
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return ''
    try:
        buf=ctypes.create_unicode_buffer(32768);size=w.DWORD(len(buf))
        return PureWindowsPath(buf.value).stem if kernel.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)) else ''
    finally:kernel.CloseHandle(handle)


def process_app_id(pid):
    """Packaged apps can have generic executable names; reuse catalog AUMIDs."""
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    try:query=kernel.GetApplicationUserModelId
    except AttributeError:return ''
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    query.argtypes=[w.HANDLE,ctypes.POINTER(w.UINT),w.LPWSTR];query.restype=w.LONG
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return ''
    try:
        size=w.UINT(0)
        if query(handle,ctypes.byref(size),None)!=122 or not 0<size.value<32768:return ''
        buffer=ctypes.create_unicode_buffer(size.value)
        return buffer.value if query(handle,ctypes.byref(size),buffer)==0 else ''
    finally:kernel.CloseHandle(handle)

def running_windows():
    rows=[]
    win.user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int];win.user.GetClassNameW.restype=ctypes.c_int
    win.user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];win.user.GetWindowLongW.restype=w.LONG
    @win.ENUM
    def collect(hwnd,_):
        if not win.user.IsWindowVisible(hwnd) or win.user.GetWindow(hwnd,4):return True
        if win.user.GetWindowLongW(hwnd,-20)&0x80:return True
        name=win.title(hwnd)
        if not name or name.startswith('Gwen Doer'):return True
        buf=ctypes.create_unicode_buffer(256);win.user.GetClassNameW(hwnd,buf,len(buf))
        if buf.value in ('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd'):return True
        pid=w.DWORD();win.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        executable=process_name(pid.value)
        rows.append({'hwnd':hwnd,'pid':pid.value,'title':name,'class_name':buf.value,'process':executable,
                     'app_id':process_app_id(pid.value),'app':CLASS_APPS.get(buf.value,executable)})
        return True
    win.user.EnumWindows(collect,0)
    return rows

def match_window(rows,query,catalog,current=None,chooser=None):
    names=catalog.identities(query)
    names={core_name(n) for n in names if n}
    ranked=[]
    for row in rows:
        ide_request=any(n.startswith('visual studio') and 'code' not in n.split() for n in names)
        if ide_request and ('visual studio code' in norm(row.get('title','')) or norm(row.get('process','')) in ('code','code insiders')):continue
        labels=[norm(row.get(k,'')) for k in ('title','app','process','app_id')]
        labels+=[norm(alias_value(label,catalog.aliases)) for label in list(labels)]
        score=0
        for name in names:
            for label in labels:
                label=core_name(label)
                if not label:continue
                score=max(score,100 if compact_name(label)==compact_name(name) else 94 if set(name.split())<=set(label.split()) else fuzz.ratio(name,label),
                          fuzz.ratio(compact_name(name),compact_name(label)))
        if score>=78:ranked.append((score,row))
    ranked.sort(key=lambda item:-item[0])
    if not ranked:raise ValueError('No running window matches '+query+'. Say open '+query+' to launch it.')
    tied=[row for score,row in ranked if ranked[0][0]-score<4]
    if len(tied)>1:
        selected=next((row for row in tied if current and row['hwnd']==current.get('hwnd')),None)
        if selected:return selected
        if chooser:
            index=chooser('Which running window should receive this command?',
                [dict(row,label=row['title'],detail=row.get('app',''),match_score=ranked[0][0]) for row in tied])
            if index is None:raise InterruptedError('Window selection cancelled.')
            if not isinstance(index,int) or not 0<=index<len(tied):raise ValueError('Invalid window choice.')
            return tied[index]
        raise ValueError('Several running windows match. Specify a document/window title: '+'; '.join(row['title'] for row in tied[:5]))
    return ranked[0][1]

def switch_to(query,catalog,current=None):
    target=match_window(running_windows(),query,catalog,current)
    if not win.target_alive(target):raise ValueError('That window closed before switching. Try again.')
    hwnd=win.focus_handle(target['hwnd'],target['title'])
    fresh=win.snapshot()
    if not fresh or fresh['hwnd']!=hwnd:raise ValueError('Window activation could not be verified.')
    return fresh

def request_close(context,confirm,stop):
    if not context or context.get('class_name') in ('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd') or not win.usable_target(context) or not win.target_alive(context):raise ValueError('Select the window you want to close, then repeat the command.')
    bound=dict(context);name=win.title(bound['hwnd'])
    if not confirm('Close this window?\n\n'+name+'\n\nThe app may ask you to save unsaved work.'):return 'Close cancelled.'
    if stop.is_set():return 'Stopped'
    if not win.target_alive(bound) or win.title(bound['hwnd'])!=name:raise ValueError('The selected window changed while confirmation was open. Nothing was closed.')
    win.ensure_input_allowed(bound['hwnd'])
    # WM_CLOSE is the graceful window close request, like its X button. Never
    # terminate the process or answer a save/discard dialog automatically.
    win.user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];win.user.PostMessageW.restype=w.BOOL
    if not win.user.PostMessageW(bound['hwnd'],0x0010,0,0):raise ctypes.WinError(ctypes.get_last_error())
    for _ in range(10):
        if not win.user.IsWindow(bound['hwnd']):return 'Closed '+name+'.'
        if win.action_window(bound['hwnd'])!=bound['hwnd']:return 'Close requested. The app has a dialog open; choose Save, Don\'t Save, or Cancel there.'
        if stop.wait(.1):break
    return 'Close requested for '+name+'. The app may need you to finish its save/confirmation dialog.'


def request_close_named(query,catalog,current,confirm,stop,chooser=None,force=False):
    target=match_window(running_windows(),query,catalog,current,chooser)
    return request_force_close(target,confirm,stop) if force else request_close(target,confirm,stop)


def request_force_close(context,confirm,stop):
    """Explicit force commands only. Bind and recheck the selected process."""
    import os
    if not context or not context.get('pid') or not win.target_alive(context):raise ValueError('The selected app is no longer running.')
    bound=dict(context);pid=bound['pid'];name=win.title(bound['hwnd']);executable=process_name(pid).lower()
    protected={'explorer','system','registry','smss','csrss','wininit','winlogon','lsass','services','svchost','dwm','logonui'}
    if pid==os.getpid() or not executable or executable in protected:raise ValueError('Force-stop is unavailable for this process. Use normal close instead.')
    if not confirm('Force-stop '+name+'?\n\nUnsaved work may be lost. This stops its process and can close other windows belonging to that process.'):return 'Force-stop cancelled.'
    if stop.is_set():return 'Stopped'
    if not win.target_alive(bound) or win.title(bound['hwnd'])!=name:raise ValueError('The selected app changed during confirmation. Nothing was stopped.')
    win.ensure_input_allowed(bound['hwnd'])
    return terminate_process(pid)


def terminate_process(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.TerminateProcess.argtypes=[w.HANDLE,w.UINT];kernel.TerminateProcess.restype=w.BOOL
    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.WaitForSingleObject.restype=w.DWORD
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
    handle=kernel.OpenProcess(0x100000|0x1000|1,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel.TerminateProcess(handle,1):raise ctypes.WinError(ctypes.get_last_error())
        if kernel.WaitForSingleObject(handle,2000)!=0:return 'Force-stop requested; process exit has not yet been confirmed.'
        return 'Force-stopped the selected app process.'
    finally:kernel.CloseHandle(handle)

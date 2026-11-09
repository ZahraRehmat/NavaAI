"""Single-thread, process-isolated UIA scanner. JSON lines in/out; no input actions."""
import json,sys,time
sys.coinit_flags=0
from grid_display import enable_dpi_awareness
enable_dpi_awareness()
import pythoncom
pythoncom.CoInitializeEx(0)
from grid_branch_scan import decode_target,scan_visible_branches
from grid_roots import merge_roots,interactive_shell
import windows_api as win
ROLES={'Button','Edit','ComboBox','Hyperlink','CheckBox','RadioButton','TabItem',
       'ListItem','MenuItem','TreeItem','Slider','Spinner','ScrollBar','DataItem',
       'SplitButton','Document','Thumb','HeaderItem'}

CACHE={}
CHANGES=None


def configure_timeouts():
    """Use the Windows 8+ UIA client with bounded provider transactions."""
    try:
        import comtypes.client
        from comtypes.gen.UIAutomationClient import CUIAutomation8,IUIAutomation2
        from pywinauto.uia_defines import IUIA
        client=comtypes.client.CreateObject(CUIAutomation8,interface=IUIAutomation2)
        client.ConnectionTimeout=600;client.TransactionTimeout=900
        uia=IUIA();uia.iuia=client;uia.root=client.GetRootElement()
        uia.true_condition=client.CreateTrueCondition();uia.get_focused_element=client.GetFocusedElement
        return True
    except Exception:return False


def screen_roots(context):
    from ctypes import wintypes as w
    import ctypes
    found=[]
    win.user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];win.user.GetWindowLongW.restype=w.LONG
    @win.ENUM
    def visit(hwnd,_):
        if not win.user.IsWindowVisible(hwnd) or win.user.IsIconic(hwnd) or win.cloaked(hwnd):return True
        title=win.title(hwnd)
        if title.startswith('Gwen Doer'):return True
        buf=ctypes.create_unicode_buffer(256);win.user.GetClassNameW(hwnd,buf,len(buf));kind=buf.value
        if win.user.GetWindowLongW(hwnd,-20)&0x20 and not interactive_shell(kind):return True
        if kind=='tooltips_class32':return True
        pid=w.DWORD();win.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        scope='taskbar' if kind in ('Shell_TrayWnd','Shell_SecondaryTrayWnd') else 'desktop' if kind in ('Progman','WorkerW') else 'app'
        found.append({'hwnd':int(hwnd),'pid':pid.value,'title':title,'kind':kind,'scope':scope})
        return True
    win.user.EnumWindows(visit,0)
    # Windows 11 shell-band windows (Start/taskbar/flyouts) can be absent
    # from EnumWindows while still visible in the accessibility desktop.
    from pywinauto.uia_defines import IUIA
    try:
        uia=IUIA();request=uia.iuia.CreateCacheRequest()
        for prop in (30001,30002,30005,30012,30020,30022):request.AddProperty(prop)
        request.TreeScope=1;request.AutomationElementMode=0
        children=uia.iuia.GetRootElement().FindAllBuildCache(2,uia.true_condition,request)
        accessible=[]
        for i in range(children.Length):
            el=children.GetElement(i);hwnd=int(el.CachedNativeWindowHandle or 0)
            if not hwnd or el.CachedIsOffscreen or win.cloaked(hwnd):continue
            title=el.CachedName or '';kind=el.CachedClassName or ''
            if title.startswith('Gwen Doer') or (win.user.GetWindowLongW(hwnd,-20)&0x20 and not interactive_shell(kind)):continue
            scope='taskbar' if kind in ('Shell_TrayWnd','Shell_SecondaryTrayWnd') else 'desktop' if kind in ('Progman','WorkerW') else 'app'
            accessible.append({'hwnd':hwnd,'pid':el.CachedProcessId,'title':title,'kind':kind,'scope':scope})
        found=merge_roots(found,accessible)
    except Exception:pass
    from grid_visibility import exposed
    from grid_display import monitors
    screens=monitors();above=[];visible=[]
    for row in found:
        try:
            box=win.rect(row['hwnd'])
            if box[2]<=box[0] or box[3]<=box[1]:continue
            regions=exposed(box,above)
            # Always inspect the desktop icon host; full-size shell background
            # windows can otherwise hide it during rectangle subtraction.
            # Per-target hit testing below still removes covered desktop icons.
            if row['scope'] in ('taskbar','desktop') or any(min(r,sr)>max(l,sl) and min(b,sb)>max(t,st) for l,t,r,b in regions for sl,st,sr,sb in screens):visible.append(row)
            # Shell-band surfaces can have transparent margins around a menu.
            if not interactive_shell(row['kind']):above.append(box)
        except OSError:continue
    found=visible
    active=context.get('hwnd') if context else None
    # Shell controls must not wait behind a complex application tree.
    from grid_roots import popup_surface
    found.sort(key=lambda row:0 if row['scope']=='taskbar' else 1 if popup_surface(row['kind']) else 2 if row['hwnd']==active else 4 if row['scope']=='desktop' else 3)
    return found




def scan_root(owner,hwnd,pid,scope,budget):
    """Read HWND directly; never wait on pywinauto's window-resolution retries."""
    from pywinauto.uia_defines import IUIA
    uia=IUIA();request=uia.iuia.CreateCacheRequest()
    for prop in (30000,30001,30003,30005,30010,30011,30012,30022,30028,30031,30034,30043,30070):request.AddProperty(prop)
    request.TreeScope=1;request.AutomationElementMode=1
    root=uia.iuia.ElementFromHandle(hwnd);bounds=win.rect(hwnd)
    # Shell trees are compact; application trees can contain unbounded virtual
    # chat/message history. Query only visible branches for applications.
    if scope=='app':
        import ctypes
        from ctypes import wintypes as w
        kind=ctypes.create_unicode_buffer(256)
        win.user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
        win.user.GetClassNameW(hwnd,kind,len(kind))
        rows=scan_visible_branches(root,hwnd,pid,scope,bounds,uia,request,1.0,file_rows=kind.value=='CabinetWClass',excel_sheet=kind.value=='XLMAIN')
        from grid_roots import popup_surface
        if popup_surface(kind.value):
            from grid_popup_scan import scan_popup
            popup_rows=scan_popup(hwnd,pid,scope,bounds,uia,request,.65)
            rows=list({row['key']:row for row in rows+popup_rows}.values())
        return rows
    try:elements=root.FindAllBuildCache(4,uia.true_condition,request)
    except Exception:return scan_visible_branches(root,hwnd,pid,scope,bounds,uia,request,1.4)
    rows=[];seen=set()
    for index in range(min(2500,elements.Length)):
        if len(rows)>=600:break
        try:
            row,_=decode_target(elements.GetElement(index),hwnd,pid,scope,bounds,uia)
            if row and row['key'] not in seen:rows.append(row);seen.add(row['key'])
        except Exception:continue
    return rows


def visible_rows(rows):
    # Exclude controls covered by another app, while ignoring Gwen's own overlays.
    from grid_mouse import GridMouse
    mouse=GridMouse();result=[]
    for row in rows:
        l,t,r,b=row['bounds'];point=((l+r-1)//2,(t+b-1)//2)
        try:
            if row.get('scope')=='taskbar' or mouse.target_at(point)==row['hwnd']:result.append(row)
        except (OSError,ValueError):pass
    return result


def observe(context,force=False,skip=(),progress=None):
    roots=screen_roots(context);dirty=CHANGES.consume() if CHANGES else set()
    now=time.monotonic();live={root['hwnd'] for root in roots}
    for hwnd in list(CACHE):
        if hwnd not in live:del CACHE[hwnd]
    rows=[];scanned=0;start=time.monotonic()
    for root in roots:
        hwnd=root['hwnd'];cached=CACHE.get(hwnd);scope=root['scope']
        if hwnd in skip:
            CACHE.pop(hwnd,None);continue
        signature=(root['pid'],win.rect(hwnd),root['title'])
        stale=not cached or cached['signature']!=signature or hwnd in dirty or now-cached['time']>2
        if force is True or (force and hwnd in force) or stale:
            if progress:progress({'scanning':hwnd})
            try:
                items=scan_root(None,hwnd,root['pid'],scope,1.4)
                CACHE[hwnd]={'rows':items,'signature':signature,'time':time.monotonic()};scanned+=1
            except Exception:
                CACHE.pop(hwnd,None)
        rows.extend(CACHE.get(hwnd,{}).get('rows',[]))
        if progress:progress({'partial':True,'rows':visible_rows(rows)})
    result=visible_rows(rows)
    return {'rows':result,'skipped':[r['hwnd'] for r in roots if r['hwnd'] in skip],'timing':{'scan_ms':round((time.monotonic()-start)*1000,1),'roots':len(roots),'rescanned':scanned,'visible_targets':len(result)}}


if __name__=='__main__':
    import threading
    from grid_events import ScreenChanges
    output_lock=threading.Lock()
    def emit(value):
        with output_lock:print(json.dumps(value),flush=True)
    configure_timeouts()
    CHANGES=ScreenChanges(lambda:emit({'changed':True}))
    try:
        for line in sys.stdin:
            try:
                request=json.loads(line)
                # Accept the old direct-context protocol for diagnostic callers.
                result=observe(request.get('context',request),request.get('force',False),request.get('skip',()),emit)
            except Exception as exc:result={'error':str(exc).strip() or type(exc).__name__}
            emit(result)
    finally:CHANGES.close()

"""Deterministic address-bar navigation in an already open ordinary browser."""
from urllib.parse import urlsplit
from routing import browser_channel
import windows_api as win
import re

def focused(context,stop):
    if stop.is_set():raise InterruptedError('Stopped')
    if not browser_channel(context) or not win.target_alive(context):raise ValueError('Select a live Chrome/Edge/Chromium window first.')
    if win.focus_handle(context['hwnd'],context['title'])!=context['hwnd']:raise ValueError('The browser has a modal dialog. Finish it first.')

def keys(context,sequence,stop,expected_title=None):
    focused(context,stop)
    import desktop_control
    if expected_title is not None and win.title(context['hwnd'])!=expected_title:raise ValueError('The active tab changed before closing. Repeat the close request.')
    if win.foreground()!=context['hwnd']:raise ValueError('Browser focus changed before input.')
    desktop_control.act({'action':'hotkey','keys':sequence})

def observe_tabs(context):
    from pywinauto import Desktop
    root=Desktop(backend='uia').window(handle=context['hwnd']).wrapper_object();rows=[]
    for element in root.descendants(control_type='TabItem'):
        try:
            # Web-page tabs also expose TabItem: exclude descendants of Document.
            parent=element.parent();inside_page=False;under_window=False
            for _ in range(35):
                if parent.element_info.control_type=='Document':inside_page=True;break
                if parent.handle==context['hwnd']:under_window=True;break
                parent=parent.parent()
            if inside_page or not under_window or not element.is_enabled():continue
            name=element.element_info.name
            if not name:continue
            try:selected=bool(element.iface_selection_item.CurrentIsSelected)
            except Exception:selected=False
            row={'name':name,'element':element,'runtime_id':tuple(element.element_info.runtime_id),'selected':selected}
            if element.is_visible():
                box=element.rectangle();row['bounds']=[box.left,box.top,box.right,box.bottom]
            rows.append(row)
        except Exception:continue
    return rows

def select_tab(context,target,stop,chooser=None):
    from browser_commands import tab_index
    focused(context,stop);rows=observe_tabs(context)
    current=next((i for i,row in enumerate(rows) if row['selected']),0)
    index=tab_index(target,rows,current,chooser);chosen=rows[index]
    focused(context,stop)
    fresh=next((row for row in observe_tabs(context) if row['runtime_id']==chosen['runtime_id']),None)
    if fresh is None or fresh['name']!=chosen['name']:raise ValueError('The chosen tab changed or closed while choosing. Try again.')
    element=fresh['element']
    try:pattern=element.iface_selection_item
    except Exception:pattern=None
    if pattern is not None:pattern.Select()
    elif element.is_visible():element.click_input()
    else:raise ValueError('This tab is hidden and does not expose selection. Expand its tab group first.')
    context=dict(context,title=win.title(context['hwnd']))
    return context,'Switched to tab: '+chosen['name']+'.'

def command(context,request,stop,chooser=None):
    op=request['action']
    if op=='tab_new':keys(context,['ctrl','t'],stop);return 'Opened a new browser tab.'
    if op=='tab_close':keys(context,['ctrl','w'],stop,expected_title=context['title']);return 'Close requested for the current browser tab. Any unsaved-work prompt is left for you.'
    if op=='tab_switch':return select_tab(context,request['target'],stop,chooser)[1]
    if op in ('media_pause','media_play'):
        if request.get('site')=='youtube' and 'youtube' not in context.get('title','').lower():context,_=select_tab(context,'youtube',stop,chooser)
        focused(context,stop)
        from accessibility import NativeControls
        probe=NativeControls();controls=probe.observe(hwnd=context['hwnd'],depth=24,limit=700)
        def playback(label):
            return [row for row in controls if row['type']=='Button' and re.fullmatch(label+r'(?:\s+(?:video|button|playback))?(?:\s*\([^)]*\))?',row['name'].strip(),re.I)]
        desired='pause' if op=='media_pause' else 'play|resume'
        candidates=playback('(?:'+desired+')')
        if not candidates:
            opposite=playback('(?:play|resume)' if op=='media_pause' else 'pause')
            if len(opposite)==1:return 'The observed player is already '+('paused.' if op=='media_pause' else 'playing.')
            raise ValueError('No unambiguous Play/Pause control was exposed by this page. Show the video controls and retry.')
        index=0
        if len(candidates)>1:
            if not chooser:raise ValueError('Several playback controls are visible. Specify the player.')
            index=chooser('Which playback control?', [dict(row,label=row['name'],match_score=100) for row in candidates])
            if index is None:raise InterruptedError('Media selection cancelled.')
        target=candidates[index]
        if stop.is_set():raise InterruptedError('Stopped')
        probe.act({'action':'ui_click','id':target['id'],'expected_name':target['name']})
        return 'Clicked the observed '+target['name']+' video control.'
    raise ValueError('Unknown native browser command')

def navigate_window(context,url,stop):
    if not browser_channel(context):raise ValueError('The selected window is not a recognized browser.')
    parsed=urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.netloc or any(c in url for c in '\r\n\t'):raise ValueError('Only a valid HTTP/HTTPS address is allowed.')
    bound=dict(context)
    if not win.target_alive(bound):raise ValueError('The selected browser window has closed.')
    win.focus_handle(bound['hwnd'],bound['title'])
    import desktop_control
    for action in ({'action':'hotkey','keys':['ctrl','l']},{'action':'type','text':url},{'action':'press','key':'enter'}):
        if stop.is_set():raise InterruptedError('Stopped')
        if not win.target_alive(bound) or win.foreground()!=bound['hwnd']:raise ValueError('Browser focus changed; navigation stopped before further input.')
        desktop_control.act(action)
    return 'Navigation requested in the selected browser: '+url

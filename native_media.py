"""Observed browser playback controls, with state checks and scoped key input."""
import re,time


def playback_name(name):
    m=re.fullmatch(r'(play|pause|resume)(?:\s+(?:video|button|playback))?(?:\s*\([^)]*\))?',name.strip(),re.I)
    return ('play' if m[1].lower()=='resume' else m[1].lower()) if m else None


def controls(context):
    from pywinauto import Desktop
    root=Desktop(backend='uia').window(handle=context['hwnd']).wrapper_object()
    result=[]
    for e in root.descendants(control_type='Button'):
        try:
            state=playback_name(e.element_info.name)
            if state and e.is_enabled():result.append({'element':e,'name':e.element_info.name,'state':state,'visible':e.is_visible()})
        except Exception:continue
    return result


def pick(rows,chooser=None):
    tagged=[r for r in rows if re.search(r'\(k\)',r['name'],re.I)]
    preferred=[r for r in tagged if r['visible']] or tagged or [r for r in rows if r['visible']] or rows
    if not preferred:raise ValueError('No Play/Pause control is exposed by this page. Open a video first.')
    if len(preferred)==1:return preferred[0]
    if not chooser:raise ValueError('Several media players are present. Select the intended player first.')
    index=chooser('Which video player?', [dict(label=r['name']) for r in preferred])
    if index is None:raise InterruptedError('Media selection cancelled.')
    if not isinstance(index,int) or not 0<=index<len(preferred):raise ValueError('Invalid media choice.')
    return preferred[index]


def check_active(context,stop):
    import windows_api as win
    if stop.is_set():raise InterruptedError('Stopped')
    if win.foreground()!=context['hwnd'] or win.title(context['hwnd'])!=context['title']:raise ValueError('Browser/video changed; no media input was sent.')


def settled_controls(context,stop,timeout=.8):
    deadline=time.monotonic()+timeout
    while True:
        check_active(context,stop);rows=controls(context)
        if rows:return rows
        if time.monotonic()>=deadline:return []
        stop.wait(.04)


def same_player(rows,identity):
    exact=next((r for r in rows if tuple(r['element'].element_info.runtime_id)==identity),None)
    if exact:return exact
    # YouTube can replace the button's accessibility node when focus reveals
    # its controls. The bound window/title plus one unique (k) control identifies
    # the same player without assuming that the old node must survive.
    youtube=[r for r in rows if re.search(r'\(k\)',r['name'],re.I)]
    return youtube[0] if len(youtube)==1 else None


def focus_control(row,context,stop):
    from native_browser import focused
    from pywinauto.uia_defines import IUIA
    focused(context,stop)
    element=row['element'];element.set_focus()
    identity=tuple(element.element_info.runtime_id);deadline=time.monotonic()+.7
    while tuple(IUIA().iuia.GetFocusedElement().GetRuntimeId())!=identity:
        check_active(context,stop)
        if time.monotonic()>=deadline:raise ValueError('The video control did not receive focus. No media key was sent.')
        stop.wait(.025)
    return identity


def click_control(row,context,stop):
    from native_browser import focused
    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto.uia_defines import IUIA
    check_active(context,stop);element=row['element'];box=element.rectangle()
    if not element.is_visible() or box.width()<=0 or box.height()<=0:raise ValueError('The video button is hidden. No click was sent.')
    identity=tuple(element.element_info.runtime_id)
    hit=UIAElementInfo.from_point((box.left+box.right)//2,(box.top+box.bottom)//2).element
    for _ in range(8):
        if not hit:break
        if tuple(hit.GetRuntimeId())==identity:
            if stop.is_set():raise InterruptedError('Stopped')
            element.click_input();return
        hit=IUIA().iuia.ControlViewWalker.GetParentElement(hit)
    raise ValueError('Another page element covers the video button. Nothing was clicked.')


def skip_ad_controls(context):
    from pywinauto import Desktop
    root=Desktop(backend='uia').window(handle=context['hwnd']).wrapper_object()
    rows=[]
    for element in root.descendants(control_type='Button'):
        try:
            name=' '.join(element.element_info.name.split())
            if re.fullmatch(r'skip(?: ads?)?',name,re.I) and element.is_visible() and element.is_enabled():
                rows.append({'element':element,'name':name})
        except Exception:continue
    return rows


def skip_ad(context,stop):
    check_active(context,stop)
    if not re.search(r'\byoutube\b',context.get('title',''),re.I):
        raise ValueError('Skip ad requires an open YouTube video.')
    rows=skip_ad_controls(context)
    if not rows:return 'No available Skip ad button. The ad may not be skippable yet, or no ad is playing.'
    if len(rows)!=1:raise ValueError('Several Skip ad buttons are exposed. Nothing was clicked.')
    click_control(rows[0],context,stop)
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        check_active(context,stop)
        if not skip_ad_controls(context):return 'YouTube Skip ad button clicked; the button has disappeared.'
        stop.wait(.08)
    raise ValueError('Skip ad was clicked once, but YouTube did not confirm the change. No repeat click was sent.')


def command(context,request,stop,chooser=None):
    from native_browser import focused,keys
    focused(context,stop);op=request['action']
    if op=='media_skip_ad':return skip_ad(context,stop)
    from system_media import command as system_command
    result=system_command(context,request,stop)
    if result is not None:return result
    row=pick(settled_controls(context,stop),chooser)
    if op in ('media_pause','media_play'):
        desired='pause' if op=='media_pause' else 'play'
        if row['state']!=desired:return 'The observed player is already '+('paused.' if desired=='pause' else 'playing.')
        focus_control(row,context,stop)
        # Re-read after focus: autoplay or another device may have changed state.
        rows=settled_controls(context,stop);identity=tuple(row['element'].element_info.runtime_id)
        current=same_player(rows,identity)
        if not current:raise ValueError('The video player changed before playback input.')
        if current['state']!=desired:return 'The player is already in the requested playback state.'
        click_control(current,context,stop)
        deadline=time.monotonic()+1.5
        while time.monotonic()<deadline:
            check_active(context,stop)
            fresh=same_player(controls(context),identity)
            if fresh and fresh['state']!=desired:return 'Video paused.' if desired=='pause' else 'Video playing.'
            stop.wait(.05)
        raise ValueError('The page did not confirm the playback change. No second toggle was sent.')
    if not re.search(r'youtube',context.get('title',''),re.I) and not re.search(r'\(k\)',row['name'],re.I):
        raise ValueError('YouTube player shortcuts require an observed YouTube player.')
    identity=focus_control(row,context,stop)
    from pywinauto.uia_defines import IUIA
    if op=='media_seek':
        seconds=request['seconds']
        if seconds not in (-10,-5,5,10):raise ValueError('Use a five- or ten-second seek.')
        sequence=['l' if seconds>0 else 'j'] if abs(seconds)==10 else ['right' if seconds>0 else 'left']
    elif op in ('media_next','media_previous'):sequence=['shift','n' if op=='media_next' else 'p']
    else:raise ValueError('Unknown media command')
    check_active(context,stop)
    if tuple(IUIA().iuia.GetFocusedElement().GetRuntimeId())!=identity:raise ValueError('Player focus changed; no media key was sent.')
    keys(context,sequence,stop)
    if op=='media_seek':return 'Sent the YouTube '+str(abs(seconds))+'-second '+('forward' if seconds>0 else 'rewind')+' shortcut.'
    return 'Requested the '+('next' if op=='media_next' else 'previous')+' YouTube video.'

"""Exact browser/video-bound Windows media-session controls; no mouse or keys."""
import asyncio,re,time
from datetime import datetime,timezone


def normalized(text):return re.sub(r'\W+','',text.casefold())


def browser_title(context):
    title=re.sub(r'[\u200b\u200c\u200d\ufeff]','',context.get('title',''))
    title=re.sub(r'\s+[-–—]\s+(?:Google Chrome|Microsoft\s*Edge|Chromium).*$', '',title,flags=re.I)
    return re.split(r'\s+[-–—]\s+YouTube(?:\s+[-–—].*)?$',title,flags=re.I)[0]


def source_matches(source,channel):
    source=source.casefold()
    if channel=='chrome':return source in ('chrome','chrome.exe') or source.endswith('\\chrome.exe')
    if channel=='msedge':return source in ('msedge','msedge.exe') or source.endswith('\\msedge.exe') or source.startswith('microsoft.microsoftedge.')
    return False


def video_title_candidates(context):
    title=browser_title(context)
    candidates={normalized(title)}
    # YouTube prepends an unread-notification count to the tab title, but does
    # not include it in Media Session metadata. Keep the original too: a real
    # video title can itself start with a parenthesized number.
    if re.search(r'\s[-–—]\sYouTube(?:\s[-–—]|$)',context.get('title',''),re.I):
        candidates.add(normalized(re.sub(r'^\(\d+\)\s+','',title)))
    return candidates-{''}


async def find_session(context):
    from routing import browser_channel
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    channel=browser_channel(context);wanted=video_title_candidates(context)
    if not wanted:return None
    manager=await GlobalSystemMediaTransportControlsSessionManager.request_async();matches=[]
    for session in manager.get_sessions():
        if not source_matches(session.source_app_user_model_id,channel):continue
        properties=await session.try_get_media_properties_async()
        if normalized(properties.title) in wanted:matches.append(session)
    return matches[0] if len(matches)==1 else None


def position(session):
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
    timeline=session.get_timeline_properties();info=session.get_playback_info()
    value=timeline.position.total_seconds()
    if info.playback_status==Status.PLAYING:
        updated=timeline.last_updated_time
        if updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
        elapsed=(datetime.now(timezone.utc)-updated).total_seconds()
        if 0<=elapsed<86400:value+=elapsed*(info.playback_rate or 1)
    return max(timeline.start_time.total_seconds(),min(timeline.end_time.total_seconds(),value))


async def execute(session,request,guard):
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
    guard();op=request['action'];info=session.get_playback_info()
    if op in ('media_pause','media_play'):
        desired=Status.PAUSED if op=='media_pause' else Status.PLAYING
        if info.playback_status==desired:return 'Video already '+('paused.' if op=='media_pause' else 'playing.')
        enabled=info.controls.is_pause_enabled if op=='media_pause' else info.controls.is_play_enabled
        if not enabled:return None
        guard()
        accepted=await (session.try_pause_async() if op=='media_pause' else session.try_play_async())
        if not accepted:raise ValueError('Windows declined the video playback request. No toggle fallback was sent.')
        deadline=time.monotonic()+1.5
        while time.monotonic()<deadline:
            guard()
            if session.get_playback_info().playback_status==desired:return 'Video paused (Windows media session).' if op=='media_pause' else 'Video playing (Windows media session).'
            await asyncio.sleep(.05)
        raise ValueError('Windows did not confirm the playback state. No repeated toggle was sent.')
    if op=='media_seek':
        seconds=request.get('seconds')
        if seconds not in (-10,-5,5,10):raise ValueError('Use a five- or ten-second seek.')
        if not info.controls.is_playback_position_enabled:return None
        timeline=session.get_timeline_properties();before=position(session)
        target=max(timeline.start_time.total_seconds(),min(timeline.end_time.total_seconds(),before+seconds))
        guard()
        if not await session.try_change_playback_position_async(round(target*10000000)):
            raise ValueError('Windows declined the seek request. No keyboard fallback was sent.')
        deadline=time.monotonic()+1.5
        while time.monotonic()<deadline:
            guard();actual=position(session)
            if abs(actual-target)<=1.5:return f'Video position {actual:.1f} seconds (Windows media session).'
            await asyncio.sleep(.05)
        raise ValueError('The video did not confirm the requested playback position.')
    return None


def command(context,request,stop):
    if request['action'] not in ('media_pause','media_play','media_seek'):return None
    try:import winrt.windows.media.control
    except ImportError:return None
    def guard():
        import windows_api as win
        if stop.is_set():raise InterruptedError('Stopped')
        if win.foreground()!=context['hwnd'] or win.title(context['hwnd'])!=context['title']:
            raise ValueError('The active browser/video changed. Media input stopped.')
    async def run():
        try:session=await asyncio.wait_for(find_session(context),1.2)
        except (OSError,RuntimeError,asyncio.TimeoutError):return None
        if session is None:return None
        return await execute(session,request,guard)
    try:return asyncio.run(asyncio.wait_for(run(),4))
    except asyncio.TimeoutError:raise ValueError('Windows media control timed out; no repeated input was sent.')

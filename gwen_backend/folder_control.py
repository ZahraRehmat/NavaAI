"""Resolve folder names from the filesystem, never from guessed screen points."""
import os,re,time
from pathlib import Path

def folder_request(task):
    match=re.fullmatch(r'\s*(?:please\s+)?(?:open|launch)\s+(?:the\s+)?(.+?)[.!]?\s*',task,re.I)
    if not match:return None
    label=match[1].strip(); explicit=False
    if re.search(r'\s+folder$',label,re.I):label=re.sub(r'\s+folder$','',label,flags=re.I);explicit=True
    elif re.match(r'folder\s+',label,re.I):label=re.sub(r'^folder\s+','',label,flags=re.I);explicit=True
    label=label.strip().strip('"').strip("'")
    if not label:return None
    if Path(label).is_absolute():explicit=True
    return label,explicit

def known_roots():
    # Registry values honor OneDrive redirection of Desktop/Documents.
    import winreg
    roots=[]
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
        for name in ('Desktop','Personal','{374DE290-123F-4565-9164-39C4925E467B}'):
            try:roots.append(Path(os.path.expandvars(winreg.QueryValueEx(key,name)[0])))
            except OSError:pass
    roots.append(Path(os.environ.get('PUBLIC',r'C:\Users\Public'))/'Desktop')
    return roots

def explorer_folders():
    """Read current Explorer locations, including a verified launch result."""
    import pythoncom,win32com.client
    pythoncom.CoInitialize()
    try:
        result=[]
        for window in win32com.client.Dispatch('Shell.Application').Windows():
            try:
                path=Path(window.Document.Folder.Self.Path)
                if path.is_absolute() and path.is_dir():result.append((int(window.HWND),path))
            except Exception:continue
        return result
    finally:pythoncom.CoUninitialize()

def resolve_folder(label,roots,chooser=None):
    candidate=Path(label)
    if candidate.is_absolute():
        if candidate.is_dir():return candidate.resolve()
        raise ValueError('Folder does not exist: '+label)
    # Named requests search one level only. Never guess partial names or crawl drives.
    if '/' in label or '\\' in label:raise ValueError('Give an absolute folder path or a folder name.')
    from speech_context import CARDINAL
    def name_key(name):
        words=re.findall(r'[a-z0-9]+',name.casefold())
        return ''.join(str(CARDINAL.get(word,word)) for word in words)
    matches={};candidates={}
    for root in roots:
        try:
            root=Path(root)
            if root.is_dir() and name_key(root.name)==name_key(label):matches[str(root.resolve()).casefold()]=root.resolve()
            for child in Path(root).iterdir():
                if child.is_dir():
                    path=child.resolve();candidates[str(path).casefold()]=path
                    if name_key(child.name)==name_key(label):matches[str(path).casefold()]=path
        except OSError:continue
    if len(matches)>1:
        if chooser:
            from target_choices import select_target
            return select_target([{'name':p.name,'path':p} for p in matches.values()],label,chooser=chooser)['row']['path']
        raise ValueError('Multiple folders have this name. Give the full path: '+'; '.join(map(str,matches.values())))
    if matches:return next(iter(matches.values()))
    if chooser:
        from rapidfuzz import fuzz
        ranked=sorted(((fuzz.ratio(name_key(label),name_key(path.name)),path) for path in candidates.values()),key=lambda pair:-pair[0])
        options=[{'label':path.name,'detail':str(path),'match_score':score} for score,path in ranked[:5] if score>=65]
        paths=[path for score,path in ranked[:5] if score>=65]
        if options:
            index=chooser('Which folder did you mean by '+label+'?',options)
            if index is not None and isinstance(index,int) and 0<=index<len(paths):return paths[index]
    return None

def open_requested_folder(task,stop,record,chooser=None):
    request=folder_request(task)
    if not request:return None
    label,explicit=request
    if label.lower() in ('first','second','third','last','next','previous','selected'):return None
    roots=known_roots()
    try:roots.extend(path for _,path in explorer_folders())
    except Exception:pass
    try:path=resolve_folder(label,roots,chooser=chooser)
    except ValueError as exc:return 'Folder lookup stopped: '+str(exc)
    if path is None:
        return 'Could not find the '+label+' folder on Desktop, in Documents/Downloads, or in an open Explorer location. Give its full path.' if explicit else None
    if stop.is_set():return 'Stopped'
    record({'route':'open_folder','path':str(path),'method':'filesystem'})
    os.startfile(str(path),'explore')
    deadline=time.monotonic()+4
    while not stop.is_set() and time.monotonic()<deadline:
        try:
            for hwnd,location in explorer_folders():
                if str(location.resolve()).casefold()==str(path).casefold():
                    record({'folder_open_verified':str(path),'hwnd':hwnd})
                    return 'Opened folder: '+str(path)
        except Exception:break
        stop.wait(.2)
    return 'Stopped' if stop.is_set() else 'Requested Explorer to open '+str(path)+'. The window could not be verified.'

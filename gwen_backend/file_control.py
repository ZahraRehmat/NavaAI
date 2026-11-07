"""Resolve named documents/images from real directory entries, before app/VLM routing."""
import os,re
from pathlib import Path
from catalog import norm
from folder_control import folder_request,known_roots,explorer_folders

DOCUMENTS={'.pdf','.md','.txt','.rtf','.doc','.docx','.odt','.xls','.xlsx','.csv','.ppt','.pptx','.png','.jpg','.jpeg','.gif','.bmp','.webp','.json','.xml','.log'}
DOCUMENTS.update({'.mp4','.mkv','.avi','.mov','.wmv','.webm','.m4v','.mpeg','.mpg','.mp3','.wav','.flac','.m4a','.ogg','.aac'})

def file_scopes(interaction):
    roots=known_roots()
    try:opened=explorer_folders()
    except Exception:opened=[]
    scopes=[]
    if interaction:
        selected=[p for hwnd,p in opened if hwnd==interaction.get('hwnd')]
        if selected:scopes.append(selected)
        elif interaction.get('title')=='Program Manager' and roots:scopes.append([roots[0],roots[-1]])
    scopes.append(roots+[p for _,p in opened])
    return scopes

def resolve_file(label,scopes,chooser=None):
    requested=Path(label);explicit=requested.suffix.lower() in DOCUMENTS
    if requested.is_absolute():
        if requested.is_file() and requested.suffix.lower() in DOCUMENTS:return requested.resolve(),[]
        return None,[]
    if '/' in label or '\\' in label:return None,[]
    suggestions={};query=norm(label)
    # A shared year/day/timestamp is not evidence of a matching filename.
    words={word for word in query.split() if len(word)>=3 and any(c.isalpha() for c in word)}
    for roots in scopes:
        matches={};fuzzy={}
        for root in roots:
            try:children=Path(root).iterdir()
            except OSError:continue
            try:
                for child in children:
                    if not child.is_file() or child.suffix.lower() not in DOCUMENTS:continue
                    key=str(child.resolve()).casefold()
                    exact=child.name.casefold()==label.casefold() if explicit else norm(child.stem)==query
                    if exact:matches[key]=child.resolve()
                    elif explicit and norm(child.stem)==norm(requested.stem):suggestions[key]=child
                    elif len(words & set(norm(child.stem).split()))>=2:suggestions[key]=child
                    if not explicit or child.suffix.lower()==requested.suffix.lower():fuzzy[key]={'name':child.name,'path':child.resolve()}
            except OSError:continue
        if len(matches)>1:
            if chooser:
                from target_choices import select_target
                return select_target([{'name':p.name,'path':p} for p in matches.values()],label,chooser=chooser)['row']['path'],[]
            raise ValueError('Multiple files match. Give the full path: '+'; '.join(map(str,matches.values())))
        if matches:return next(iter(matches.values())),[]
        from label_matching import choose_label,NoLabelMatch,AmbiguousLabel
        try:
            if chooser:
                from target_choices import select_target
                return select_target(list(fuzzy.values()),label,chooser=chooser)['row']['path'],[]
            return choose_label(list(fuzzy.values()),label)['row']['path'],[]
        except NoLabelMatch:pass
        except AmbiguousLabel as exc:raise ValueError('Multiple files match. '+str(exc))
    return None,list(suggestions.values())[:5]

def open_requested_file(task,stop,record,interaction=None,chooser=None):
    request=folder_request(task)
    if not request:return None
    label,_=request
    if Path(label).suffix.lower() not in DOCUMENTS and re.search(r'(?:\s+folder[.!]?\s*$|^\s*(?:please\s+)?(?:open|launch)\s+(?:the\s+)?folder\s+)',task,re.I):return None
    try:path,suggestions=resolve_file(label,file_scopes(interaction),chooser=chooser)
    except ValueError as exc:return 'File lookup stopped: '+str(exc)
    if path is None:
        if suggestions and chooser:
            options=[{'label':p.name,'path':p,'detail':str(p),'match_score':0} for p in suggestions]
            selected=chooser(label+' (suggestions only; check the full name and extension)',options)
            if selected is None:return 'Selection cancelled. Nothing was opened.'
            if isinstance(selected,bool) or not isinstance(selected,int) or not 0<=selected<len(options):return 'Invalid selection. Nothing was opened.'
            path=options[selected]['path']
        elif suggestions:return 'No file exactly matches "'+label+'". Possible files: '+'; '.join(str(p) for p in suggestions)+'. Please choose one.'
        # A named item may be visible in a virtual folder, remote view or app
        # even when absent from the filesystem scopes. Let full-screen vision
        # locate it; the model must ask if it cannot see the target.
        if path is None:return None
    if stop.is_set():return 'Stopped'
    if not path.is_file():return 'The chosen file no longer exists. Nothing was opened.'
    record({'route':'open_file','path':str(path),'method':'filesystem'})
    os.startfile(str(path),'open')
    from label_matching import match_description
    return 'Requested the default app to open: '+str(path)+' '+match_description(label,path.name)

"""Visible target names and ordinary mouse vocabulary for manual smart grid."""
import re
from target_choices import select_target,rank_targets

ALIASES={
    'win':'start','windows':'start','win button':'start','windows button':'start',
    'startup button':'start','start up button':'start','start button':'start','windows start':'start',
    'windows key':'start','win key':'start','start menu':'start',
    'startup':'start','start up':'start','windows logo':'start','windows icon':'start',
    'win icon':'start','start icon':'start','windows start button':'start','startmenu':'start',
    'chrome':'google chrome','google':'google chrome','edge':'microsoft edge','store':'microsoft store',
    'file explorer':'file explorer','explorer':'file explorer','files':'file explorer',
    'vs code':'visual studio code','vscode':'visual studio code','word':'word','excel':'excel',
    'task view button':'task view','notification centre':'notification center',
    'back button':'back','forward button':'forward','home button':'home',
    'up button':'up to','parent folder':'up to','more menu':'more options',
    'taskbar arrow':'show hidden icons','tray arrow':'show hidden icons',
    'hidden icons':'show hidden icons',
}

def parse_named(task):
    from grid_commands import parse
    from direct_commands import normalize_command
    text=normalize_command(task).strip().rstrip('.!')
    parts=re.split(r'\s*;\s*|\s+then\s+|\s+and\s+(?=(?:click|press|select|open|move|hold|release|scroll)\b)',text,flags=re.I)
    if len(parts)>1:
        if len(parts)>12:raise ValueError('Use at most 12 grid steps.')
        result=[]
        for part in parts:
            actions=parse(part,True) or parse_named(part)
            if not actions:raise ValueError('Unrecognized grid step: '+part)
            result.extend(actions)
        return result
    m=re.fullmatch(r'scroll\s+(up|down|left|right)(?:wards?)?(?:\s+(\d+)(?:\s+(?:steps?|times|notches?))?)?\s+(?:on|at|in|from|form|over)\s+(?:the\s+)?(.+)',text,re.I)
    if m:return [{'action':'scroll','direction':m[1].lower(),'amount':int(m[2] or 5),'target_name':m[3].strip()}]
    m=re.fullmatch(r'(double\s+click|right\s+click|middle\s+click|left\s+click|click|press|select|open|hold(?:\s+right)?|move\s+to)\s+(?:(?:on|the)\s+)?(.+)',text,re.I)
    if not m:return None
    op=m[1].lower();op={'press':'click','select':'click','open':'double click','move to':'move'}.get(op,op)
    return [{'action':op,'target_name':m[2].strip()}]

def resolve_name(rows,query,chooser=None):
    query=re.sub(r'\s+',' ',query.lower().strip())
    taskbar=bool(re.search(r'\btask\s*bar\b',query))
    query=re.sub(r'\b(?:on|in|from)\s+(?:the\s+)?task\s*bar\b|\btask\s*bar\b','',query).strip()
    query=re.sub(r'^the\s+','',query);query=ALIASES.get(query,query)
    from dropdown_control import grid_dropdown_name
    specific=grid_dropdown_name(query)
    if specific:
        direct=[row for row in rows if row.get('type')=='ComboBox' and (row.get('dropdown_name')==specific or grid_dropdown_name(row.get('source_name',row['name']))==specific)]
        if len(direct)==1:return direct[0]
        if direct:return select_target(direct,specific,chooser=chooser,merge_overlaps=True)['row']
    candidates=[dict(row,detail=f"{row.get('scope','app')} • {row['label']}") for row in rows]
    # A confident app-name match on the taskbar is the normal way to switch apps.
    bar=[row for row in candidates if row.get('scope')=='taskbar']
    exact_apps=[]
    for row in bar:
        clean=re.split(r'\s+[-—]\s+\d+\s+running\s+windows?\b|\s+pinned\b',row['name'],maxsplit=1,flags=re.I)[0].strip().lower()
        if clean==query:exact_apps.append(row)
    if exact_apps:return select_target(exact_apps,query,chooser=chooser,merge_overlaps=True)['row']
    ranked=rank_targets(bar,query)
    if taskbar or (ranked and ranked[0]['score']>=90):candidates=bar
    return select_target(candidates,query,chooser=chooser,merge_overlaps=True)['row']

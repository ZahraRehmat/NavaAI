"""Deterministic browser tab/media intents, separate from app/window commands."""
import re

NUMBERS={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'sixth':6,'seventh':7,'eighth':8,'ninth':9,'tenth':10}

def intent(task,browser_active=False):
    text=re.sub(r'^\s*(?:please\s+|can you\s+|could you\s+)','',task,flags=re.I).strip().rstrip('.!')
    low=text.lower()
    if re.fullmatch(r'(?:open|add|create|start)?\s*(?:a\s+)?(?:new|another)\s+(?:browser\s+)?tab',low):return {'action':'tab_new'}
    if re.fullmatch(r'close\s+(?:the\s+)?(?:(?:this|current|active|selected)\s+)?(?:browser\s+)?tab',low):return {'action':'tab_close'}
    match=re.fullmatch(r'(?:switch(?:\s+to)?|go(?:\s+to)?|select|open)?\s*(?:the\s+)?(next|previous|prev|last|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+)\s+tab',low)
    if match:return {'action':'tab_switch','target':match[1]}
    low=re.sub(r'\s+please$','',low)
    low=re.sub(r'\s+(?:on|in)\s+youtube$',' youtube',low)
    low=re.sub(r'\bvideo\s+youtube$','youtube video',low)
    match=re.fullmatch(r'(?:switch(?:\s+(?:back\s+)?to)?|go\s+to|select|open)\s+(?:the\s+)?(?:browser\s+)?tab\s+(.+)',text,re.I)
    if not match:match=re.fullmatch(r'(?:switch(?:\s+(?:back\s+)?to)?|go\s+to|select|open)\s+(?:the\s+)?(.+?)\s+tab',text,re.I)
    if match:return {'action':'tab_switch','target':match[1]}
    if browser_active:
        implicit=re.fullmatch(r'(?:switch\s+(?:back\s+)?to|go\s+to\s+tab)\s+(.+)',text,re.I)
        if implicit:return {'action':'tab_switch','target':implicit[1],'implicit':True}
    match=re.fullmatch(r'(pause|play|resume|stop)\s*(?:(?:the|this|current)\s+)?(?:(youtube)(?:\s+video)?|video|playback|media)?',low)
    if match and (browser_active or match[2] or re.search(r'video|playback|media',low)):
        return {'action':'media_pause' if match[1] in ('pause','stop') else 'media_play','site':'youtube' if match[2] else None}
    return None

def tab_index(target,rows,current=0,chooser=None):
    key=target.lower().strip()
    key=re.sub(r'^(?:number|no\.)\s+','',key)
    if not rows:raise ValueError('No browser tabs were observed.')
    if key=='next':return (current+1)%len(rows)
    if key in ('previous','prev'):return (current-1)%len(rows)
    if key=='last':return len(rows)-1
    number=NUMBERS.get(key,int(key) if key.isdigit() else None)
    if number is not None:
        if not 1<=number<=len(rows):raise ValueError(f'There are {len(rows)} observed tabs; tab {number} is unavailable.')
        return number-1
    from target_choices import select_target
    chosen=select_target(rows,target,chooser=chooser)['row']
    return next(i for i,row in enumerate(rows) if row is chosen)

"""Immediate mouse/keyboard commands; no model inference for basic input."""
import re

def normalize_command(text):
    text=text.strip()
    text=re.sub(r'^(?:please\s+|can you\s+|could you\s+)','',text,flags=re.I)
    fixes={'sroll':'scroll','scrol':'scroll','scrll':'scroll','clikc':'click','clik':'click','cick':'click','clk':'click','tpye':'type','typclick':'click','boild':'bold','bould':'bold','insertt':'insert'}
    m=re.match(r'(\S+)(.*)',text,re.S)
    if m: text=fixes.get(m[1].lower(),m[1])+m[2]
    text=re.sub(r'\bherte\b','here',text,flags=re.I)
    return text

def parse_direct(text):
    text=normalize_command(text)
    simple=text.lower().strip().rstrip('.!')
    m=re.fullmatch(r'scroll\s+(up|down|left|right)(?:\s+(a little|a bit|a lot|more|\d+)(?:\s+(pages?|steps?|times))?)?',simple)
    if m:
        direction,size,unit=m.groups(); steps=2 if size in ('a little','a bit') else 12 if size=='a lot' else int(size) if size and size.isdigit() else 5
        if unit and unit.startswith('page'): steps*=5
        return {'kind':'scroll','direction':direction,'steps':min(20,max(1,steps))}
    m=re.fullmatch(r'(click|left click|double click|right click|tap)(?:\s+(?:here|there|this|at (?:the )?cursor|where the mouse is))?',simple)
    if m: return {'kind':'pointer','action':{'double click':'double_click','right click':'right_click'}.get(m[1],'click')}
    m=re.fullmatch(r'(?:type|write|dictate)\s+(.+)',text,re.S|re.I)
    if m:
        value=m[1]
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"): value=value[1:-1]
        return {'kind':'type','text':value}
    shortcuts={'select all':['ctrl','a'],'copy':['ctrl','c'],'paste':['ctrl','v'],'undo':['ctrl','z'],'redo':['ctrl','y'],
               'go back':['alt','left'],'back':['alt','left'],'go forward':['alt','right'],'forward':['alt','right'],
               'go home':['alt','home'],'go up':['alt','up']}
    if simple in shortcuts: return {'kind':'keys','keys':shortcuts[simple]}
    m=re.fullmatch(r'(?:press|hit)\s+(.+)',simple)
    if m:
        aliases={'control':'ctrl','escape':'esc','return':'enter','spacebar':'space','delete':'delete'}
        keys=[aliases.get(k.strip(),k.strip()) for k in re.split(r'\s*\+\s*|\s+and\s+',m[1])]
        if len(keys)==1 and ' ' in keys[0]: keys=keys[0].split()
        keys=[aliases.get(k,k) for k in keys]
        if keys in (['page','down'],['page','up']): keys=[''.join(keys)]
        return {'kind':'keys','keys':keys}
    return None

def is_question(text):
    return bool(re.match(r'^(?:question\b|chat\b|hello\b|hi\b|how\b|what\b|who\b|why\b|where\b|explain\b|tell me\b)',text.strip(),re.I))

def is_action_request(text):
    text=normalize_command(text)
    if text.lower() in ('quit','exit','close this','close it'):return True
    if re.match(r'^(?:quit|exit|stop|kill|terminate|force\s+(?:close|quit|stop))\s+\S',text,re.I):return True
    if parse_direct(text): return True
    if text.casefold() in ('bold','unbold','italic','italicize','underline'):return True
    if re.match(r'^(?:bold|unbold|italic|italicize|underline|insert|add|make|format)\s+\S',text,re.I):return True
    return bool(re.match(r'^(?:open|launch|start|search|find|look up|go to|visit|navigate to|click(?: on)?|double click|right click|select|move|drag|close|fill|replace|install|download|read|summarize|save|switch|refresh|play|pause|increase|decrease|scroll|type|press|copy|paste|cut|undo|redo|delete|send|write|create|organize|sort|extract|upload|rename|resize|minimize|maximize)\s+\S',text.strip(),re.I))

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
    simple=text.lower().strip().rstrip('.! ').strip()
    if re.fullmatch(r'copy\s+(?:(?:it|this|the text)\s+)?to\s+(?:the\s+)?clipboard',simple):return {'kind':'keys','keys':['ctrl','c']}
    if not re.match(r'^(?:type|write|dictate)\b',text,re.I):
        from selection_commands import range_command
        selection=range_command(text)
        if selection:return selection
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
    if re.fullmatch(r'(?:punctuate|add punctuation(?: to)?)(?:\s+(?:it|this|that|the text|this text|the written text))?',simple):return {'kind':'punctuate'}
    if re.fullmatch(r'(?:backspace|back space|erase(?:\s+(?:it|that|the last word|last word))?|delete\s+(?:the\s+)?last\s+word)',simple):return {'kind':'keys','keys':['ctrl','backspace']}
    if re.fullmatch(r'paste\s+(?:here|in\s+(?:this|the)\s+(?:field|box|typing bar))',simple):return {'kind':'keys','keys':['ctrl','v']}
    if re.fullmatch(r'paste\s+(?:(?:it|this|the copied data|the copied text)\s+)?(?:here|(?:to|in)\s+(?:this|the)\s+(?:field|box|typing bar))',simple):return {'kind':'keys','keys':['ctrl','v']}
    m=re.fullmatch(r'select\s+(?:the\s+text\s+)?from\s+(.+?)\s+(?:to|through|until)\s+(.+)',text.rstrip('.!'),re.I)
    if m:return {'kind':'select_text','start':m[1].strip('"\''),'end':m[2].strip('"\'')}
    m=re.fullmatch(r'(increase|decrease|enlarge|shrink)\s+(?:the\s+)?(?:font|text)(?:\s+size)?',simple)
    if m:return {'kind':'font_delta','direction':1 if m[1] in ('increase','enlarge') else -1}
    m=re.fullmatch(r'(?:make\s+)?(?:the\s+)?(?:font|text)(?:\s+size)?\s+(bigger|larger|smaller)',simple)
    if m:return {'kind':'font_delta','direction':-1 if m[1]=='smaller' else 1}
    # Only the command slot is normalized; dictated payloads above stay literal.
    if re.fullmatch(r'paste\s+(?:what\s+i\s+(?:copied|cut)|(?:the\s+)?copy\s+(?:data|text|content))',simple):
        return {'kind':'keys','keys':['ctrl','v']}
    simple=re.sub(r'\b(?:it|that|this|the|stuff|thing|text|selected|selection|copied|data|content|clipboard)\b',' ',simple)
    simple=' '.join(simple.split())
    shortcuts={'select all':['ctrl','a'],'copy':['ctrl','c'],'paste':['ctrl','v'],'undo':['ctrl','z'],'redo':['ctrl','y'],
               'cut':['ctrl','x'],'enter':['enter'],'new line':['enter'],'next line':['enter'],
               'go back':['alt','left'],'back':['alt','left'],'go forward':['alt','right'],'forward':['alt','right'],
               'go home':['alt','home'],'go up':['alt','up']}
    if simple in shortcuts: return {'kind':'keys','keys':shortcuts[simple]}
    m=re.fullmatch(r'(?:press|hit)\s+(.+)',simple)
    if m:
        key_text=re.sub(r'\b(?:key|button)\b',' ',m[1]).strip()
        key_text=re.sub(r'\bback\s+space\b','backspace',key_text)
        key_text=re.sub(r'\bspace\s+bar\b','spacebar',key_text)
        aliases={'control':'ctrl','escape':'esc','return':'enter','spacebar':'space','delete':'delete'}
        keys=[aliases.get(k.strip(),k.strip()) for k in re.split(r'\s*\+\s*|\s+and\s+',key_text)]
        if len(keys)==1 and ' ' in keys[0]: keys=keys[0].split()
        keys=[aliases.get(k,k) for k in keys]
        if keys in (['page','down'],['page','up']): keys=[''.join(keys)]
        return {'kind':'keys','keys':keys}
    return None

def is_question(text):
    return bool(re.match(r'^(?:question\b|chat\b|hello\b|hi\b|how\b|what\b|who\b|why\b|where\b|explain\b|tell me\b)',text.strip(),re.I))

def is_action_request(text):
    text=normalize_command(text)
    from dropdown_control import dropdown_intent,missing_target
    if dropdown_intent(text) or missing_target(text):return True
    if text.lower() in ('quit','exit','close this','close it','minimize','minimise','maximize','maximise','restore'):return True
    if re.match(r'^(?:minimi[sz]e|maximi[sz]e|restore)\s+',text,re.I):return True
    if re.match(r'^(?:quit|exit|stop|kill|terminate|force\s+(?:close|quit|stop))\s+\S',text,re.I):return True
    if parse_direct(text): return True
    if text.casefold() in ('bold','unbold','italic','italicize','underline'):return True
    if re.match(r'^(?:bold|unbold|italic|italicize|underline|insert|add|make|format)\s+\S',text,re.I):return True
    return bool(re.match(r'^(?:open|launch|start|search|find|look up|go to|visit|navigate to|click(?: on)?|double click|right click|select|move|drag|close|fill|replace|install|download|read|summarize|save|switch|refresh|play|pause|increase|decrease|scroll|type|press|copy|paste|cut|undo|redo|delete|send|write|create|organize|sort|extract|upload|rename|resize|minimize|maximize)\s+\S',text.strip(),re.I))

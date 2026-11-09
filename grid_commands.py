"""Smart-grid activation and direct mouse commands. Never invokes Qwen."""
import re
from direct_commands import normalize_command

LABEL=r'(?:M\d+-)?[A-Z]{1,6}\s*\d{0,3}'

def toggle_intent(task):
    text=normalize_command(task).lower().strip().rstrip('.!?')
    text=re.sub(r'^(?:gwen|guen|glen|glenn)\s+','',text)
    text=re.sub(r'^please\s+|\s+(?:please|now)$','',text)
    text=re.sub(r'\b(?:griud|gruid|grdi|gird)\b','grid',text)
    text=re.sub(r'\b(?:turhn|trun|turm)\b','turn',text)
    target=r'(?:the\s+)?(?:(?:smart|auto|automatic|full)\s*)?grid'
    if re.fullmatch(r'(?:(?:close|hide|disable|stop|exit|remove|deactivate)\s+'+target+r'|(?:turn|switch)\s+(?:off|of)\s+'+target+r'|(?:turn|switch)\s+'+target+r'\s+(?:off|of)|'+target+r'\s*(?:off|close|hide|disable|stop|exit))',text):return 'disable'
    if re.fullmatch(r'(?:(?:open|show|enable|start|activate|launch|bring up)\s+'+target+r'|(?:turn|switch|put)\s+on\s+'+target+r'|(?:turn|switch|put)\s+'+target+r'\s+on|'+target+r'(?:\s*(?:on|mode|open|show|start|enable))?)',text):return 'smart_unavailable'
    return None

def parse(task,active=False):
    toggle=toggle_intent(task)
    if toggle:return [{'action':toggle}]
    raw=normalize_command(task).strip().rstrip('.!')
    raw=re.sub(r'\b(?:doubkle|duble)\b','double',raw,flags=re.I)
    raw=re.sub(r'\b(?:lcick|clikc|clik)\b','click',raw,flags=re.I);text=raw.lower()
    if not active:return None
    from dropdown_control import dropdown_intent,missing_target
    if missing_target(raw):return [{'action':'dropdown_prompt'}]
    dropdown=dropdown_intent(raw)
    if dropdown:
        if re.fullmatch(LABEL,dropdown,re.I):return [{'action':'expand','label':dropdown}]
        return [{'action':'expand','target_name':dropdown}]
    chain_raw=raw
    raw=re.sub(r'^(?:please\s+)?(?:press|select)\b','click',raw,flags=re.I)
    raw=re.sub(r'^(?:please\s+)?open\b','double click',raw,flags=re.I)
    text=raw.lower()
    if text in ('stop','cancel','emergency stop'):return [{'action':'disable'}]
    parts=re.split(r'\s*;\s*|\s+then\s+|\s+and\s+(?=(?:move|release|drop|click|hold|press|select|open|scroll)\b)',chain_raw,flags=re.I)
    if len(parts)>1:
        if len(parts)>12:raise ValueError('Use at most 12 mouse steps in one command.')
        result=[]
        for part in parts:
            actions=parse(part,True)
            if actions is None:raise ValueError('Unrecognized grid step: '+part)
            result.extend(actions)
        return result
    if text in ('reset grid','grid reset','refresh grid'):return [{'action':'reset'}]
    match=re.fullmatch(r'(?:drag)\s+('+LABEL+r')\s+(?:to|onto)\s+('+LABEL+r')',raw,re.I)
    if match:return [{'action':'drag','source':match[1],'label':match[2]}]
    match=re.fullmatch(r'(?:move(?:\s+(?:mouse|cursor))?\s+(?:to\s+)?)?(?:pixel|point)\s+(-?\d+)\s*[, ]\s*(-?\d+)',text)
    if match:return [{'action':'pixel','x':int(match[1]),'y':int(match[2])}]
    match=re.fullmatch(r'(?:move|nudge)(?:\s+(?:mouse|cursor))?\s+(left|right|up|down)(?:\s+(\d+)(?:\s*(?:px|pixels?))?)?',text)
    if match:return [{'action':'nudge','direction':match[1],'amount':int(match[2] or 40)}]
    # Accept natural location words, an omitted preposition, and common joined
    # typing mistakes ("formfg"). A scroll never inherits bare-label clicking.
    location=re.fullmatch(r'(?:from|form|on|at|in|over)\s*('+LABEL+r')\s+scroll\s+(up|down|left|right)(.*)',raw,re.I)
    if location:raw='scroll '+location[2]+location[3]+' from '+location[1]
    match=re.fullmatch(r'scroll\s+(up|down|left|right)(?:wards?)?(?:\s+(\d+|a little|a bit|a lot)(?:\s+(?:steps?|times|notches?))?)?(?:\s+(?:(?:on|at|in|from|form|over)\s*)?(?:the\s+)?('+LABEL+r'))?(?:\s+(\d+)(?:\s+(?:steps?|times|notches?))?)?',raw,re.I)
    if match:
        size=match[2] or match[4] or '5'
        amount=2 if size.lower() in ('a little','a bit') else 12 if size.lower()=='a lot' else int(size)
        return [{'action':'scroll','direction':match[1].lower(),'amount':amount,'label':match[3]}]
    match=re.fullmatch(r'(click|left click|double[ -]?click|right[ -]?click|middle click|hold|hold left|hold right|release|drop)(?:\s+(?:on|at|to))?(?:\s+('+LABEL+r'))?',raw,re.I)
    if match:return [{'action':match[1].lower().replace('-',' '),'label':match[2]}]
    match=re.fullmatch(r'('+LABEL+r')',raw,re.I)
    if match:return [{'action':'click','label':match[1],'bare_label':True}]
    match=re.fullmatch(r'(?:move|go|mouse|cursor|teleport)(?:\s+(?:mouse|cursor))?(?:\s+to)?\s+('+LABEL+r')',raw,re.I)
    if match:return [{'action':'move','label':match[1]}]
    return None

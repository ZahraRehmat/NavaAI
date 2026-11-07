"""Explicit mouse vocabulary for manual full-grid mode. Never invokes Qwen."""
import re
from direct_commands import normalize_command

LABEL=r'(?:M\d+-)?[A-Z]{1,3}\s*\d{0,3}'

def parse(task,active=False):
    raw=normalize_command(task).strip().rstrip('.!')
    raw=re.sub(r'\b(?:doubkle|duble)\b','double',raw,flags=re.I)
    raw=re.sub(r'\b(?:lcick|clikc|clik)\b','click',raw,flags=re.I);text=raw.lower()
    if re.fullmatch(r'(?:gwen\s+)?(?:show|enable|start|activate)?\s*(?:the\s+)?full\s+grid(?:\s+(?:on|mode))?',text):return [{'action':'enable'}]
    if re.fullmatch(r'(?:gwen\s+)?(?:(?:show|enable|start|activate)\s+)?(?:the\s+)?(?:smart\s+)?grid(?:\s+(?:on|mode))?',text):return [{'action':'smart_unavailable'}]
    if text in ('exit grid','exit full grid','hide grid','grid off','full grid off','stop grid','gwen stop grid','gwen exit grid'):return [{'action':'disable'}]
    if not active:return None
    raw=re.sub(r'^(?:please\s+)?(?:press|select)\b','click',raw,flags=re.I)
    raw=re.sub(r'^(?:please\s+)?open\b','double click',raw,flags=re.I)
    text=raw.lower()
    if text in ('stop','cancel','emergency stop'):return [{'action':'disable'}]
    parts=re.split(r'\s*;\s*|\s+then\s+|\s+and\s+(?=(?:move|release|drop|click|hold|press|select|open|scroll)\b)',raw,flags=re.I)
    if len(parts)>1:
        if len(parts)>12:raise ValueError('Use at most 12 mouse steps in one command.')
        result=[]
        for part in parts:
            actions=parse(part,True)
            if actions is None:raise ValueError('Unrecognized grid step: '+part)
            result.extend(actions)
        return result
    if text in ('reset grid','full screen','grid reset','refresh grid'):return [{'action':'reset'}]
    if text in ('zoom out','grid back','back grid'):return [{'action':'back'}]
    match=re.fullmatch(r'(?:zoom(?:\s+(?:in|into|on))?|refine)\s+('+LABEL+r')',raw,re.I)
    if match:return [{'action':'zoom','label':match[1]}]
    match=re.fullmatch(r'grid\s+(?:size|density)\s+(\d+)\s*(?:by|x)\s*(\d+)',text)
    if match:return [{'action':'density','columns':int(match[1]),'rows':int(match[2])}]
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

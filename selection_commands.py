"""Selection-mode phrases stay separate from dictation and grid labels."""
import re

ON={'selection','selection mode','start selection','select text','start selecting'}
OFF={'stop selection','end selection','cancel selection','exit selection','finish selection'}


def range_command(text,mode=False):
    text=text.strip().rstrip('.! ')
    match=re.fullmatch(r'(?:select\s+and\s+copy|copy|selection)\s+(?:from\s+)?(.+?)\s+(?:to|through|until)\s+(.+)',text,re.I)
    if not match and mode:
        match=re.fullmatch(r'(?:select\s+)?(?:from\s+)?(.+?)\s+(?:to|through|until)\s+(.+)',text,re.I)
    if not match:return None
    start,end=(v.strip().strip('"\'') for v in match.groups())
    if not start or not end:return None
    return {'kind':'select_text','start':start,'end':end,'copy':True,'screen':True}


def canonical(command):
    return 'select and copy from '+command['start']+' to '+command['end']

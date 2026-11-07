"""Reject malformed model actions before any input is sent."""
import math

POINTS={'click','move','double_click','right_click','drag'}
IDS={'ui_click','ui_fill','browser_click','browser_fill','browser_select','browser_check','browser_hover','browser_upload'}
KNOWN=POINTS|IDS|{'type','hotkey','press','scroll','open_app','open_browser','desktop_mode','browser_mode','wait','confirm','navigate','browser_press','browser_scroll','browser_back','browser_tab','browser_new_tab','browser_close_tab','browser_read','done','ask'}

def number(value,field):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f'{field} must be a finite scalar number; arrays and strings are invalid')
    return value

def validate_action(a):
    if not isinstance(a,dict) or a.get('action') not in KNOWN: raise ValueError('Unknown action')
    op=a['action']
    if op in POINTS:
        for key in ('x','y'):
            v=number(a.get(key),key)
            if not 0<=v<=1000: raise ValueError('Coordinates must be between 0 and 1000')
    if op in IDS or op=='browser_tab':
        key='index' if op=='browser_tab' else 'id'
        if type(a.get(key)) is not int or a[key]<0: raise ValueError(key+' must be a nonnegative integer')
    for field,ops in {'text':{'type','ui_fill','browser_fill'},'name':{'open_app'},'key':{'press','browser_press'},'url':{'navigate'},'path':{'browser_upload'},'value':{'browser_select'}}.items():
        if op in ops and not isinstance(a.get(field),str): raise ValueError(field+' must be text')
    if op=='hotkey' and (not isinstance(a.get('keys'),list) or not a['keys'] or any(not isinstance(k,str) for k in a['keys'])): raise ValueError('keys must be a list of key names')
    if op in ('scroll','browser_scroll'): number(a.get('amount'),'amount')
    if op=='wait': number(a.get('seconds',1),'seconds')
    if op=='confirm':
        if not isinstance(a.get('message'),str) or a.get('next_action',{}).get('action')=='confirm': raise ValueError('Invalid confirmation')
        validate_action(a.get('next_action'))
    return a

def fingerprint(a):
    import json
    return json.dumps({k:v for k,v in a.items() if k not in ('reason','message')},sort_keys=True)

"""Keyboard commands coexist with grids; labels remain mouse commands."""
import re
from direct_commands import parse_direct,normalize_command

def keyboard_command(task):
    text=normalize_command(task)
    from window_commands import intent
    window=intent(text)
    if window and window['action'] in ('close_window','close_named','force_close_window','force_close_named','switch_window'):return True
    direct=parse_direct(text)
    if not direct:return False
    if direct['kind']=='type':return True
    if direct['kind']!='keys':return False
    # "press F" is a grid click, whereas "press enter" is a keyboard action.
    keys=direct['keys']
    special={'enter','tab','esc','backspace','delete','space','up','down','left','right','home','end','pageup','pagedown','insert'}
    valid=lambda k:k in special|{'ctrl','alt','shift'} or bool(re.fullmatch(r'[a-z0-9]|f(?:[1-9]|1\d|2[0-4])',k))
    return all(valid(k) for k in keys) and (len(keys)>1 or any(k in special for k in keys))

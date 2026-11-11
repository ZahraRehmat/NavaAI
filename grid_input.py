"""Keyboard commands coexist with grids; labels remain mouse commands."""
import re
from direct_commands import parse_direct,normalize_command

def keyboard_command(task,context=None):
    text=normalize_command(task)
    from grid_commands import toggle_intent
    if toggle_intent(text):return False
    from dropdown_control import missing_target
    if missing_target(text):return True
    from excel_commands import parse as parse_excel
    from office_control import office_kind
    if office_kind(context)=='excel' and parse_excel(text):return True
    from routing import website_intent
    if website_intent(text):return True
    from browser_commands import intent as browser_intent
    if browser_intent(text,browser_active=False):return True
    from window_commands import intent
    window=intent(text)
    if window and window['action'] in ('close_window','close_named','force_close_window','force_close_named','switch_window','minimize_window','maximize_window','restore_window','minimize_named','maximize_named','restore_named'):return True
    direct=parse_direct(text)
    if not direct:return False
    if direct['kind'] in ('type','select_text','font_delta','punctuate'):return True
    if direct['kind']!='keys':return False
    # "press F" is a grid click, whereas "press enter" is a keyboard action.
    keys=direct['keys']
    special={'enter','tab','esc','backspace','delete','space','up','down','left','right','home','end','pageup','pagedown','insert'}
    valid=lambda k:k in special|{'ctrl','alt','shift'} or bool(re.fullmatch(r'[a-z0-9]|f(?:[1-9]|1\d|2[0-4])',k))
    return all(valid(k) for k in keys) and (bool(set(keys)&{'ctrl','alt','shift'}) or (len(keys)==1 and (keys[0] in special or bool(re.fullmatch(r'f(?:[1-9]|1\d|2[0-4])',keys[0])))))

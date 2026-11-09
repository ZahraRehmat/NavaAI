import ctypes, io, time
ctypes.windll.user32.SetProcessDPIAware()
import pyautogui as pg
import pyperclip
from PIL import Image
import windows_api

pg.FAILSAFE=True
pg.PAUSE=0.2

def foreground_title():
    return windows_api.title(windows_api.foreground())

def foreground_handle(): return windows_api.stable_foreground()

def screen_bounds():
    width,height=pg.size()
    return (0,0,width,height)

def window_bounds(hwnd):
    x1,y1,x2,y2=windows_api.rect(hwnd)
    w,h=pg.size()
    left,top=max(0,x1),max(0,y1)
    right,bottom=min(w,x2),min(h,y2)
    if right<=left or bottom<=top: raise ValueError('Target window is outside the primary display')
    return (left,top,right,bottom)

def capture(bounds=None, resize=True):
    region=(bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1]) if bounds else None
    image=pg.screenshot(region=region).convert('RGB')
    if not resize: return image
    image.thumbnail((1280,800))
    return image

def map_point(x,y,bounds):
    left,top,right,bottom=bounds
    return (min(right-1,left+round(x*(right-left)/1000)),min(bottom-1,top+round(y*(bottom-top)/1000)))

def act(a,bounds=None):
    from actions import validate_action
    validate_action(a)
    op=a['action']
    if op in ('click','move','double_click','right_click','drag'):
        # Coordinates map to the observation bounds (full screen for VLM actions).
        x,y=float(a['x']),float(a['y'])
        if not (0<=x<=1000 and 0<=y<=1000): raise ValueError('Coordinates must be 0..1000')
        if bounds is None:
            w,h=pg.size(); bounds=(0,0,w,h)
        x,y=map_point(x,y,bounds)
        if op=='move': pg.moveTo(x,y,duration=.2)
        elif op=='drag': pg.dragTo(x,y,duration=.6)
        else: pg.click(x,y,clicks=2 if op=='double_click' else 1,interval=.1,button='right' if op=='right_click' else 'left')
    elif op=='type':
        text=str(a['text'])
        if len(text)>20000: raise ValueError('Text exceeds 20,000 characters')
        # Clipboard pasting supports Unicode. Preserve the user's text clipboard.
        old=pyperclip.paste()
        try:
            pyperclip.copy(text); pg.hotkey('ctrl','v'); time.sleep(.25)
        finally: pyperclip.copy(old)
    elif op=='hotkey':
        keys=a['keys']
        if not isinstance(keys,list) or not 1<=len(keys)<=5 or any(k not in pg.KEYBOARD_KEYS for k in keys): raise ValueError('Invalid keyboard keys')
        pg.hotkey(*keys)
    elif op=='press':
        if a['key'] not in pg.KEYBOARD_KEYS: raise ValueError('Invalid key')
        pg.press(a['key'])
    elif op=='scroll': pg.scroll(max(-20,min(20,int(a['amount']))))
    else: raise ValueError('Unknown desktop action: '+op)
    return 'Desktop action completed'

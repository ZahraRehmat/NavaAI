"""Unicode keyboard packets for ordinary dictation, preserving the whole clipboard."""
import ctypes,time
from ctypes import wintypes as w


class Keyboard(ctypes.Structure):
    _fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
class Mouse(ctypes.Structure):
    _fields_=[('x',w.LONG),('y',w.LONG),('data',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
class Payload(ctypes.Union):
    _fields_=[('keyboard',Keyboard),('mouse',Mouse)]
class Input(ctypes.Structure):
    _fields_=[('kind',w.DWORD),('payload',Payload)]


def packets(text):
    encoded=text.encode('utf-16-le')
    for index in range(0,len(encoded),2):
        unit=int.from_bytes(encoded[index:index+2],'little')
        for flags in (4,6):yield Input(1,Payload(keyboard=Keyboard(0,unit,flags,0,0)))


def type_unicode(text,hwnd,stop=None):
    import windows_api as win
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.SendInput.argtypes=[w.UINT,ctypes.POINTER(Input),ctypes.c_int];user.SendInput.restype=w.UINT
    # Modern RichEdit/UWP editors can coalesce a burst of VK_PACKET messages
    # into repeated final characters. Deliver a complete Unicode character at
    # a time and let the target pump its input queue between characters.
    for index,char in enumerate(text):
        if stop and stop.is_set():raise InterruptedError('Stopped')
        if win.foreground()!=hwnd:raise ValueError('Active app changed during typing. Remaining text was stopped.')
        batch=list(packets(char));buffer=(Input*len(batch))(*batch)
        if user.SendInput(len(batch),buffer,ctypes.sizeof(Input))!=len(batch):
            raise RuntimeError('Windows blocked some typing input. Inspect the field before retrying.')
        if index+1<len(text):
            if stop:
                if stop.wait(.008):raise InterruptedError('Stopped')
            else:time.sleep(.008)

"""Disposable native Win32 accessibility surface; never opens user content."""
import ctypes,json
from ctypes import wintypes as w
from grid_display import enable_dpi_awareness
enable_dpi_awareness()
u=ctypes.WinDLL('user32',use_last_error=True);k=ctypes.WinDLL('kernel32',use_last_error=True)
PROC=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
class WC(ctypes.Structure):
    _fields_=[('style',w.UINT),('proc',PROC),('cls',ctypes.c_int),('wnd',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
u.DefWindowProcW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];u.DefWindowProcW.restype=ctypes.c_ssize_t
u.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID];u.CreateWindowExW.restype=w.HWND
u.SetWindowTextW.argtypes=[w.HWND,w.LPCWSTR]
u.MoveWindow.argtypes=[w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.BOOL]
k.GetModuleHandleW.argtypes=[w.LPCWSTR];k.GetModuleHandleW.restype=w.HMODULE
controls={};events=[]
def child(kind,text,x,y,width,height,number):
    handle=u.CreateWindowExW(0,kind,text,0x50010000,x,y,width,height,root,w.HMENU(number),instance,None)
    controls[number]=handle;return handle
@PROC
def proc(hwnd,msg,wp,lp):
    if msg==0x111:
        number=wp&65535;events.append(number)
        if number==101:
            u.MoveWindow(controls[102],500,300,160,60,True)
            if 104 not in controls:child('BUTTON','New target',30,300,160,60,104)
            u.SetWindowTextW(controls[105],'Target moved; its label should stay stable.')
        elif number in (102,104):
            u.SetWindowTextW(controls[105],'PASS: '+('moved destination' if number==102 else 'new target')+' clicked')
        from pathlib import Path
        Path('diagnostics/smart-grid-native-events.json').write_text(json.dumps({'events':events}))
        return 0
    if msg==2:u.PostQuitMessage(0);return 0
    return u.DefWindowProcW(hwnd,msg,wp,lp)
instance=k.GetModuleHandleW(None);wc=WC(0,proc,0,0,instance,None,None,w.HBRUSH(6),None,'GwenSmartTest')
u.RegisterClassW(ctypes.byref(wc))
root=u.CreateWindowExW(0,wc.name,'Gwen Smart Grid Test Surface',0x10cf0000,100,100,820,560,None,None,instance,None)
child('BUTTON','Move target',30,80,160,60,101)
child('BUTTON','Destination',300,150,160,60,102)
child('EDIT','Test input',230,80,240,30,103)
child('STATIC','Own disposable test surface.',30,20,700,35,105)
u.ShowWindow(root,5)
print(json.dumps({'ready':True,'hwnd':root}),flush=True)
msg=w.MSG()
while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:u.TranslateMessage(ctypes.byref(msg));u.DispatchMessageW(ctypes.byref(msg))

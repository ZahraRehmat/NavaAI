"""Isolated Save/Don't Save fixture. Guarded against invoking any other window."""
import ctypes,json,queue,threading
from ctypes import wintypes as w
from pathlib import Path
from unittest.mock import patch
ctypes.windll.user32.SetProcessDPIAware()
import tkinter as tk
from tkinter import ttk
import windows_api as win
from agent import Agent
from accessibility import NativeControls

root=tk.Tk();root.title('Gwen Dialog Test');root.geometry('640x330+160+160');root.attributes('-topmost',True)
status=tk.StringVar(value='Start the isolated scratch dialog test. No workbook is used.')
ttk.Label(root,text='Save-dialog focus test',font=('Segoe UI',19,'bold')).pack(pady=15)
ttk.Label(root,textvariable=status,wraplength=580).pack(padx=15,pady=12)
user=ctypes.WinDLL('user32',use_last_error=True)
user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
user.GetDlgItem.argtypes=[w.HWND,ctypes.c_int];user.GetDlgItem.restype=w.HWND
user.SetWindowTextW.argtypes=[w.HWND,w.LPCWSTR];user.SetWindowTextW.restype=w.BOOL
user.MessageBoxW.argtypes=[w.HWND,w.LPCWSTR,w.LPCWSTR,w.UINT];user.MessageBoxW.restype=ctypes.c_int
root.update_idletasks();owner=user.GetParent(root.winfo_id()) or root.winfo_id()
events=queue.Queue();rows=[];actions={};stage=0;active_popup=None;started=False;executing=False;agent=None
def open_box():
    result=user.MessageBoxW(owner,'This dialog belongs only to the Gwen test. No document or user data is saved/discarded.','Gwen Scratch Save Dialog',3)
    events.put(('response',result))
def start():
    global started
    if started:return
    started=True;button.configure(state='disabled');threading.Thread(target=open_box,daemon=True).start()
def run_command(popup,command):
    global agent
    agent=Agent(log=lambda s:events.put(('log',s)))
    original=NativeControls.act
    def guarded(probe,action):
        if probe.hwnd!=popup:raise AssertionError('Blocked action outside the scratch dialog')
        return original(probe,action)
    context={'hwnd':owner,'title':root.title(),'bounds':win.rect(owner),'pointer':win.cursor()}
    with patch.object(NativeControls,'act',guarded):result=agent.run(command,interaction=context)
    events.put(('action',(command,result)));agent.close()
button=ttk.Button(root,text='Start isolated test',command=start);button.pack(pady=20)
def poll():
    global active_popup,executing,stage
    if started and not executing:
        popup=win.action_window(owner)
        if popup!=owner and popup and win.user.IsWindowVisible(popup):
            active_popup=popup;executing=True
            user.SetWindowTextW(user.GetDlgItem(popup,6),'Save')
            user.SetWindowTextW(user.GetDlgItem(popup,7),"Don't Save")
            command='click dont save' if stage==0 else 'click save'
            threading.Thread(target=run_command,args=(popup,command),daemon=True).start()
    try:
        while True:
            kind,value=events.get_nowait()
            if kind=='log':status.set(value[:150])
            elif kind=='response':
                expected=7 if stage==0 else 6
                command='click dont save' if stage==0 else 'click save'
                action_result=actions.get(command,'pending')
                rows.append({'command':command,'dialog_response':value,'expected_response':expected,'action_result':action_result,'passed':value==expected and action_result.startswith('Clicked')})
                Path('diagnostics/dialog-native-verification.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
                if stage==0 and value==expected:
                    stage=1;executing=False;root.after(500,lambda:threading.Thread(target=open_box,daemon=True).start())
                else:status.set('PASS: both scratch dialog buttons were invoked correctly.' if len(rows)==2 and all(r['passed'] for r in rows) else 'FAILED: inspect dialog-native-verification.json')
            elif kind=='action':
                command,result=value;actions[command]=result;status.set(result)
                for row in rows:
                    if row['command']==command:row['action_result']=result;row['passed']=row['dialog_response']==row['expected_response'] and result.startswith('Clicked')
                Path('diagnostics/dialog-native-verification.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
                if len(rows)==2 and all(r['passed'] for r in rows):status.set('PASS: both scratch dialog buttons were invoked correctly.')
    except queue.Empty:pass
    root.after(100,poll)
poll();root.mainloop()

"""Bounded live Qwen test: real screenshot -> model -> coordinates -> own widgets.

No named-click, folder, OCR, or direct-command route matches the test tasks.
Only clicks contained by the expected fixture widget are allowed to execute.
"""
import ctypes,json,queue,threading
from pathlib import Path
ctypes.windll.user32.SetProcessDPIAware()
import tkinter as tk
from tkinter import ttk
import windows_api as win
from agent import Agent
from desktop_control import map_point

root=tk.Tk();root.title('Gwen Vision Test');root.geometry('900x700+100+100');root.configure(bg='white');root.attributes('-topmost',True)
title=tk.StringVar(value='Qwen visual input test')
tk.Label(root,textvariable=title,font=('Segoe UI',23,'bold'),bg='white').pack(pady=12)
status=tk.StringVar(value='Press Start. Qwen will select BETA, then double-click SAMPLE.')
tk.Label(root,textvariable=status,bg='white',wraplength=850).pack()
canvas=tk.Canvas(root,bg='#eef2f6',height=430,highlightthickness=0);canvas.pack(fill='both',expand=True,padx=25,pady=15)
alpha=tk.Button(canvas,text='ALPHA',bg='#b9c6df',font=('Segoe UI',20))
beta=tk.Button(canvas,text='BETA',bg='#146acf',fg='white',font=('Segoe UI',20))
sample=tk.Label(canvas,text='SAMPLE.pdf',bg='#f5b638',font=('Segoe UI',16),relief='raised',borderwidth=3)
canvas.create_window(160,115,window=alpha,width=200,height=100)
canvas.create_window(610,280,window=beta,width=200,height=100)
canvas.create_window(180,315,window=sample,width=220,height=90)
events=queue.Queue();work=queue.Queue();rows=[];counts={'beta':0,'sample':0};handle=None;agent=None;phase=0
def beta_click():counts['beta']+=1;beta.configure(text='BETA SELECTED');title.set('BETA selected')
def sample_open(event):counts['sample']+=1;sample.configure(text='SAMPLE OPEN');title.set('SAMPLE open')
beta.configure(command=beta_click);sample.bind('<Double-Button-1>',sample_open)
def worker():
    global agent
    agent=Agent(log=lambda s:events.put(('log',s)))
    original=agent.dispatch
    while True:
        item=work.get()
        if item is None:agent.close();return
        task,expected_box,wanted,context=item;executed=[]
        def bounded(action,background):
            if action['action'] in ('click','double_click'):
                point=map_point(action['x'],action['y'],agent.desktop_bounds)
                if not(expected_box[0]<=point[0]<expected_box[2] and expected_box[1]<=point[1]<expected_box[3]):
                    raise RuntimeError('Model missed the fixture target; input blocked: '+str(point))
                if action['action']!=wanted:raise RuntimeError('Wrong click type: '+action['action'])
                executed.append({'action':action,'screen_point':point})
                return original(action,background)
            if action['action']=='wait':return original(action,background)
            raise RuntimeError('Only the expected fixture click may execute: '+str(action))
        agent.dispatch=bounded
        result=agent.run(task,interaction=context,step_limit=3)
        events.put(('finished',{'task':task,'result':result,'executed':executed,'model_loaded':agent.planner is not None}))
def issue():
    widget=beta if phase==0 else sample
    box=(widget.winfo_rootx(),widget.winfo_rooty(),widget.winfo_rootx()+widget.winfo_width(),widget.winfo_rooty()+widget.winfo_height())
    task='Select BETA using a single click.' if phase==0 else 'Open SAMPLE.pdf.'
    ctx={'hwnd':handle,'title':root.title(),'bounds':win.rect(handle),'pointer':win.cursor()}
    work.put((task,box,'click' if phase==0 else 'double_click',ctx))
def start():
    global handle
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.GetParent.argtypes=[ctypes.c_void_p];user.GetParent.restype=ctypes.c_void_p
    handle=user.GetParent(root.winfo_id()) or root.winfo_id()
    if win.foreground()!=handle:status.set('Select this test window before starting.');return
    start_button.configure(state='disabled');issue()
start_button=ttk.Button(root,text='Start test',command=start);start_button.pack(pady=12)
def poll():
    global phase
    try:
        while True:
            kind,value=events.get_nowait()
            if kind=='log':status.set(value[:180])
            elif kind=='finished':
                value['widget_activations']=counts['beta' if phase==0 else 'sample']
                value['passed']=bool(value['executed']) and value['widget_activations']==1 and value['model_loaded']
                rows.append(value)
                Path('diagnostics/live-vlm-verification.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
                if phase==0 and value['passed']:phase=1;root.after(300,issue)
                else:
                    status.set('PASS: Qwen selected BETA and opened SAMPLE with real input.' if all(r['passed'] for r in rows) and len(rows)==2 else 'FAILED: inspect diagnostics/live-vlm-verification.json')
                    work.put(None)
    except queue.Empty:pass
    root.after(100,poll)
threading.Thread(target=worker,daemon=True).start();poll();root.mainloop()

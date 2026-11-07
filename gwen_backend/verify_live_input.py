"""Interactive integration fixture: all injected input stays inside this test window."""
import ctypes,json,threading,queue
from pathlib import Path
ctypes.windll.user32.SetProcessDPIAware()
import tkinter as tk
from tkinter import ttk
from agent import Agent
import windows_api

root=tk.Tk(); root.title('Gwen Input Test'); root.geometry('900x760')
ttk.Label(root,text='Direct input integration test',font=('Segoe UI',18,'bold')).pack(pady=10)
status=tk.StringVar(value='Press Start test. No other application is used.')
ttk.Label(root,textvariable=status).pack()
text=tk.Text(root,height=18,width=70); text.pack(fill='both',expand=True,padx=20,pady=10)
text.insert('1.0','\n'.join(f'Line {i}: Gwen scroll test' for i in range(150)))
entry=ttk.Entry(root); entry.pack(fill='x',padx=20,pady=8)
clicks=0
def clicked():
    global clicks
    clicks+=1; status.set('Target button clicked by the input controller.')
target=ttk.Button(root,text='Target button',command=clicked); target.pack(pady=5)
events=queue.Queue(); a=Agent(log=lambda s:events.put(('log',s))); result={}; handle=None

def point(widget): return (widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)
def issue(task,pointer,next_step):
    context={'hwnd':handle,'title':root.title(),'bounds':windows_api.rect(handle),'pointer':pointer}
    def run():
        try: a.run(task,interaction=context); events.put(('next',next_step))
        except Exception as exc: events.put(('failed',str(exc)))
    threading.Thread(target=run,daemon=True).start()
def after_down():
    result['after_scroll_down']=text.yview()[0]
    if result['after_scroll_down']<=0: fail('Scroll down had no effect'); return
    issue('scroll up',point(text),'up')
def after_up():
    result['after_scroll_up']=text.yview()[0]
    if result['after_scroll_up']>=result['after_scroll_down']: fail('Scroll up had no effect'); return
    issue('clikc herte',point(target),'click')
def after_click():
    result['target_clicks']=clicks
    if clicks!=1: fail('Click here did not click the target'); return
    entry.focus_set(); root.after(100,lambda:issue('type "Gwen typed this."',point(entry),'type'))
def after_type():
    result['typed_text']=entry.get(); result['model_loaded']=a.planner is not None
    if entry.get()!='Gwen typed this.' or a.planner is not None: fail('Typing or model bypass check failed'); return
    result['passed']=True
    Path('live-input-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    status.set('PASS: scroll down/up, click at point, and typing; Qwen was not loaded.')
def fail(message):
    result.update(passed=False,error=message); Path('live-input-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8'); status.set('FAILED: '+message)
def start():
    global handle
    handle=windows_api.foreground(); start_button.configure(state='disabled'); text.yview_moveto(0)
    issue('sroll down',point(text),'down')
start_button=ttk.Button(root,text='Start test',command=start); start_button.pack(pady=10)
def poll():
    try:
        while True:
            kind,value=events.get_nowait()
            if kind=='next': root.after(250,{'down':after_down,'up':after_up,'click':after_click,'type':after_type}[value])
            elif kind=='failed': fail(value)
    except queue.Empty: pass
    root.after(100,poll)
poll(); root.mainloop()

"""Resident local voice and computer assistant."""
import argparse,ctypes,queue,threading,traceback
ctypes.windll.user32.SetProcessDPIAware()
import tkinter as tk
from tkinter import ttk,scrolledtext,messagebox
from voice_gate import VoiceGate

def gui(smoke=False,instance=None):
    root=tk.Tk(); root.title('Gwen Doer 2.0 - Voice Assistant'); root.geometry('1000x900'); root.configure(bg='#111827')
    events=queue.Queue(); work=queue.Queue(maxsize=4); stop=threading.Event(); state_lock=threading.Lock()
    busy=False; closing=False; last_target=None; last_keys={}; cancel_epoch=0
    gate=VoiceGate()
    from speech import Speaker,VoiceEngine
    speaker=Speaker(lambda s:events.put(('log',s)))
    background=tk.BooleanVar(value=False); one_step=tk.BooleanVar(value=False)
    mic_on=tk.BooleanVar(value=False); spoken=tk.BooleanVar(value=True); handsfree=tk.BooleanVar(value=False)
    status=tk.StringVar(value='Starting...'); voice_status=tk.StringVar(value='Starting speech recognition...')
    target_status=tk.StringVar(value='Target: select an app to control')
    ttk.Label(root,text='Gwen Doer',font=('Segoe UI',23,'bold')).pack(anchor='w',padx=18,pady=(12,3))
    ttk.Label(root,text='Enable Hands-free once for continuous commands, or press F9 to speak. Say “Gwen sleep” to pause.').pack(anchor='w',padx=18)
    output=scrolledtext.ScrolledText(root,height=8,wrap='word',font=('Consolas',10),bg='#172033',fg='#e5e7eb',state='disabled')
    output.pack(fill='both',expand=True,padx=18,pady=10)
    entry=tk.Text(root,height=3,font=('Segoe UI',12)); entry.pack(fill='x',padx=18)
    row=ttk.Frame(root); row.pack(fill='x',padx=18,pady=8)
    ttk.Checkbutton(row,text='Browser in background',variable=background).pack(side='left')
    ttk.Checkbutton(row,text='One action',variable=one_step).pack(side='left',padx=8)
    controls=ttk.Frame(root); controls.pack(fill='x',padx=18,pady=(0,6))
    ttk.Label(root,textvariable=status).pack(anchor='w',padx=18)
    ttk.Label(root,textvariable=target_status).pack(anchor='w',padx=18)
    ttk.Label(root,textvariable=voice_status).pack(anchor='w',padx=18,pady=(3,0))
    ttk.Label(root,text='F9: speak once   F10: show/hide chat   F8: stop   Closing this window keeps Gwen running.').pack(anchor='w',padx=18,pady=(5,10))
    dock=tk.Toplevel(root); dock.title('Gwen Doer Dock'); dock.withdraw(); dock.overrideredirect(True); dock.configure(bg='#172033'); dock.attributes('-topmost',True)
    dock.geometry(f'420x145+{max(0,root.winfo_screenwidth()-440)}+{max(0,root.winfo_screenheight()-200)}')
    tk.Label(dock,text='GWEN  •  voice assistant',bg='#172033',fg='#a5b4fc',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=10,pady=(7,2))
    dock_status=tk.StringVar(value='Press F9 or Speak to enable voice')
    tk.Label(dock,textvariable=dock_status,bg='#172033',fg='white',wraplength=395,justify='left',font=('Segoe UI',9)).pack(anchor='w',padx=10)
    dock_row=ttk.Frame(dock); dock_row.pack(fill='x',padx=8,pady=7)
    meter=ttk.Progressbar(dock,maximum=100); meter.pack(fill='x',padx=10,pady=(0,5))
    def log(text): events.put(('log',str(text)))
    def context():
        import windows_api
        current=windows_api.snapshot()
        if current and not current['title'].startswith('Gwen Doer'): return current
        return dict(last_target) if last_target else None
    voice=VoiceEngine(lambda text,ctx:events.put(('voice',(text,ctx,voice.epoch))),lambda s:events.put(('voice_status',s)),context,speaker)
    def show_dock():
        if closing or busy: return
        try:
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.GetParent.argtypes=[ctypes.c_void_p]; user.GetParent.restype=ctypes.c_void_p
            hwnd=user.GetParent(dock.winfo_id()) or dock.winfo_id()
            user.GetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int]; user.GetWindowLongW.restype=ctypes.c_long
            user.SetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_long]; user.SetWindowLongW.restype=ctypes.c_long
            user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x08000000|0x80)
        except Exception: pass
        dock.deiconify()
    def hide_chat(): root.withdraw(); show_dock()
    def show_chat(): root.deiconify(); root.lift(); root.focus_force()
    def toggle_chat():
        if root.state() in ('withdrawn','iconic'): show_chat()
        else: hide_chat()
    def mic_changed():
        voice.set_enabled(mic_on.get())
        if not mic_on.get(): voice_status.set('Microphone off'); dock_status.set('Microphone off • F9 to enable and speak')
    def hands_changed():
        if handsfree.get(): mic_on.set(True); voice.set_enabled(True)
        gate.handsfree=handsfree.get(); dock_status.set('Hands-free: say a command' if gate.handsfree else 'Say “Gwen listen” or press F9')
        log('Hands-free session '+('enabled.' if gate.handsfree else 'paused.'))
    def spoken_changed():
        speaker.enabled=spoken.get()
        if not spoken.get(): speaker.cancel()
    def halt():
        nonlocal cancel_epoch
        with state_lock: cancel_epoch+=1; stop.set()
        speaker.cancel(); voice.cancel_pending()
        while True:
            try: work.get_nowait()
            except queue.Empty: break
        status.set('Stopping...'); dock_status.set('Stopped. Ready for your next command.')
    def speak_once():
        speaker.cancel(); voice.cancel_pending(); mic_on.set(True); voice.set_enabled(True); gate.arm(15)
        dock_status.set('Listening for your next command...'); status.set('Listening for your next command...')
    def quit_app():
        nonlocal closing
        if closing: return
        closing=True; halt(); voice.close(); speaker.close(); dock.withdraw(); work.put(None); status.set('Closing after the current action...')
    root.protocol('WM_DELETE_WINDOW',hide_chat)
    ttk.Checkbutton(controls,text='Microphone',variable=mic_on,command=mic_changed).pack(side='left')
    ttk.Checkbutton(controls,text='Hands-free session',variable=handsfree,command=hands_changed).pack(side='left',padx=8)
    ttk.Checkbutton(controls,text='Spoken replies',variable=spoken,command=spoken_changed).pack(side='left')
    ttk.Button(controls,text='Speak once (F9)',command=speak_once).pack(side='left',padx=10)
    ttk.Button(controls,text='Quit',command=quit_app).pack(side='right')
    ttk.Button(controls,text='Hide to dock',command=hide_chat).pack(side='right')
    ttk.Button(dock_row,text='Speak',command=speak_once).pack(side='left')
    ttk.Button(dock_row,text='Chat',command=show_chat).pack(side='left',padx=4)
    ttk.Button(dock_row,text='Stop',command=halt).pack(side='left')
    ttk.Checkbutton(dock_row,text='Mic',variable=mic_on,command=mic_changed).pack(side='left',padx=4)
    ttk.Button(dock_row,text='Quit',command=quit_app).pack(side='right')
    try:
        import sounddevice as sd
        inputs=[(i,d['name']) for i,d in enumerate(sd.query_devices()) if d['max_input_channels']>0]
        device_row=ttk.Frame(root); device_row.pack(fill='x',padx=18,pady=(0,8))
        ttk.Label(device_row,text='Microphone:').pack(side='left')
        device=ttk.Combobox(device_row,values=['System default']+[f'{i}: {name}' for i,name in inputs],state='readonly',width=65)
        device.current(0); device.pack(side='left',padx=5)
        device.bind('<<ComboboxSelected>>',lambda event:voice.set_device(None if device.current()==0 else inputs[device.current()-1][0]))
    except Exception as exc: log('Could not list audio inputs: '+str(exc))
    def confirm(message):
        answer=queue.Queue(); events.put(('confirm',(message,answer)))
        while not stop.is_set():
            try: return answer.get(timeout=.2)
            except queue.Empty: pass
        return False
    def worker():
        from agent import Agent
        try: agent=Agent(log,confirm,stop); events.put(('ready',None))
        except Exception: events.put(('fatal',traceback.format_exc())); return
        while True:
            item=work.get()
            if item is None: break
            task,bg,steps,ctx,origin,epoch=item
            with state_lock:
                cancelled=epoch!=cancel_epoch
                if not cancelled: stop.clear()
            if cancelled: events.put(('finished',('Cancelled.',origin))); continue
            events.put(('started',(task,origin))); result=''
            try:
                if task=='/refresh':
                    from catalog import Catalog
                    Catalog.refresh(); agent.catalog=Catalog(); result='App directory refreshed.'; log(result)
                elif task=='/apps': result='\n'.join(sorted({e['name'] for e in agent.catalog.entries})); log(result)
                elif task=='/reset': agent.context=[]; result='Conversation cleared.'; log(result)
                else: result=agent.run(task,bg,steps,interaction=ctx)
            except Exception as exc:
                agent.record({'unexpected_error':traceback.format_exc()}); result='Task failed: '+str(exc).splitlines()[0][:180]; log(result)
            finally: events.put(('finished',(result,origin)))
        agent.close(); events.put(('closed',None))
    def enqueue(task,ctx=None,origin='typed'):
        nonlocal busy
        if not task.strip() or closing: return
        with state_lock: epoch=cancel_epoch
        try: work.put_nowait((task.strip(),background.get(),1 if one_step.get() else None,ctx or context(),origin,epoch))
        except queue.Full: log('Command queue is full. Wait or say stop.'); return
        busy=True; dock.withdraw(); root.withdraw(); status.set('Working... F8 stops.'); run.configure(state='disabled')
    def submit(event=None):
        task=entry.get('1.0','end').strip()
        if task: entry.delete('1.0','end'); enqueue(task,context(),'typed')
        return 'break'
    run=ttk.Button(row,text='Run task',command=submit,state='disabled'); run.pack(side='right')
    ttk.Button(row,text='Stop',command=halt).pack(side='right',padx=6)
    entry.bind('<Control-Return>',submit)
    def voice_command(text,ctx,epoch):
        if epoch!=voice.epoch: return
        outcome=gate.accept(text)
        if not outcome: return
        if 'command' in outcome: log('Heard: '+outcome['command']); enqueue(outcome['command'],ctx,'voice'); return
        control=outcome['control']
        if control=='stop': halt(); return
        if control=='show': show_chat(); return
        if control=='unclear': status.set('No complete command recognized.'); dock_status.set('Please say a complete command or question.'); return
        if control=='hide': hide_chat(); return
        if control=='mic_off': mic_on.set(False); mic_changed(); speaker.say('Microphone off.'); return
        if control=='armed': speak_once(); speaker.say('Listening.'); return
        if control=='handsfree': handsfree.set(True); hands_changed(); speaker.say('Listening.'); return
        if control=='sleep': handsfree.set(False); hands_changed(); speaker.say('Paused.')
    def poll():
        nonlocal busy,last_target
        try:
            current=context()
            if current:
                last_target=current; target_status.set('Target: '+current['title'][:100])
        except Exception: pass
        for key,action in ((0x77,halt),(0x78,speak_once),(0x79,toggle_chat)):
            down=bool(ctypes.windll.user32.GetAsyncKeyState(key)&0x8000)
            if down and not last_keys.get(key): action()
            last_keys[key]=down
        if instance and instance.show_requested(): show_chat()
        meter['value']=min(100,voice.level*1000)
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=='log':
                    output.configure(state='normal'); output.insert('end',value+'\n\n'); output.see('end'); output.configure(state='disabled')
                elif kind=='ready': busy=False; run.configure(state='normal'); status.set('Ready. Closing this chat keeps Gwen available.'); show_dock()
                elif kind=='started': busy=True; dock.withdraw(); status.set('Working: '+value[0][:70])
                elif kind=='finished':
                    result,origin=value; busy=not work.empty(); run.configure(state='disabled' if busy else 'normal'); status.set('Ready. F9 speaks once; F10 opens chat.')
                    dock_status.set((result or 'Ready.')[:130]); show_dock()
                    if origin=='voice' and spoken.get() and result: speaker.say(result if len(result)<220 else result[:217]+'...')
                elif kind=='voice': voice_command(*value)
                elif kind=='voice_status':
                    voice_status.set(value)
                    if value.startswith(('Microphone unavailable','Voice unavailable')): mic_on.set(False); dock_status.set(value[:130])
                elif kind=='confirm':
                    show_chat(); message,answer=value; approved=messagebox.askyesno('Confirm action',message,parent=root)
                    root.withdraw(); answer.put(approved)
                elif kind=='fatal': messagebox.showerror('Startup failed',value); root.destroy(); return
                elif kind=='closed': root.destroy(); return
        except queue.Empty: pass
        root.after(100,poll)
    threading.Thread(target=worker,daemon=True).start()
    if not smoke:
        voice.set_enabled(mic_on.get()); voice.start()
    else: voice.set_enabled(False)
    poll()
    if smoke: root.after(1800,quit_app)
    root.mainloop()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--task'); parser.add_argument('--background',action='store_true'); parser.add_argument('--ui-smoke',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.task:
        from agent import Agent
        agent=Agent(confirm=lambda message:input(message+' [yes/no] ').strip().lower()=='yes')
        try: agent.run(args.task,args.background)
        finally: agent.close()
    else:
        from app_runtime import SingleInstance
        instance=SingleInstance()
        try:
            if instance.owner: gui(args.ui_smoke,instance)
        finally: instance.close()

if __name__=='__main__': main()

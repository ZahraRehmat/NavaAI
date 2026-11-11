"""Resident typed and offline-voice command panel."""
import argparse,ctypes,json,queue,re,threading,time,traceback
from pathlib import Path
from grid_display import enable_dpi_awareness
enable_dpi_awareness()
import tkinter as tk
from tkinter import ttk,scrolledtext,messagebox

def gui(smoke=False,instance=None):
    import windows_api as win
    from cursor_marker import CursorMarker
    startup_target=win.choose_target(win.snapshot(),[])
    root=tk.Tk();root.withdraw(); root.title('Gwen Doer - Type commands'); root.configure(bg='#172033')
    width,height=480,480
    root.geometry(f'{width}x{height}+{max(0,root.winfo_screenwidth()-width-18)}+{max(0,root.winfo_screenheight()-height-70)}')
    root.minsize(480,460); root.attributes('-topmost',False)
    events=queue.Queue(); work=queue.Queue(); stop=threading.Event()
    busy=False; ready=False; closing=False; last_target=startup_target; target_history=[]; epoch=0; last_keys={}
    current_task='';task_started=0
    from command_voice import CommandVoice,stale,power_intent
    from speech_context import codes
    config_path=Path(__file__).with_name('voice_config.json')
    voice_config=json.loads(config_path.read_text(encoding='utf-8'))
    voice_session=CommandVoice(voice_config);voice_engine=None;pending_voice=None;voice_dialog=None;dialog_version=0
    from dictation_queue import DictationQueue
    dictation_queue=DictationQueue()
    from selection_hints import VisibleWordHints
    selection_hints=VisibleWordHints()
    from task_feedback import SoundCues,BackgroundPresenter
    cues=SoundCues(voice_config.get('completion_beep',True));presenter=BackgroundPresenter(root,cues)
    marker=CursorMarker(root,visible=voice_session.active)
    from status_indicator import StatusIndicator,indicator_state
    indicator=StatusIndicator(root,visible=voice_session.active)
    mic_listening=False;mic_error=False;recognizing=False;last_voice_diagnostic=0;last_voice_decision=''
    from grid_overlay import GridOverlay
    from grid_mouse import GridMouse
    from smart_grid import AdaptiveGrid,AccessibleTargets,check_target
    from grid_display import monitors
    grid_overlay=GridOverlay(root)
    smart_grid=AdaptiveGrid(GridMouse(),monitors,render=lambda picture:events.put(('grid',picture)),stop=stop,
                           observer=AccessibleTargets(lambda:last_target),target_check=check_target,chooser=lambda query,options:choose(query,options))
    tk.Label(root,text='GWEN  •  type or say a command',bg='#172033',fg='#a5b4fc',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=10,pady=(7,2))
    status=tk.StringVar(value='Starting…')
    tk.Label(root,textvariable=status,bg='#172033',fg='white',anchor='w',wraplength=415).pack(fill='x',padx=10)
    target=tk.StringVar(value='Select the app to control, then type here.')
    tk.Label(root,textvariable=target,bg='#172033',fg='#a1aabe',anchor='w').pack(fill='x',padx=10,pady=(2,4))
    output=scrolledtext.ScrolledText(root,height=5,wrap='word',font=('Segoe UI',9),bg='#101827',fg='#e5e7eb',state='disabled')
    output.pack(fill='both',expand=True,padx=10,pady=(0,6))
    command=tk.StringVar()
    entry=ttk.Entry(root,textvariable=command,font=('Segoe UI',11)); entry.pack(fill='x',padx=10)
    row=ttk.Frame(root); row.pack(fill='x',padx=10,pady=6)
    background=tk.BooleanVar(value=False)
    ttk.Checkbutton(row,text='Background',variable=background).pack(side='left')
    voice_row=ttk.Frame(root);voice_row.pack(fill='x',padx=10,pady=(0,3))
    voice_enabled=tk.BooleanVar(value=bool(voice_config.get('enabled',True)))
    handsfree=tk.BooleanVar(value=voice_session.handsfree)
    voice_status=tk.StringVar(value='Voice: starting offline recognizer…' if voice_enabled.get() else 'Voice off')
    tk.Label(root,textvariable=voice_status,bg='#172033',fg='#b9e7c3',anchor='w',wraplength=445,font=('Segoe UI',8)).pack(fill='x',padx=10)
    tk.Label(root,text='Enter: send   F8: stop   F9: voice   F10: show/hide',bg='#172033',fg='#a1aabe',font=('Segoe UI',8)).pack(pady=(0,5))
    def log(text):events.put(('log',str(text)))
    def context():
        return win.choose_target(win.snapshot(),[last_target,*target_history])
    def show(focus=False):
        if closing:return
        root.deiconify(); root.lift()
        if focus:root.focus_force(); entry.focus_set()
    def halt(notify=True):
        nonlocal epoch,pending_voice
        pending_voice=None;voice_session.armed_until=0;voice_session.dictating=False
        voice_session.selecting=False
        dictation_queue.clear()
        if voice_engine:voice_engine.cancel_pending(restart=False)
        epoch+=1; stop.set(); smart_grid.emergency_stop();status.set('Stopped. Mouse released. Ready for your next command.')
        if notify and not busy and not closing and voice_session.active:presenter.finished('Stopped')
    def quit_app():
        nonlocal closing
        if closing:return
        halt(); closing=True
        if voice_engine:voice_engine.close()
        cues.close()
        indicator.close();smart_grid.close();grid_overlay.close(); marker.close(); root.withdraw(); work.put(None)
    def confirm(message):
        answer=queue.Queue(); events.put(('confirm',(message,answer)))
        while not stop.is_set():
            try:return answer.get(timeout=.2)
            except queue.Empty:pass
        return False
    def choose(query,options,preview=None):
        answer=queue.Queue();events.put(('choose',(query,options,preview,answer)))
        while not stop.is_set():
            try:return answer.get(timeout=.2)
            except queue.Empty:pass
        return None
    def worker():
        try:
            from agent import Agent
            agent=Agent(log,confirm,stop,choose=choose,start_dictation=lambda target:events.put(('dictation_after_edit',(target,task_epoch)))); events.put(('ready',None))
        except Exception:events.put(('fatal',traceback.format_exc()));return
        while True:
            item=work.get()
            if item is None:break
            task,bg,ctx,task_epoch=item
            if task_epoch!=epoch:events.put(('finished','Cancelled.'));continue
            stop.clear()
            if task_epoch!=epoch or not voice_session.active:
                events.put(('finished','Cancelled.'));continue
            try:
                grid_result=smart_grid.run(task)
                if grid_result is not None:
                    result=grid_result;agent.record({'manual_grid':task,'result':result,'active':smart_grid.active,'point':smart_grid.point,'held':list(smart_grid.mouse.held),'targets':smart_grid.last_targets})
                elif task=='/reset':agent.context=[]; result='Conversation cleared.'
                elif task=='/apps':result='\n'.join(sorted({e['name'] for e in agent.catalog.entries}))
                elif task.startswith('/office'):
                    from office_catalog import summary,search_controls
                    from office_language import tools_for
                    from office_control import office_kind
                    kind=office_kind(ctx) or 'word';query=task[len('/office'):].strip()
                    if query.lower().startswith('search '):query=query[7:]
                    if query:result=kind+':\n'+'\n'.join(c['id']+' ('+c['type']+')' for c in search_controls(kind,query))
                    else:result='Native '+kind+' tools: '+', '.join(tools_for(kind))+'.\nCatalog: '+str(summary())+'\nUse /office search <feature>. Indexed controls are not all executable in every view.'
                else:result=agent.run(task,bg,interaction=ctx)
            except Exception as exc:
                agent.record({'unexpected_error':traceback.format_exc(),'grid_targets':smart_grid.last_targets}); result='Task failed: '+(str(exc).strip() or type(exc).__name__).splitlines()[0][:250]
            events.put(('finished',result or 'Done.'))
        smart_grid.emergency_stop();agent.close(); events.put(('closed',None))
    def send_task(task,ctx):
        nonlocal busy,pending_voice,current_task,task_started
        power=power_intent(task)
        if power:
            set_power(power=='power_on');return 'break'
        if not voice_session.active:
            status.set('Gwen is off. Say or type “Gwen turn on”, or press F9.');return 'break'
        from selection_commands import ON,OFF,range_command,canonical
        selection_text=task.lower().strip().rstrip('.! ')
        if selection_text in ON|OFF:
            voice_session.selecting=selection_text in ON;voice_session.dictating=False
            if voice_engine:voice_engine.cancel_pending(restart=False)
            command.set('');status.set('Selection: say start words to end words; the span will be copied.' if voice_session.selecting else 'Selection off.')
            return 'break'
        if voice_session.selecting:
            selection_range=range_command(task,mode=True)
            if selection_range:task=canonical(selection_range)
        from grid_commands import toggle_intent
        if toggle_intent(task)=='disable':
            halt();command.set('');status.set('Smart grid off. Mouse released.');log('Gwen: Smart grid off.');return 'break'
        if not task or busy or not ready or closing:return 'break'
        pending_voice=None;command.set(''); busy=True; run.configure(state='disabled')
        current_task=task;task_started=time.monotonic()
        log('You: '+task); status.set('Working… F8 stops.'); marker.working(True)
        presenter.begin()
        work.put((task,background.get(),ctx,epoch))
        return 'break'
    def submit(event=None):return send_task(command.get().strip(),context())
    run=ttk.Button(row,text='Send',command=submit,state='disabled'); run.pack(side='right')
    ttk.Button(row,text='Stop',command=halt).pack(side='right',padx=3)
    ttk.Button(row,text='Quit',command=quit_app).pack(side='right')
    entry.bind('<Return>',submit); root.protocol('WM_DELETE_WINDOW',quit_app)
    def keyboard_halt(_):
        ctypes.windll.user32.GetAsyncKeyState(0x77);last_keys[0x77]=True;halt()
    root.bind('<F8>',keyboard_halt)
    def save_voice():
        voice_config['enabled']=voice_enabled.get();voice_config['device']=voice_engine.device if voice_engine else voice_config.get('device')
        voice_config['handsfree']=voice_session.handsfree
        voice_config['assistant_active']=voice_session.active
        config_path.write_text(json.dumps(voice_config,indent=2)+'\n',encoding='utf-8')
    def speech_context():
        if not voice_session.active:return {'assistant_active':False,'dictation':False,'busy':busy,'captured_at':time.monotonic()}
        ctx=context();snapshot={'assistant_active':True,'interaction':ctx,'dictation':voice_session.dictating,'office':'excel' if ctx and 'excel' in ctx.get('title','').lower() else '',
                               'busy':busy,'captured_at':time.monotonic(),'dialog_version':dialog_version,'dialog_active':bool(voice_dialog and not voice_dialog['chooser'].done)}
        snapshot['selection']=voice_session.selecting
        if ctx and ctx.get('class_name')=='XLMAIN':snapshot['office']='excel'
        if snapshot['dialog_active']:
            snapshot['dialog_kind']=voice_dialog['kind'];snapshot['dialog_count']=voice_dialog['count']
            snapshot['dialog_labels']=list(voice_dialog['chooser'].labels)
            snapshot['dialog_numbers']=list(voice_dialog['chooser'].numbers)
        if voice_session.selecting:snapshot['selection_hints']=selection_hints.get(ctx) or voice_session.recent_dictation
        with smart_grid.lock:
            snapshot['grid_active']=smart_grid.active
            snapshot['grid_version']=(smart_grid.mode,smart_grid.generation)
            if smart_grid.active:
                keys={label:row['key'] for label,row in smart_grid.grid.targets.items()}
                snapshot['target_names']=[row['name'] for row in smart_grid.grid.targets.values()]
                snapshot['labels']=list(keys);snapshot['label_keys']=keys
        return snapshot
    def toggle_voice():
        nonlocal voice_engine,pending_voice,mic_listening,mic_error,recognizing
        pending_voice=None
        mic_listening=False;mic_error=False;recognizing=False
        if voice_engine is None and voice_enabled.get():
            from speech import VoiceEngine
            voice_engine=VoiceEngine(lambda packet,ctx:events.put(('speech',(packet,ctx))),lambda message:events.put(('speech_status',message)),speech_context,speaker=cues,config=voice_config,detailed=True)
            voice_engine.device=voice_config.get('device');voice_engine.start()
        elif voice_engine:voice_engine.set_enabled(voice_enabled.get());voice_engine.cancel_pending()
        if not voice_enabled.get():voice_session.handsfree=False;voice_session.armed_until=0;voice_session.dictating=False;voice_session.selecting=False;handsfree.set(False)
        voice_status.set('Voice: say “Gwen listen” or “Gwen <command>”.' if voice_enabled.get() else 'Voice off')
        save_voice()
    def toggle_handsfree():
        voice_session.handsfree=handsfree.get();voice_session.armed_until=0
        save_voice()
        if voice_session.handsfree:root.withdraw();cues.notify()
        voice_status.set('Voice: hands-free commands enabled' if handsfree.get() else 'Voice: say Gwen before a command')
    def set_power(value):
        nonlocal pending_voice
        value=bool(value)
        if not value:
            halt(notify=False)
            selection_hints.clear()
            if voice_dialog and not voice_dialog['chooser'].done:voice_dialog['chooser'].finish(None)
            grid_overlay.close()
        voice_session.active=value;voice_session.handsfree=value;voice_session.dictating=False;voice_session.armed_until=0
        voice_session.selecting=False
        pending_voice=None;command.set('');handsfree.set(value)
        root.withdraw();marker.set_visible(value);indicator.set_visible(value)
        # Standby keeps only a local wake listener, so hands-free reactivation
        # remains possible. Explicit microphone off / Quit still release it.
        voice_enabled.set(True)
        if voice_engine is None or not voice_engine.enabled.is_set():toggle_voice()
        elif voice_engine:voice_engine.cancel_pending(restart=False)
        save_voice()
        voice_status.set('Gwen on: continuous commands enabled.' if value else 'Gwen off: wake listener only. Say “Gwen turn on” or press F9.')
        status.set('Ready.' if value else 'Gwen off. Wake listener only.')
        cues.notify()
    def mic_settings():
        import sounddevice as sd
        window=tk.Toplevel(root);window.title('Gwen Doer - Microphone');window.attributes('-topmost',True)
        devices=[(None,'Windows default microphone')]+[(i,d['name']) for i,d in enumerate(sd.query_devices()) if d['max_input_channels']>0]
        ttk.Label(window,text='Offline speech input device').pack(padx=12,pady=8)
        box=ttk.Combobox(window,state='readonly',width=58,values=[name for _,name in devices]);box.pack(padx=12,pady=8);box.current(0)
        selected=voice_config.get('device')
        for index,(device,_) in enumerate(devices):
            if selected==device:box.current(index);break
        ttk.Label(window,text='Choose an INPUT microphone. Earphone speakers alone do not supply audio.').pack(padx=12,pady=4)
        mic_level=tk.StringVar();ttk.Label(window,textvariable=mic_level).pack(padx=12,pady=4)
        def refresh_level():
            if not window.winfo_exists():return
            name=voice_engine.active_device if voice_engine else 'Voice off'
            level=voice_engine.level if voice_engine else 0
            mic_level.set(f'Active: {name}\nInput level: {level:.4f} — speak and watch the badge meter.')
            window.after(150,refresh_level)
        refresh_level()
        def select():
            device=devices[box.current()][0];voice_config['device']=device
            if voice_engine:voice_engine.set_device(device)
            save_voice();window.destroy()
        ttk.Button(window,text='Use microphone',command=select).pack(pady=10)
    ttk.Checkbutton(voice_row,text='Offline voice',variable=voice_enabled,command=toggle_voice).pack(side='left')
    ttk.Checkbutton(voice_row,text='Hands-free',variable=handsfree,command=toggle_handsfree).pack(side='left')
    ttk.Button(voice_row,text='Mic…',command=mic_settings).pack(side='right')
    def voice_input(packet,captured):
        nonlocal pending_voice,last_voice_decision
        if not voice_enabled.get() or closing:return
        def speech_trace(stage,**details):
            try:
                path=Path(__file__).with_name('logs')/'voice-decisions.jsonl';path.parent.mkdir(exist_ok=True)
                record={'time':time.time(),'stage':stage,**details}
                with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            except OSError:pass
        speech_trace('recognized',text=packet.get('text',''),confidence=packet.get('confidence',0),
            words=packet.get('words',[]),grid_active=captured.get('grid_active',False),
            handsfree=voice_session.handsfree,busy=busy,target_at_utterance=captured.get('interaction'),
            backend=packet.get('backend'),primary_text=packet.get('primary_text'),primary_confidence=packet.get('primary_confidence'),
            dictation=captured.get('dictation',False),selection=captured.get('selection',False),decode_seconds=packet.get('seconds'))
        raw=packet.get('text','').strip();plain=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s*','',raw,flags=re.I).strip().rstrip('.!?').lower()
        power=power_intent(raw)
        if power:
            if packet.get('confidence',0)>=voice_config.get('review_confidence',.86):
                speech_trace('power',control=power);set_power(power=='power_on')
            return
        if not voice_session.active:
            speech_trace('ignored',reason='assistant_off');return
        from grid_commands import toggle_intent
        if not voice_session.dictating and toggle_intent(plain)=='disable' and packet.get('confidence',0)>=voice_config.get('review_confidence',.86):
            speech_trace('control',control='grid_off')
            send_task('grid off',None);return
        if plain in ('stop','stop now','cancel task','stop the task') and packet.get('confidence',0)>=.5:halt();return
        if voice_dialog and not voice_dialog['chooser'].done:
            from dialog_voice import answer
            if not captured.get('dialog_active') or captured.get('dialog_version')!=voice_dialog['version']:
                speech_trace('choice_rejected',reason='stale_dialog');return
            if packet.get('confidence',0)<.86:
                speech_trace('choice_rejected',reason='low_confidence')
                voice_status.set('Choice unclear. Say a displayed letter or its NATO spelling, or cancel.');return
            selected=answer(raw,voice_dialog['count'],voice_dialog['kind'],labels=voice_dialog['chooser'].labels,
                            numbers=voice_dialog['chooser'].numbers)
            if selected is None:
                speech_trace('choice_rejected',reason='invalid_answer');return
            speech_trace('choice_answer',index=selected,dialog_version=voice_dialog['version'])
            voice_dialog['chooser'].finish(None if selected=='cancel' else selected)
            return
        was_handsfree=voice_session.handsfree
        decision=voice_session.route(packet,captured);kind=decision['kind']
        last_voice_decision=kind
        speech_trace('routed',decision=decision)
        handsfree.set(voice_session.handsfree)
        if was_handsfree!=voice_session.handsfree:save_voice()
        if kind=='ignore':return
        if kind=='control':
            control=decision['control']
            if control=='stop':halt()
            elif control=='show':show()
            elif control=='hide':root.withdraw()
            elif control=='mic_off':voice_enabled.set(False);toggle_voice()
            elif control in ('dictation_on','dictation_off','selection_on','selection_off'):
                pending_voice=None
                if control=='selection_on':selection_hints.get(context())
                if voice_engine:voice_engine.cancel_pending(restart=False)
                voice_status.set('Selection: say “Islamabad to Karachi” to select and copy; “stop selection” to finish.' if voice_session.selecting else 'Dictation on: speak text; say “stop dictation” to finish.' if voice_session.dictating else 'Listening for commands.')
                root.withdraw();cues.notify()
            elif control=='reject':pending_voice=None;command.set('');voice_status.set('Voice: command cancelled')
            elif control=='confirm':
                if pending_voice and pending_voice['confirmable']:
                    candidate=pending_voice
                    if time.monotonic()-candidate['context'].get('captured_at',0)<=20 and not stale(candidate['context'],speech_context(),candidate.get('code','')) and not busy:
                        send_task(candidate['text'],candidate['context'].get('interaction'))
                    else:pending_voice=None;voice_status.set('Voice: screen changed; repeat the command')
            else:
                voice_status.set('Voice: hands-free commands enabled' if voice_session.handsfree else 'Voice: say Gwen before a command')
                if control in ('handsfree','sleep'):
                    save_voice();root.withdraw();cues.notify()
            return
        if time.monotonic()-captured.get('captured_at',0)>12 or stale(captured,speech_context(),decision.get('code','')):
            speech_trace('not_executed',reason='stale_screen_or_expired')
            voice_status.set('Voice: screen/grid changed while recognizing; repeat the command');presenter.review();return
        log('Heard: '+raw+(' → '+decision['text'] if raw!=decision['text'] else ''))
        if kind=='command' and busy and decision.get('dictation_input'):
            from direct_commands import parse_direct
            running=parse_direct(current_task)
            if running and running['kind'] in ('type','keys','select_text','punctuate') and dictation_queue.push(decision['text'],captured,epoch):
                voice_status.set('Dictation queued; continuing in the same app.');return
        if kind=='review':
            # A speech hypothesis is not typed input. Inserting it into the
            # entry can replace a user's command between typing and Enter.
            pending_voice={**decision,'context':captured};presenter.review()
            voice_status.set('Heard “'+decision['text']+'”. Not executed: '+decision['reason']+(' Say “Gwen confirm command” to accept.' if decision['confirmable'] else ''))
        elif busy or not ready:
            speech_trace('not_executed',reason='busy_or_starting')
            voice_status.set('Voice: task is busy or starting; repeat when ready');presenter.review()
        else:
            speech_trace('submitted',text=decision['text'])
            send_task(decision['text'],captured.get('interaction'))
    def open_voice_dialog(query,options,respond,kind='choice',preview=None):
        nonlocal voice_dialog,dialog_version
        from choice_ui import TargetChooser
        dialog_version+=1
        suppress_grid=any(option.get('dropdown_choice') for option in options)
        if suppress_grid:grid_overlay.close()
        def chosen(index):
            respond(index)
            if suppress_grid and smart_grid.active:smart_grid.picture()
        chooser=TargetChooser(root,query,options,chosen,stop,preview,activate=not voice_enabled.get())
        voice_dialog={'chooser':chooser,'count':len(options),'kind':kind,'version':dialog_version,'suppress_grid':suppress_grid}
        if voice_engine:voice_engine.cancel_pending(restart=False)
        voice_status.set('Voice: say yes or no' if kind=='confirm' else 'Voice: say a displayed choice letter or its NATO spelling')
    def poll():
        nonlocal busy,ready,last_target,mic_listening,mic_error,recognizing,last_voice_diagnostic
        if not closing:
            current=win.snapshot() if voice_session.active else None
            if win.usable_target(current) and win.target_alive(current):
                if last_target and last_target['hwnd']!=current['hwnd']:
                    target_history[:]=[last_target]+[old for old in target_history if old['hwnd'] not in (last_target['hwnd'],current['hwnd'])]
                    del target_history[8:]
                last_target=current; target.set('Target: '+(current['title'] or 'Desktop')[:52])
            for key in (0x77,0x78,0x79):
                state=ctypes.windll.user32.GetAsyncKeyState(key);down=bool(state&0x8000)
                if state&1 or (down and not last_keys.get(key)):
                    if key==0x77:halt()
                    elif key==0x78:
                        if not voice_session.active:set_power(True)
                        else:voice_enabled.set(not voice_enabled.get());toggle_voice()
                    elif root.state()=='withdrawn':show(True)
                    else:root.withdraw()
                last_keys[key]=down
            if instance and instance.show_requested():
                if not voice_session.active:set_power(True)
                show(True)
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=='grid':
                    try:
                        if voice_dialog and not voice_dialog['chooser'].done and voice_dialog.get('suppress_grid'):grid_overlay.close()
                        elif voice_session.active:grid_overlay.draw(value)
                        else:grid_overlay.close()
                        if value.get('active') and value.get('mode')=='smart' and not busy:
                            status.set('SMART GRID • '+str(value['count'])+' targets • '+(value.get('error') or 'auto refresh on'))
                    except Exception as exc:
                        smart_grid.emergency_stop();grid_overlay.close();log('Grid overlay stopped: '+str(exc))
                elif kind=='log':
                    output.configure(state='normal'); output.insert('end',value+'\n'); output.see('end'); output.configure(state='disabled')
                elif kind=='speech':
                    try:voice_input(*value)
                    except Exception as exc:voice_status.set('Voice command not executed: '+(str(exc).strip() or type(exc).__name__)[:150]);presenter.review()
                elif kind=='dictation_after_edit':
                    editing_target,editing_epoch=value
                    if editing_epoch==epoch and voice_session.active and not stop.is_set() and win.target_alive(editing_target) and win.foreground()==editing_target['hwnd']:
                        voice_session.dictating=True;voice_session.selecting=False
                        if not voice_enabled.get():voice_enabled.set(True);toggle_voice()
                        elif voice_engine:voice_engine.cancel_pending(restart=False)
                        root.withdraw();voice_status.set('Dictation on in the Excel cell. Say stop dictation to finish, or press enter to commit.')
                elif kind=='speech_status':
                    message=value.lower()
                    if message.startswith('microphone listening'):
                        mic_listening=True;mic_error=False;recognizing=False
                    elif 'unavailable' in message or 'recognition error' in message:
                        mic_error=True;recognizing=False
                    elif 'microphone off' in message:
                        mic_listening=False;recognizing=False
                    elif message.startswith('recognizing speech'):recognizing=True
                    if not pending_voice and not (voice_dialog and not voice_dialog['chooser'].done):
                        voice_status.set(('Voice (hands-free): ' if voice_session.handsfree else 'Voice (say Gwen): ')+value)
                elif kind=='ready':ready=True; run.configure(state='normal'); status.set('Ready.')
                elif kind=='finished':
                    busy=False; marker.working(False); run.configure(state='normal'); log('Gwen: '+value)
                    try:
                        path=Path(__file__).with_name('logs')/'task-results.jsonl'
                        with path.open('a',encoding='utf-8') as stream:
                            stream.write(json.dumps({'time':time.time(),'task':current_task,'result':value,
                                'seconds':round(time.monotonic()-task_started,2)})+'\n')
                    except OSError:pass
                    if smart_grid.active and not value.startswith('Task failed:'):
                        point=smart_grid.point or smart_grid.mouse.position()
                        status.set(smart_grid.mode.upper()+f' GRID • {point[0]}, {point[1]} • '+('holding '+', '.join(sorted(smart_grid.mouse.held)) if smart_grid.mouse.held else 'mouse released'))
                    else:status.set(value.splitlines()[0][:100])
                    if voice_session.active:presenter.finished(value)
                    try:
                        if value.startswith(('Could not','Task failed:','Stopped','Cancelled')):dictation_queue.clear()
                        queued=dictation_queue.pop(speech_context(),epoch)
                        if queued:send_task(*queued)
                    except ValueError as exc:voice_status.set(str(exc));presenter.review()
                elif kind=='confirm':
                    message,answer=value
                    if not voice_session.active:answer.put(False)
                    elif voice_enabled.get():open_voice_dialog(message,[{'label':'Yes'},{'label':'No'}],lambda index:answer.put(index==0),'confirm')
                    else:show();answer.put(messagebox.askyesno('Confirm action',message,parent=root));root.withdraw()
                elif kind=='choose':
                    query,options,preview,answer=value
                    if voice_session.active:open_voice_dialog(query,options,answer.put,preview=preview)
                    else:answer.put(None)
                elif kind=='fatal':messagebox.showerror('Gwen startup failed',value,parent=root);indicator.close();marker.close();root.destroy();return
                elif kind=='closed':root.destroy();return
        except queue.Empty:pass
        if not closing:
            mic_open=bool(voice_engine and voice_engine.microphone_open.is_set())
            level=voice_engine.level if mic_open else 0
            badge_state=indicator_state(ready=ready,busy=busy,enabled=voice_enabled.get(),
                microphone=mic_open,handsfree=voice_session.handsfree,
                armed=voice_session.armed_until>time.monotonic(),recognizing=recognizing,
                review=bool(pending_voice or (voice_dialog and not voice_dialog['chooser'].done)),error=mic_error)
            if busy:
                badge_state=('Working '+str(int(time.monotonic()-task_started))+'s · F8','#fbbf24')
                if voice_dialog and not voice_dialog['chooser'].done:badge_state=('Choose / say cancel','#fbbf24')
            elif voice_session.dictating and mic_open and not mic_error:badge_state=('Dictating · say stop','#c4b5fd')
            elif voice_session.selecting and mic_open and not mic_error:badge_state=('Selection · say from / to','#93c5fd')
            indicator.update(badge_state,level)
            if time.monotonic()-last_voice_diagnostic>1:
                last_voice_diagnostic=time.monotonic()
                try:
                    path=Path(__file__).with_name('logs')/'voice_runtime.json';path.parent.mkdir(exist_ok=True)
                    path.write_text(json.dumps({'updated_at':time.time(),'microphone_open':mic_open,
                        'device':voice_engine.active_device if voice_engine else '', 'level':level,
                        'status':voice_engine.last_status if voice_engine else 'Off',
                        'handsfree':voice_session.handsfree,'assistant_active':voice_session.active,'last_decision':last_voice_decision,
                        'dictating':voice_session.dictating,'selecting':voice_session.selecting,
                        'busy':busy,'current_task':current_task if busy else '',
                        'task_seconds':round(time.monotonic()-task_started,1) if busy else 0}),encoding='utf-8')
                except OSError:pass
        root.after(80,poll)
    threading.Thread(target=worker,daemon=True).start();poll()
    if voice_enabled.get() and not smoke:toggle_voice()
    if voice_enabled.get() and voice_config.get('start_hidden',True) and not smoke:
        root.withdraw();root.after_idle(lambda:win.restore_launch_focus(startup_target))
    else:root.deiconify()
    if smoke:root.after(1800,quit_app)
    root.mainloop()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task');parser.add_argument('--background',action='store_true');parser.add_argument('--ui-smoke',action='store_true')
    args=parser.parse_args()
    if args.task:
        from agent import Agent
        agent=Agent(confirm=lambda msg:input(msg+' [yes/no] ').strip().lower()=='yes')
        try:agent.run(args.task,args.background)
        finally:agent.close()
    else:
        from app_runtime import SingleInstance
        instance=SingleInstance()
        try:
            if instance.owner:gui(args.ui_smoke,instance)
        finally:instance.close()

if __name__=='__main__':main()

import json, re, threading, time, os
from datetime import datetime
from pathlib import Path
from catalog import Catalog, norm, launch_request, AmbiguousApp
from browser_control import Browser
from routing import search_intent, website_intent, browser_channel, explicit_browser, first_result_intent, text_entry_intent, normalize_launch_verb, named_click_intent, open_chat_intent
from planner import PlannerUnavailable,requested_point_action
from actions import validate_action, fingerprint, POINTS, IDS
from direct_commands import normalize_command,parse_direct,is_question,is_action_request

ROOT=Path(__file__).resolve().parent

class Agent:
    def __init__(self, log=print, confirm=lambda message:False, stop=None,choose=None):
        self.log=log; self.confirm=confirm; self.stop=stop or threading.Event()
        self.choose=choose
        self.config=json.loads((ROOT/'config.json').read_text())
        self.catalog=Catalog(); self.browser=Browser(); self.planner=None
        self.mode='desktop'; self.context=[]; self.last_task=None
        self.active_target=None; self.native=None
        self.desktop_bounds=None; self.visual=None
        self.visual_controls={}
        self.interaction=None
        self.background_requested=False
        self.task_index=0
        self.last_browser_window=None
        (ROOT/'logs').mkdir(exist_ok=True)
        self.logfile=ROOT/'logs'/('session-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.jsonl')

    def record(self, data):
        with self.logfile.open('a',encoding='utf8') as f: f.write(json.dumps(data,ensure_ascii=False,default=str)+'\n')

    def choose_targets(self,query,options,preview=None):
        """Attach screen marks only when file paths really belong to that view."""
        if not self.choose:return None
        options=[dict(option) for option in options]
        if any(option.get('path') for option in options) and self.interaction:
            try:
                from folder_control import explorer_folders,known_roots
                from accessibility import NativeControls
                from label_matching import normalize_label
                kind=self.interaction.get('class_name','');parents=[]
                if kind in ('CabinetWClass','ExploreWClass'):
                    parents=[p.resolve() for hwnd,p in explorer_folders() if hwnd==self.interaction['hwnd']]
                elif kind in ('Progman','WorkerW'):
                    roots=known_roots();parents=[p.resolve() for p in (roots[:1]+roots[-1:])]
                if parents:
                    controls=NativeControls().observe(hwnd=self.interaction['hwnd'])
                    for option in options:
                        path=Path(option['path'])
                        if path.parent.resolve() not in parents:continue
                        matches=[row for row in controls if normalize_label(row['name'])==normalize_label(path.name) and row.get('bounds')]
                        if matches:option['bounds']=matches[0]['bounds']
            except Exception:pass
        self.record({'target_choice_request':query,'candidates':[{'label':o['label'],'score':o.get('match_score'),'detail':o.get('detail','')} for o in options]})
        return self.choose(query,options,preview=preview)

    def _focus_native(self):
        if self.interaction and self.interaction.get('hwnd'):
            from windows_api import focus_handle,target_alive,snapshot,usable_target
            if not target_alive(self.interaction):
                self.record({'stale_target':self.interaction.get('hwnd'),'title':self.interaction.get('title')})
                fresh=snapshot();self.active_target=None
                self.interaction=fresh if usable_target(fresh) and target_alive(fresh) else None
                if self.interaction is None:return
            return focus_handle(self.interaction['hwnd'],self.interaction.get('title','target app'))
        self.native.focus_app(self.active_target)

    def _managed_target(self,context):
        if not self.browser.context: return False
        try:
            # A personal Chrome tab can have the same title as an owned tab.
            # Never use title coincidence as proof of a DOM connection.
            pid=getattr(self.browser,'process_id',None)
            if not isinstance(pid,int) or not pid or context.get('pid')!=pid:return False
            window_title=context.get('title','').lower()
            matches=[page for page in self.browser.context.pages if page.title() and page.title().lower() in window_title]
            if len(matches)!=1:return False
            self.browser.selected=matches[0]
            return True
        except Exception: return False

    def _navigate_browser(self,route,background):
        channel=route['channel']
        existing=browser_channel(self.interaction)
        if not background and existing==channel and not self._managed_target(self.interaction):
            from native_browser import navigate_window
            self.mode='desktop';self.active_target={'msedge':'edge'}.get(channel,channel)
            self.record({'browser_navigation_method':'existing_window_address_bar','hwnd':self.interaction['hwnd'],'url':route['url']})
            return navigate_window(self.interaction,route['url'],self.stop)
        self.dispatch({'action':'open_browser','channel':channel},background)
        self.active_target={'msedge':'edge'}.get(channel,channel)
        self.browser.act({'action':'navigate','url':route['url']})
        if not background:self.browser.page.bring_to_front()
        return self.browser.blocked_reason() or 'Browser navigation completed: '+self.browser.page.url

    def _direct(self,command):
        import desktop_control as desktop
        import windows_api as win
        if self.mode=='browser' and self.browser.context and self.browser.headless and self.background_requested:
            page=self.browser.page
            if command['kind']=='pointer': raise ValueError('Click here needs a visible app. In background browser mode, name the control to click.')
            if command['kind']=='scroll':
                amount=command['steps']*100*(-1 if command['direction'] in ('up','left') else 1)
                viewport=page.viewport_size or {'width':1280,'height':800}; page.mouse.move(viewport['width']/2,viewport['height']/2)
                page.mouse.wheel(amount if command['direction'] in ('left','right') else 0,amount if command['direction'] in ('up','down') else 0)
                return 'Scrolled '+command['direction']+'.'
            if command['kind']=='type':
                if not page.evaluate("()=>{let e=document.activeElement;return e && (e.isContentEditable || ['INPUT','TEXTAREA'].includes(e.tagName))}"): raise ValueError('Focus an input in the browser before typing.')
                page.keyboard.insert_text(command['text']); return 'Typed the requested text.'
            if command['kind']=='keys':
                names={'ctrl':'Control','alt':'Alt','shift':'Shift','enter':'Enter','esc':'Escape','tab':'Tab','space':'Space','backspace':'Backspace','delete':'Delete','pagedown':'PageDown','pageup':'PageUp','left':'ArrowLeft','right':'ArrowRight','up':'ArrowUp','down':'ArrowDown'}
                page.keyboard.press('+'.join(names.get(k,k) for k in command['keys'])); return 'Pressed the requested keys.'
        target=self.interaction or win.snapshot()
        if not target or target['title'].startswith('Gwen Doer'): raise ValueError('Select the app you want to control, then repeat the command.')
        if command['kind']=='scroll' and self._managed_target(target):
            amount=command['steps']*100
            if command['direction'] in ('up','left'): amount=-amount
            viewport=self.browser.page.viewport_size or {'width':1280,'height':800}
            self.browser.page.mouse.move(viewport['width']/2,viewport['height']/2)
            self.browser.page.mouse.wheel(amount if command['direction'] in ('left','right') else 0,amount if command['direction'] in ('up','down') else 0)
            return 'Scrolled '+command['direction']+'.'
        win.focus_handle(target['hwnd'],target['title'])
        bounds=desktop.window_bounds(target['hwnd'])
        if command['kind']=='pointer':
            if target.get('bounds') and tuple(target['bounds'])!=tuple(win.rect(target['hwnd'])): raise ValueError('The target window moved after you pointed. Point again and repeat.')
            x,y=target.get('pointer') or win.cursor()
            if not(bounds[0]<=x<bounds[2] and bounds[1]<=y<bounds[3]): raise ValueError('The pointer is outside the selected app. Point inside it and repeat.')
            desktop.act({'action':command['action'],'x':(x-bounds[0])*1000/(bounds[2]-bounds[0]),'y':(y-bounds[1])*1000/(bounds[3]-bounds[1])},bounds=bounds)
            return 'Clicked where you pointed.'
        if command['kind']=='scroll':
            x,y=target.get('pointer') or win.cursor()
            if not(bounds[0]<=x<bounds[2] and bounds[1]+80<=y<bounds[3]): x=(bounds[0]+bounds[2])//2; y=(bounds[1]+bounds[3])//2
            desktop.pg.moveTo(x,y,duration=.1)
            amount=command['steps']*(-1 if command['direction'] in ('down','left') else 1)
            win.scroll_at(target['hwnd'],x,y,amount,horizontal=command['direction'] in ('left','right'))
            return 'Scrolled '+command['direction']+'.'
        if command['kind']=='type': desktop.act({'action':'type','text':command['text']},bounds=bounds); return 'Typed the requested text.'
        if command['kind']=='keys': desktop.act({'action':'hotkey','keys':command['keys']},bounds=bounds); return 'Pressed '+ ' + '.join(command['keys'])+'.'
        raise ValueError('Unknown direct input')

    def dispatch(self, a, background):
        validate_action(a)
        op=a['action']
        if op=='open_app':
            self.interaction=None
            name=self.catalog.launch(a['name']); self.mode='desktop'
            self.active_target=name
            time.sleep(1); return 'Launch requested for '+name
        if op=='open_browser':
            self.interaction=None
            result=self.browser.open(a.get('channel','chrome'), background)
            self.active_target={'msedge':'edge','chromium':'chromium'}.get(a.get('channel','chrome'),'chrome')
            self.mode='browser'; return result
        if op=='desktop_mode':
            if self.browser.context and self.browser.headless: raise ValueError('Physical fallback unavailable in background mode. Disable background mode and reopen the browser.')
            self.mode='desktop'; return 'Using physical desktop'
        if op=='browser_mode': self.mode='browser'; return 'Using browser DOM'
        if op=='wait':
            self.stop.wait(max(0,min(5,float(a.get('seconds',1))))); return 'Waited'
        if op=='confirm':
            next_action=a.get('next_action',{})
            if next_action.get('action') in ('confirm','done','ask'): raise ValueError('Invalid confirmation action')
            if not self.confirm(a['message']): raise InterruptedError('User declined or stopped')
            if self.stop.is_set(): raise InterruptedError('Stopped')
            return self.dispatch(next_action,background)
        if op.startswith('browser_') or op=='navigate':
            self.mode='browser'; return self.browser.act(a)
        if op.startswith('ui_'):
            if a['id'] in self.visual_controls:
                if op!='ui_click': raise ValueError('OCR labels support clicks; select a real editable control for ui_fill')
                import desktop_control
                if desktop_control.foreground_handle()!=self.visual_hwnd or desktop_control.window_bounds(self.visual_hwnd)!=self.desktop_bounds: raise ValueError('Window changed after observation')
                box=self.visual_controls[a['id']]
                width,height=self.visual_size
                return desktop_control.act({'action':'click','x':(box[0]+box[2])*500/width,'y':(box[1]+box[3])*500/height},bounds=self.desktop_bounds)
            if self.native is None: raise ValueError('No current accessibility observation')
            return self.native.act(a)
        if self.mode=='browser' and self.browser.headless:
            raise ValueError('Background browser requires browser actions, not physical mouse/keyboard')
        import desktop_control
        if self.mode=='browser': raise ValueError('Use browser DOM actions; explicit desktop_mode is required for physical fallback')
        self.mode='desktop'
        return desktop_control.act(a,bounds=self.desktop_bounds)

    def click_named_native(self,label):
        from accessibility import NativeControls,named_control_id,ObservationChanged
        from label_matching import dialog_action
        import windows_api as win
        if self.native is None: self.native=NativeControls()
        # Dialog buttons must be actual buttons in a bound native window. Never
        # OCR arbitrary screen/chat text for Save/Don't Save/Cancel/Yes/No/OK.
        if dialog_action(label):return self.click_dialog_button(label)
        focused=self._focus_native()
        bound=focused if isinstance(focused,int) else self.interaction.get('hwnd') if self.interaction else None
        if bound:bound=win.action_window(bound)
        try: controls=self.native.observe(hwnd=bound) if bound else self.native.observe()
        except Exception as exc:
            self.record({'accessibility_error':str(exc),'fallback':'ocr'})
            controls=[]
        try:
            if self.choose:
                from target_choices import select_target
                control_id=select_target([c for c in controls if c.get('type')!='Group'],label,chooser=self.choose_targets,merge_overlaps=True)['row']['id']
            else:control_id=named_control_id(controls,label)
        except ValueError as exc:
            if 'More than one' in str(exc): raise
            import desktop_control
            from visual_targets import VisualTargets
            hwnd=bound or desktop_control.foreground_handle()
            if desktop_control.foreground_handle()!=hwnd:
                if win.focus_handle(hwnd,'requested target window')!=hwnd:raise ObservationChanged('A new dialog appeared; repeat the command for that dialog.')
            if desktop_control.foreground_title().startswith('Gwen Doer'): raise ValueError('Target app is not foreground')
            bounds=desktop_control.window_bounds(hwnd)
            image=desktop_control.capture(bounds,resize=False)
            if self.visual is None:
                self.log('Reading visible app text...'); self.visual=VisualTargets()
            if self.choose:
                from target_choices import select_target
                rows=[dict(row,bounds=[row['bounds'][0]+bounds[0],row['bounds'][1]+bounds[1],row['bounds'][2]+bounds[0],row['bounds'][3]+bounds[1]]) for row in self.visual.read(image) if row['score']>=.75]
                target=select_target(rows,label,key='text',chooser=self.choose_targets)['row']
                target=dict(target,bounds=[target['bounds'][0]-bounds[0],target['bounds'][1]-bounds[1],target['bounds'][2]-bounds[0],target['bounds'][3]-bounds[1]])
                if win.focus_handle(hwnd,'chosen target window')!=hwnd:raise ObservationChanged('The target dialog changed while choosing.')
                from label_matching import normalize_label
                left,top,right,bottom=target['bounds'];center=((left+right)/2,(top+bottom)/2)
                refreshed=self.visual.read(desktop_control.capture(bounds,resize=False))
                current=[r for r in refreshed if r['score']>=.75 and normalize_label(r['text'])==normalize_label(target['text']) and abs((r['bounds'][0]+r['bounds'][2])/2-center[0])<24 and abs((r['bounds'][1]+r['bounds'][3])/2-center[1])<24]
                if len(current)!=1:raise ObservationChanged('The chosen screen label moved or changed. Repeat the request to observe it again.')
                target=current[0]
            else:target=self.visual.find(image,label)
            from label_matching import match_description
            description=match_description(label,target['text'])
            if description:self.log(description)
            if self.stop.is_set(): raise InterruptedError('Stopped')
            if desktop_control.foreground_handle()!=hwnd or desktop_control.window_bounds(hwnd)!=bounds: raise ValueError('Target window changed during text recognition. Nothing was clicked.')
            left,top,right,bottom=target['bounds']
            action={'action':'click','x':(left+right)*500/image.width,'y':(top+bottom)*500/image.height}
            desktop_control.act(action,bounds=bounds)
            self.record({'native_target':label,'method':'ocr','target_window':self.active_target,'window_bounds':bounds,'text_bounds':target['bounds']})
            return 'Clicked the visible '+label+' text in '+str(self.active_target or 'the target app')+'.'
        if self.stop.is_set(): raise InterruptedError('Stopped')
        from label_matching import match_description
        matched=next((c['name'] for c in controls if c['id']==control_id),label)
        description=match_description(label,matched)
        if description:self.log(description)
        self.native.act(dict(action='ui_click',id=control_id,expected_name=matched) if self.choose else {'action':'ui_click','id':control_id})
        self.record({'native_target':label,'method':'accessibility','target_window':self.active_target,'control_id':control_id})
        return 'Clicked the observed '+label+' control.'

    def click_dialog_button(self,label):
        from accessibility import NativeControls,named_control_id,ObservationChanged
        from label_matching import match_description
        import windows_api as win
        requested=self.interaction.get('hwnd') if self.interaction else None
        requested=win.action_window(requested) if requested and win.user.IsWindow(requested) else None
        dialogs=win.blocking_dialogs()
        scopes=[requested] if requested in dialogs else list(dict.fromkeys([h for h in [requested,*dialogs] if h]))
        if not scopes:scopes=[win.action_window(win.stable_foreground())]
        choices=[];failures=[]
        for hwnd in scopes:
            probe=NativeControls()
            try:
                controls=probe.observe(hwnd=hwnd);control_id=named_control_id(controls,label)
                choices.append((hwnd,probe,controls,control_id))
            except Exception as exc:
                if 'More than one' in str(exc):raise
                failures.append({'hwnd':hwnd,'reason':str(exc)[:180]})
        if not choices:
            self.record({'dialog_lookup_failed':label,'scopes':scopes,'details':failures})
            raise ValueError('No enabled '+label+' button was found in the selected window or its save dialog. No screen-text fallback was used.')
        chosen=0
        if len(choices)>1:
            if not self.choose:raise ValueError('That button exists in more than one window. Select the intended dialog first.')
            options=[]
            for hwnd,probe,controls,control_id in choices:
                row=next(c for c in controls if c['id']==control_id)
                options.append(dict(row,label=row['name'],detail=win.title(hwnd),match_score=100))
            chosen=self.choose_targets(label,options)
            if chosen is None:raise InterruptedError('Selection cancelled. Nothing was clicked.')
        hwnd,probe,controls,control_id=choices[chosen]
        for attempt in range(2):
            if self.stop.is_set():raise InterruptedError('Stopped')
            try:
                self.native=probe
                name=next(c['name'] for c in controls if c['id']==control_id)
                description=match_description(label,name)
                if description:self.log(description)
                before=win.foreground()
                probe.act({'action':'ui_click','id':control_id})
                self.record({'native_target':label,'matched_name':name,'method':'dialog_accessibility','bound_hwnd':hwnd,'foreground_before':before})
                return 'Clicked the '+name+' button.'
            except ObservationChanged:
                if attempt:raise
                self.record({'dialog_reobserve':label,'old_bound':hwnd,'resolved_now':win.action_window(hwnd),'foreground_now':win.foreground()})
                hwnd=win.action_window(hwnd)
                probe=NativeControls();controls=probe.observe(hwnd=hwnd);control_id=named_control_id(controls,label)
            except Exception as exc:
                current=win.foreground()
                self.record({'dialog_action_error':str(exc),'bound_hwnd':hwnd,'foreground_now':current,'foreground_title':win.title(current)})
                raise

    def run(self, task, background=False, step_limit=None,interaction=None):
        self.interaction=interaction
        self.background_requested=background
        self.last_task=task
        self.task_index+=1
        if self.stop.is_set(): self.log('Stopped'); return 'Stopped'
        self.log('You: '+task); self.record({'task':task})
        if interaction: self.record({'interaction_target':interaction.get('title'),'target_hwnd':interaction.get('hwnd'),'pointer':interaction.get('pointer')})
        history=[]; result=''
        text_request=text_entry_intent(task)
        click_request=re.fullmatch(r'(?:please\s+)?click\s+(?:the\s+)?(.+?)\s+(?:button|link)[.!]?',task.strip(),re.I)
        try:
            normalized=normalize_launch_verb(normalize_command(task))
            if normalized!=task: self.log('Interpreted as: '+normalized); task=normalized
            from browser_commands import intent as browser_command_intent
            visible_browser=browser_channel(self.interaction)
            if visible_browser:self.last_browser_window=dict(self.interaction)
            managed_session=(not self.interaction or background) and self.mode=='browser' and bool(self.browser.context)
            browser_command=browser_command_intent(task,bool(visible_browser or managed_session))
            if browser_command and browser_command.get('implicit'):
                try:self.catalog.resolve(browser_command['target'])
                except ValueError:pass
                else:browser_command=None # Keep installed-app switches as window commands.
            if browser_command:
                try:
                    chooser=self.choose_targets if self.choose else None
                    if not visible_browser and not managed_session:
                        import windows_api as win
                        from window_commands import running_windows
                        remembered=self.last_browser_window
                        if remembered and win.target_alive(remembered):
                            self.interaction=dict(remembered,title=win.title(remembered['hwnd']))
                        else:
                            candidates=[row for row in running_windows() if browser_channel(row)]
                            selected=0
                            if len(candidates)>1:
                                if not chooser:raise ValueError('Several browser windows are open. Select one or specify its title first.')
                                selected=chooser('Which browser window?', [dict(row,label=row['title'],detail=row.get('process',''),match_score=100) for row in candidates])
                                if selected is None:raise InterruptedError('Browser selection cancelled.')
                            if candidates:self.interaction=candidates[selected]
                        visible_browser=browser_channel(self.interaction)
                    if visible_browser and not background and not self._managed_target(self.interaction):
                        from native_browser import command as native_browser_command
                        result=native_browser_command(self.interaction,browser_command,self.stop,chooser)
                        self.mode='desktop';self.active_target={'msedge':'edge'}.get(visible_browser,visible_browser)
                        self.last_browser_window=dict(self.interaction)
                    elif managed_session or (visible_browser and self._managed_target(self.interaction)):
                        result=self.browser.command(browser_command,chooser);self.mode='browser'
                    elif browser_command['action']=='tab_new':
                        self.dispatch({'action':'open_browser','channel':'chrome'},background)
                        result=self.browser.command(browser_command,chooser)
                    else:raise ValueError('Select the browser window, then repeat the tab/video command.')
                    self.record({'browser_command':browser_command,'result':result})
                except InterruptedError:raise
                except Exception as exc:result='Browser command stopped: '+str(exc)[:350]
                self.log(result);return result
            from window_commands import intent as window_intent,request_close,request_close_named,request_force_close,switch_to
            window_command=window_intent(task,self.catalog)
            if window_command:
                try:
                    if window_command['action']=='close_window':result=request_close(self.interaction,self.confirm,self.stop)
                    elif window_command['action']=='force_close_window':result=request_force_close(self.interaction,self.confirm,self.stop)
                    elif window_command['action'] in ('close_named','force_close_named'):
                        result=request_close_named(window_command['name'],self.catalog,self.interaction,self.confirm,self.stop,
                            self.choose_targets if self.choose else None,force=window_command['action']=='force_close_named')
                    else:
                        self.interaction=switch_to(window_command['name'],self.catalog,self.interaction)
                        self.mode='browser' if self._managed_target(self.interaction) else 'desktop'
                        self.active_target=self.interaction.get('title')
                        result='Switched to '+self.interaction['title']+'.'
                except Exception as exc:result='Window action stopped: '+str(exc)[:350]
                self.record({'window_command':window_command,'result':result})
                self.log(result);return result
            headless_context=background and self.mode=='browser' and self.browser.context and self.browser.headless
            if interaction and not headless_context and not interaction.get('title','').startswith('Gwen Doer'):
                if self._managed_target(interaction):
                    self.mode='browser';self.active_target={'msedge':'edge'}.get(self.browser.channel,self.browser.channel)
                else:
                    self.mode='desktop';title=interaction.get('title','')
                    channel=browser_channel(interaction)
                    self.active_target={'msedge':'edge'}.get(channel,channel) if channel else next((app for app in ('Task Manager','Microsoft Store','WhatsApp','Word','Excel','PowerPoint') if app.lower() in title.lower()),None)
            app_name=launch_request(task)
            if app_name:
                try:entry=self.catalog.resolve(app_name)
                except AmbiguousApp as exc:
                    result=str(exc);self.log(result);return result
                except ValueError:pass
                else:
                    canonical=norm(entry['name'])
                    if canonical in ('google chrome','chrome','microsoft edge','edge','chromium'):
                        channel='msedge' if 'edge' in canonical else 'chromium' if canonical=='chromium' else 'chrome'
                        result=self.dispatch({'action':'open_browser','channel':channel},background)
                    else:result=self.dispatch({'action':'open_app','name':app_name},background)
                    self.record({'route':'open_installed_app','requested_name':app_name,'matched_name':entry['name']})
                    self.log(result);return result
            website=website_intent(task,self.active_target)
            if website:
                self.record({'route':website})
                try:result=self._navigate_browser(website,background)
                except InterruptedError:raise
                except Exception as exc:result='Browser navigation stopped: '+str(exc)[:350]
                self.log(result);return result
            from file_control import open_requested_file
            file_result=open_requested_file(task,self.stop,self.record,self.interaction,chooser=self.choose_targets) if self.choose else open_requested_file(task,self.stop,self.record,self.interaction)
            if file_result is not None:
                result=file_result;self.log(result);return result
            from folder_control import open_requested_folder
            folder_result=open_requested_folder(task,self.stop,self.record,chooser=self.choose_targets) if self.choose else open_requested_folder(task,self.stop,self.record)
            if folder_result is not None:
                self.mode='desktop'; self.active_target=None; self.interaction=None
                result=folder_result; self.log(result); return result
            from office_control import office_kind,parse_office,execute_office
            office=office_kind(self.interaction)
            if office:
                command=parse_office(task)
                from office_language import related
                if command is None and related(task):
                    try:
                        from planner import Planner
                        import desktop_control
                        self._focus_native()
                        if self.planner is None:self.planner=Planner(self.config,self.stop,self.log)
                        command=self.planner.office_plan(task,office,desktop_control.capture(resize=False),self.logfile.with_suffix('')/f'task-{self.task_index:03d}')
                    except InterruptedError:raise
                    except Exception as exc:
                        result='Could not interpret this Office request: '+str(exc)[:250];self.log(result);return result
                if command and command['action']=='ask':
                    result=command['message'];self.log(result);return result
                if command:
                    try:
                        self._focus_native()
                        if self.stop.is_set():raise InterruptedError('Stopped')
                        result=execute_office(office,command,self.interaction,stop=self.stop)
                        self.record({'office_action':command['action'],'application':office,'result':result})
                    except InterruptedError:raise
                    except Exception as exc:
                        if command['action']=='new':
                            try:result=self.click_named_native({'word':'New blank document','excel':'Blank workbook','powerpoint':'Blank Presentation'}[office])
                            except Exception as fallback:result='Office action stopped: '+str(fallback).splitlines()[0][:300]
                        else:result='Office action stopped: '+str(exc).splitlines()[0][:300]
                    self.log(result);return result
            direct=parse_direct(task)
            if direct:
                try: result=self._direct(direct)
                except Exception as exc: result='Could not perform that input: '+str(exc)[:240]
                self.log(result); return result
            if is_question(task):
                from planner import Planner
                if self.planner is None: self.planner=Planner(self.config,self.stop,self.log)
                import desktop_control
                screen_image=desktop_control.capture(resize=False)
                result=self.planner.answer(task,self.context,image=screen_image); self.log(result); return result
            if not is_action_request(task):
                result='Please give a complete action or question. For example: scroll down, click on a name, or open an app.'
                self.log(result); return result
            site=None
            if self.mode=='browser' and self.browser.context:
                from urllib.parse import urlparse
                host=(urlparse(self.browser.page.url).hostname or '').lower()
                if host=='youtube.com' or host.endswith('.youtube.com'): site='youtube'
            route=search_intent(task,self.active_target,site)
            if route:
                self.log('Route: '+route['kind']); self.record({'route':route})
                if route['kind']=='native_search':
                    try:
                        from accessibility import NativeControls
                        if self.native is None: self.native=NativeControls()
                        self.native.focus_app(route['target'])
                        controls=self.native.observe()
                        fields=[e for e in controls if e['type'] in ('Edit','ComboBox') and any(t in (e['name']+' '+e.get('automation_id','')).lower() for t in ('search','filter','type a name'))]
                        if len(fields)!=1: raise ValueError('Could not identify a unique search field. No text was entered.')
                        self.native.act({'action':'ui_fill','id':fields[0]['id'],'text':route['query']})
                        result='Set the '+route['target']+' search field to '+route['query']+'.'
                    except Exception as exc:
                        self.record({'native_search_error':str(exc)})
                        result='Search stopped: '+str(exc)[:350]
                elif route['kind']=='store_search':
                    if route['query']!=route['original_query']: self.log('Search spelling: '+route['query'])
                    os.startfile(route['uri']); self.mode='desktop'; self.active_target='Microsoft Store'
                    result='Opened Microsoft Store search for '+route['query']+'.'
                else:
                    try:result=self._navigate_browser(route,background)
                    except InterruptedError:raise
                    except Exception as exc:result='Browser navigation stopped: '+str(exc)[:350]
                self.log(result); return result
            channel=explicit_browser(task)
            if channel: self.dispatch({'action':'open_browser','channel':channel},background)
            # Fast intent route for a single app-launch request. No inference delay.
            match=re.fullmatch(r'\s*(?:please\s+)?(?:open|launch|start)\s+(.+?)[.!]?\s*',task,re.I)
            if match:
                name=norm(match[1])
                if name in ('chrome','google chrome','edge','microsoft edge','browser','chromium'):
                    channel='msedge' if 'edge' in name else 'chromium' if name=='chromium' else 'chrome'
                    result=self.dispatch({'action':'open_browser','channel':channel},background)
                    self.active_target={'msedge':'edge','chromium':'chromium'}.get(channel,'chrome')
                    self.log(result); return result
            if self.mode=='browser':
                blocked=self.browser.blocked_reason()
                if blocked: result=blocked; self.log(result); return result
                label=named_click_intent(task)
                if label:
                    try: result=self.browser.click_named(label,chooser=self.choose_targets) if self.choose else self.browser.click_named(label)
                    except Exception as exc: result='Could not click '+label+': '+str(exc).split('Call log:')[0][:450]
                    self.log(result); return result
                first=first_result_intent(task)
                if first:
                    try: result=self.browser.open_first(first)
                    except Exception as exc: result='Could not open the first result: '+str(exc).split('Call log:')[0][:300]
                    self.log(result); return result
            else:
                chat=open_chat_intent(task)
                if chat and norm(self.active_target or '')!='whatsapp':
                    self.dispatch({'action':'open_app','name':'WhatsApp'},background)
                label=chat or named_click_intent(task)
                if label:
                    try:
                        result=self.click_named_native(label)
                    except InterruptedError: raise
                    except Exception as exc:
                        self.record({'native_click_error':str(exc)})
                        result='Could not click '+label+': '+str(exc).split('Call log:')[0][:250]
                    self.log(result); return result
            if self.mode=='desktop':
                app_suffix=re.search(r'\b(?:on|in|using)\s+(.+?)[.!]?$',task,re.I)
                if app_suffix:
                    try: self.active_target=self.catalog.resolve(app_suffix[1])['name']
                    except ValueError: pass
            errors=0; unchanged=0; previous_state=None; observed_hwnd=None; observed_window_bounds=None
            for i in range(step_limit or self.config['max_steps']):
                if self.stop.is_set(): raise InterruptedError('Stopped')
                image=None
                stage='observe'
                try:
                    if self.mode=='browser':
                        observation=self.browser.observe()
                        if observation.get('blocked'): raise InterruptedError(observation['blocked'])
                        import desktop_control
                        image=desktop_control.capture(resize=False)
                        self.desktop_bounds=desktop_control.screen_bounds()
                    else:
                        import desktop_control
                        from accessibility import NativeControls
                        if self.native is None: self.native=NativeControls()
                        if i==0 and self.active_target:
                            try: self._focus_native()
                            except Exception as exc: raise InterruptedError(str(exc)) from exc
                        elif i==0 and self.interaction: self._focus_native()
                        if desktop_control.foreground_title().startswith('Gwen Doer'):
                            raise InterruptedError('Stopped: Gwen is in the foreground instead of the target app. Open the app you want to control first.')
                        observed_hwnd=desktop_control.foreground_handle()
                        observed_window_bounds=desktop_control.window_bounds(observed_hwnd)
                        self.desktop_bounds=desktop_control.screen_bounds()
                        image=desktop_control.capture(resize=False)
                        observation={'mode':'desktop','foreground_window':desktop_control.foreground_title(),'screenshot_width':image.width,'screenshot_height':image.height,'active_app':self.active_target,'coordinate_space':'whole current screen; 0..1000 across the entire image','screen_bounds':self.desktop_bounds,'foreground_bounds':observed_window_bounds}
                        # Visual planning sees the image; named-control commands
                        # use the separate UIA/OCR route above. Do not combine the
                        # control-name dump with Qwen's coordinate prediction.
                        self.visual_controls={}
                    if image is not None and self.mode=='desktop':
                        state=image.resize((64,40)).tobytes()
                        unchanged=unchanged+1 if state==previous_state else 0
                        previous_state=state
                        if history and unchanged:
                            history[-1]['visual_feedback']='The previous action caused no visible change. Reinspect the target and choose a different action or ask; do not repeat the same click.'
                        if unchanged>=2: raise InterruptedError('Stopped: desktop did not change after two attempts. No more blind clicks.')
                    observation['mode']=self.mode
                    if self.planner is None:
                        from planner import Planner
                        stage='load_model'
                        self.planner=Planner(self.config,self.stop,self.log)
                    stage='plan'
                    trace_dir=self.logfile.with_suffix('')/f'task-{self.task_index:03d}'/f'step-{i+1:03d}'
                    self.record({'model_request':True,'window':observation.get('foreground_window'),'capture_size':list(image.size) if image else None,'screen_bounds':self.desktop_bounds,'foreground_bounds':observed_window_bounds,'input_trace':str(trace_dir)})
                    a=self.planner.next(task,observation,image,history,self.context,trace_dir=trace_dir)
                    self.record({'model_output':a})
                    stage='validate'
                    if text_request and a.get('action') in ('browser_fill','ui_fill'):
                        a['text']=text_request['text']
                    validate_action(a)
                    if a['action'] in IDS and a['id'] not in getattr(self.planner,'exposed_ids',set()):
                        raise ValueError('Element ID was not in the model observation. Choose one of the current visible control IDs.')
                    if self.stop.is_set(): raise InterruptedError('Stopped')
                    self.log(f'Step {i+1}: '+json.dumps(a,ensure_ascii=False))
                    self.record({'step':i+1,'action':a,'url':observation.get('url'),'window':observation.get('foreground_window')})
                    if a['action'] in ('done','ask'):
                        result=a.get('message','Finished'); self.log(result); return result
                    if click_request and a['action']=='browser_click':
                        target=next((e for e in observation.get('elements',[]) if e['id']==int(a['id'])),None)
                        if not target or norm(target['text'])!=norm(click_request[1]) or target['tag']=='INPUT':
                            raise ValueError('Selected element does not match the requested button/link label. Choose its correct ID.')
                    if sum(fingerprint(h['action'])==fingerprint(a) for h in history[-5:] if 'action' in h)>=2:
                        raise InterruptedError('Stopped a repeated action loop. Inspect the result and give the next instruction.')
                    if unchanged and history and history[-1].get('action') and fingerprint(history[-1]['action'])==fingerprint(a):
                        raise InterruptedError('Stopped: Qwen repeated an action that made no visible change. The repeated input was not sent. Exact model input is in the session trace.')
                    if a['action']=='type' and observation.get('native_controls') and not any(e.get('focused') and e['type'] in ('Edit','ComboBox') for e in observation['native_controls']):
                        raise ValueError('No observed text field has keyboard focus. Use ui_fill or focus the intended input before typing.')
                    if self.mode=='desktop' and a['action'] in POINTS|{'type','hotkey','press','scroll'}:
                        import desktop_control
                        if desktop_control.foreground_handle()!=observed_hwnd or desktop_control.window_bounds(observed_hwnd)!=observed_window_bounds or desktop_control.screen_bounds()!=self.desktop_bounds: raise InterruptedError('Window focus, position or screen size changed during planning; stopped before input.')
                    stage='execute'
                    if image is not None and a['action'] in POINTS:
                        from desktop_control import map_point
                        self.record({'coordinate_action':a,'screen_bounds':self.desktop_bounds,'foreground_bounds':observed_window_bounds,'screen_point':map_point(a['x'],a['y'],self.desktop_bounds)})
                    feedback=self.dispatch(a,background)
                    history.append({'action':a,'result':feedback})
                    if image is not None and requested_point_action(task) and a['action'] in POINTS:
                        # A single requested click is one input, not an open-ended
                        # task that should keep clicking until the VLM says done.
                        result={'click':'Clicked','double_click':'Double-clicked','right_click':'Right-clicked'}.get(a['action'],'Acted on')+' the requested visual target.'
                        self.log(result);return result
                    if text_request and a['action'] in ('browser_fill','ui_fill'):
                        result='Entered the full requested text in the selected field.'; self.log(result); return result
                    if click_request and a['action']=='browser_click':
                        result='Clicked '+click_request[1]+'.'; self.log(result); return result
                    errors=0; self.stop.wait(.6)
                except PlannerUnavailable as exc:
                    self.planner=None
                    raise InterruptedError(str(exc))
                except (InterruptedError, KeyboardInterrupt): raise
                except Exception as exc:
                    # PyAutoGUI corner fail-safe must end the task immediately.
                    if exc.__class__.__name__=='FailSafeException': raise InterruptedError('Mouse-corner emergency stop')
                    errors+=1; message=f'{type(exc).__name__}: {exc}'
                    self.record({'error':message,'stage':stage})
                    history.append({'error':message[:240]})
                    if self.mode=='desktop' or errors>=2:
                        description={'observe':'Could not observe the target window; Qwen was not called','load_model':'Could not load the local model','plan':'Model inference failed','validate':'The model returned an invalid action; it was not executed','execute':'Executing the action failed; inspect the app before retrying'}[stage]
                        raise InterruptedError(description+': '+str(exc).splitlines()[0][:220]+'. Details are in the session log.')
                    self.log('The proposed action was invalid. Trying one correction.')
            result='Step limit reached. Inspect the result and give the next instruction.'
            self.log(result); return result
        except InterruptedError as exc:
            result=str(exc); self.log(result); return result
        finally:
            self.context.append({'task':task,'result':result or 'Task failed; inspect logs'})
            self.context=self.context[-8:]

    def close(self): self.browser.close()

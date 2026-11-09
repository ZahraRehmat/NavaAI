"""Live accessibility target grid. No model calls and no OCR polling."""
import threading,time,re
from smart_mouse_actions import SmartMouseActions
from grid_commands import parse
from grid_display import ScreenBounds
from smart_labels import smart_label

def error_text(exc):
    return (str(exc).strip() or type(exc).__name__).splitlines()[0][:160]


class SmartMap:
    def __init__(self,monitors):
        self.monitors=list(map(tuple,monitors));self.geometry=ScreenBounds(monitors)
        self.labels={};self.targets={};self.next_label=0

    def update(self,rows):
        targets={}
        for row in rows:
            l,t,r,b=row['bounds']
            visible=[(max(l,ml),max(t,mt),min(r,mr),min(b,mb)) for ml,mt,mr,mb in self.monitors]
            visible=[box for box in visible if box[2]>box[0] and box[3]>box[1]]
            if not visible:continue
            l,t,r,b=max(visible,key=lambda box:(box[2]-box[0])*(box[3]-box[1]))
            key=row['key']
            if key not in self.labels:
                self.labels[key]=smart_label(self.next_label);self.next_label+=1
            label=self.labels[key]
            point=row.get('point',((l+r-1)//2,(t+b-1)//2))
            if not (l<=point[0]<r and t<=point[1]<b):point=((l+r-1)//2,(t+b-1)//2)
            targets[label]={**row,'bounds':(l,t,r,b),'label':label,'point':tuple(point)}
        changed=targets!=self.targets;self.targets=targets
        return changed

    def cell(self,label):
        label=re.sub(r'\s+','',label.upper())
        if label not in self.targets:raise ValueError('Smart target '+label+' is no longer visible. Use a currently displayed label.')
        return self.targets[label]

    def nearest(self,x,y):return self.geometry.nearest(x,y)

    def snapshot(self):
        areas=[]
        for i,box in enumerate(self.monitors):
            l,t,r,b=box
            cells=[]
            for cell in self.targets.values():
                x,y=cell['point']
                if l<=x<r and t<=y<b:cells.append(cell)
            areas.append({'monitor':i+1,'bounds':box,'cells':cells})
        return areas


class AccessibleTargets:
    """Isolate UIA's process-global COM singleton from the agent and refresh thread."""
    def __init__(self,target,response_timeout=6,window_timeout=2):
        self.target=target;self.process=None;self.answers=None;self.changed=threading.Event();self.last_timing={}
        self.response_timeout=response_timeout;self.warning='';self.quarantined={}
        self.window_timeout=window_timeout

    def wait_for_change(self,timeout):
        changed=self.changed.wait(timeout);self.changed.clear();return changed

    def close(self):
        process=self.process;self.process=None
        if process:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=2)
            except Exception:process.kill()
            for stream in (process.stdin,process.stdout):
                if stream:stream.close()

    def __call__(self):return self.scan()

    def scan(self,force=False,on_partial=None):
        import windows_api as win
        import subprocess,sys,json,queue
        from pathlib import Path
        context=win.choose_target(win.snapshot(),[self.target()])
        if not self.process or self.process.poll() is not None:
            self.close();self.answers=queue.Queue()
            executable=Path(sys.executable).with_name('python.exe')
            self.process=subprocess.Popen([str(executable),'-u',str(Path(__file__).with_name('smart_grid_observer.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
            process=self.process;answers=self.answers
            def read():
                try:
                    for line in process.stdout:
                        if '"changed": true' in line:self.changed.set()
                        else:answers.put(line)
                except (OSError,ValueError):pass
                finally:answers.put(None)
            threading.Thread(target=read,daemon=True,name='Smart grid UIA responses').start()
        partial=[];waiting_for=None;self.warning='';deadline=time.monotonic()+self.response_timeout;window_deadline=deadline
        try:
            self.quarantined={hwnd:until for hwnd,until in self.quarantined.items() if until>time.monotonic()}
            self.process.stdin.write(json.dumps({'context':context,'force':force,'skip':list(self.quarantined)})+'\n');self.process.stdin.flush()
            while True:
                remaining=min(deadline,window_deadline)-time.monotonic()
                if remaining<=0:raise queue.Empty()
                line=self.answers.get(timeout=remaining)
                if line is None:raise ValueError('Accessibility scanner stopped.')
                result=json.loads(line)
                if 'scanning' in result:
                    waiting_for=result['scanning'];window_deadline=min(deadline,time.monotonic()+self.window_timeout);continue
                if result.get('partial'):
                    partial=result['rows'];waiting_for=None;window_deadline=deadline
                    if on_partial:on_partial(partial)
                    continue
                break
            if 'error' in result:raise ValueError(result['error'])
            self.last_timing=result.get('timing',{})
            skipped=result.get('skipped',[])
            if skipped:self.warning='An unresponsive window is temporarily skipped; available targets are active.'
            return result['rows']
        except queue.Empty:
            if waiting_for:self.quarantined[int(waiting_for)]=time.monotonic()+15
            self.close()
            self.warning='Accessibility scan timed out; '+('available targets are active. Retrying the stalled window shortly.' if partial else 'retrying automatically. F8 stops.')
            return partial
        except Exception:
            self.close();raise


class AdaptiveGrid(SmartMouseActions):
    """Adaptive smart targets and their direct mouse controls."""
    def __init__(self,*args,observer,target_check=None,chooser=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.observer=observer;self.target_check=target_check;self.chooser=chooser;self.mode='smart';self.error=''
        self.generation=0;self.shutdown=threading.Event();self.scan_lock=threading.Lock()
        self.last_targets=[]
        self.thread=threading.Thread(target=self._watch,daemon=True,name='Gwen smart grid refresh');self.thread.start()

    def picture(self):
        self.render({'active':self.active,'mode':self.mode,'error':self.error,
                     'count':len(self.grid.targets) if self.active and self.mode=='smart' else 0,
                     'areas':self.grid.snapshot() if self.active else [],'config':self.config})

    def emergency_stop(self):
        with self.lock:
            self.generation+=1;super().emergency_stop()

    def close(self):
        self.shutdown.set();self.emergency_stop()
        # The watcher owns observation; finish it before disposing its helper.
        self.thread.join(timeout=7)
        if hasattr(self.observer,'close'):self.observer.close()

    def refresh(self,force=False):
        # Scan outside the input lock so F8 can always release held buttons.
        with self.scan_lock:
            with self.lock:
                if not self.active or self.mode!='smart' or self.mouse.held:return
                generation=self.generation
                initial=not self.grid.targets
            def publish_initial(rows):
                with self.lock:
                    if generation==self.generation and self.active and self.mode=='smart' and not self.mouse.held:
                        if self.grid.update(rows):self.picture()
            try:
                rows=self.observer.scan(force=force,on_partial=publish_initial if initial else None) if isinstance(self.observer,AccessibleTargets) else self.observer.scan(force=force) if hasattr(self.observer,'scan') else self.observer()
                error=getattr(self.observer,'warning','')
            except Exception as exc:rows=[];error=error_text(exc)
            with self.lock:
                if generation!=self.generation or not self.active or self.mode!='smart' or self.mouse.held:return
                boxes=list(map(tuple,self.displays()))
                topology_changed=boxes!=self.grid.monitors
                if topology_changed:
                    self.grid.monitors=boxes;self.grid.geometry=ScreenBounds(boxes)
                changed=self.grid.update(rows)
                if changed or topology_changed or error!=self.error:
                    self.error=error;self.picture()

    def _watch(self):
        last=0
        while not self.shutdown.wait(.04):
            if hasattr(self.observer,'wait_for_change'):
                changed=self.observer.wait_for_change(.12)
                if not changed and time.monotonic()-last<.35:continue
            elif self.shutdown.wait(.1):break
            last=time.monotonic()
            try:self.refresh()
            except Exception:
                # An unavailable display must not leave an old clickable map.
                with self.lock:
                    if self.active and self.mode=='smart':
                        self.grid.update([]);self.error='Screen changed; waiting for the next refresh.';self.picture()

    def run(self,task):
        self.last_targets=[]
        # A tab's grid label identifies that exact native TabItem. Do this
        # before generic "close app" parsing, which cannot resolve grid codes.
        close=re.fullmatch(r'close\s+(?:tab\s+)?([A-Za-z]{1,6})',task.strip(),re.I)
        if self.active and close and hasattr(self.mouse,'tab_action'):
            label=close[1].upper()
            with self.lock:cell=self.grid.targets.get(label)
            if cell and cell.get('type')=='TabItem':
                if self.mouse.held:raise ValueError('Release the held mouse button before closing a tab.')
                if self.target_check:self.target_check(cell)
                return self.mouse.tab_action(cell,self.stop,close=True)
        from grid_input import keyboard_command
        if self.active and keyboard_command(task):return None
        from smart_grid_names import parse_named,resolve_name
        try:actions=parse(task,self.active)
        except ValueError:
            if not self.active or self.mode!='smart':raise
            actions=parse_named(task)
            if not actions:raise
        if not actions and self.active and self.mode=='smart':actions=parse_named(task)
        if actions and any(a['action']=='dropdown_prompt' for a in actions):
            return 'Which dropdown? Say open Font dropdown, or open dropdown followed by its displayed label.'
        # Bare words which are not displayed labels may be short target names.
        if self.active and self.mode=='smart' and actions:
            from smart_grid_names import ALIASES
            for a in actions:
                label=(a.get('label') or '').upper().replace(' ','')
                if label and label not in self.grid.targets and (label.lower() in ALIASES or (label.isalpha() and len(label)>2)):
                    a['target_name']=label.lower();del a['label']
        if actions and len(actions)>1 and any(a['action'] in ('disable','smart_unavailable') for a in actions):
            raise ValueError('Turn the grid on/off separately from mouse-action chains.')
        if actions and actions[0]['action']=='smart_unavailable':
            self.emergency_stop()
            with self.lock:
                self.mode='smart';self.grid=SmartMap(self.displays());self.active=True;self.error='';self.point=self.grid.nearest(*self.mouse.position())
                self.generation+=1;self.picture()
            self.refresh()
            return ('Smart grid on. '+str(len(self.grid.targets))+' targets. Type A to click, move to A to move only, double click A, scroll down on A, or close grid. Labels refresh automatically. '
                    +(self.error or ('No accessible controls found here. Show the target app and refresh grid.' if not self.grid.targets else 'F8 stops and releases.')))
        if actions and actions[0]['action']=='disable':
            self.emergency_stop();return 'Smart grid off. Mouse released; agent commands remain available.'
        if not self.active:return None
        if not actions:
            from direct_commands import is_action_request,is_question
            if is_action_request(task) or is_question(task):return None
            return 'Smart grid is active. Use a displayed label, mouse commands, refresh grid, or close grid.'
        if any(a['action'] in ('smart_unavailable','disable') for a in actions):
            if len(actions)>1:raise ValueError('Switch grid modes separately from mouse commands.')
            self.emergency_stop();return 'Grid off. Mouse released; agent commands restored.'
        if self.stop.is_set():self.emergency_stop();return 'Stopped'
        with self.lock:
            roots={self.grid.targets[a[key]]['hwnd'] for a in actions for key in ('label','source') if a.get(key) in self.grid.targets}
        self.refresh(force=True if any(a['action']=='reset' for a in actions) else list(roots)) # Revalidate addressed windows, reuse unrelated trees.
        for a in actions:
            if a.get('target_name'):
                with self.lock:rows=list(self.grid.targets.values())
                try:selected=resolve_name(rows,a['target_name'],self.chooser)
                except Exception as exc:
                    from label_matching import NoLabelMatch
                    # Opening a named app/file/folder can use the agent's
                    # directory when it is not an observed manual grid target.
                    if isinstance(exc,NoLabelMatch) and len(actions)==1 and re.match(r'^\s*(?:please\s+)?(?:open|launch|start)\s+',task,re.I):return None
                    raise
                a['label']=selected['label']
                # A choice popup can outlive the original screen. Revalidate its identity.
                self.refresh(force=[selected['hwnd']])
        try:
            with self.lock:
                # Resolve every label before any part of a chain executes.
                for a in actions:
                    for key in ('label','source'):
                        if a.get(key):
                            cell=self.grid.cell(a[key])
                            if self.target_check:self.target_check(cell)
                            self.last_targets.append({k:cell.get(k) for k in ('label','name','type','bounds','point','key','hwnd','expandable','dropdown_owner')})
            messages=[]
            for index,a in enumerate(actions):
                if index:
                    with self.lock:roots={self.grid.targets[a[key]]['hwnd'] for key in ('label','source') if a.get(key) in self.grid.targets}
                    self.refresh(force=list(roots)) # A prior click can move targets or open menus.
                with self.lock:
                    if self.stop.is_set() or not self.active:raise InterruptedError('Stopped')
                    if a['action']=='reset':messages.append('Smart grid refreshed.');continue
                    for key in ('label','source'):
                        if a.get(key):
                            cell=self.grid.cell(a[key])
                            if self.target_check:self.target_check(cell)
                    messages.append(self.execute(a))
            return ' '.join(messages)
        except Exception:
            self.mouse.release();raise


def check_target(cell):
    """Refuse to click through an app that covered a recently observed target."""
    from grid_mouse import GridMouse
    import windows_api as win
    actual=GridMouse().target_at(cell['point'])
    if actual!=cell['hwnd'] and win.action_window(cell['hwnd'])!=actual:
        raise ValueError('Another window covers this target. Select the app or refresh grid before retrying.')

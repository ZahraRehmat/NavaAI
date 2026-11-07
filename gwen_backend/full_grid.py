"""Manual full-grid controller. UI rendering is a callback; AI is never involved."""
import json,threading,re
from pathlib import Path
from grid_commands import parse
from grid_geometry import GridMap

class FullGrid:
    def __init__(self,mouse,displays,render=lambda _:None,stop=None,config=None):
        self.mouse=mouse;self.displays=displays;self.render=render;self.stop=stop or threading.Event()
        self.config=config or json.loads(Path(__file__).with_name('full_grid_config.json').read_text())
        self.active=False;self.grid=None;self.point=None;self.lock=threading.RLock()

    def picture(self):self.render({'active':self.active,'areas':self.grid.snapshot() if self.active else [],'config':self.config})

    def emergency_stop(self):
        with self.lock:
            self.mouse.release();self.active=False;self.picture()

    def run(self,task):
        from grid_input import keyboard_command
        if self.active and keyboard_command(task):return None
        with self.lock:
            try:
                actions=parse(task,self.active)
                if actions is None:
                    if self.active:
                        from direct_commands import is_action_request,is_question
                        if is_action_request(task) or is_question(task):return None
                        return 'Full grid is active. Use a label, click/scroll/hold/move, or exit grid for agent commands.'
                    return None
                if not actions:return None
                if len(actions)>1 and any(a['action'] in ('enable','disable','smart_unavailable') for a in actions):raise ValueError('Enable/exit grid separately from mouse-action chains.')
                if actions[0]['action']=='smart_unavailable':return 'Smart grid is not enabled yet. Say Gwen full grid for the full-screen grid.'
                if actions[0]['action']=='disable':self.emergency_stop();return 'Full grid off. Mouse buttons released; agent commands restored.'
                if self.stop.is_set():self.mouse.release();return 'Stopped'
                if actions[0]['action']=='enable':
                    self.mouse.release();self.grid=GridMap(self.displays(),self.config['columns'],self.config['rows']);self.active=True;self.picture()
                    self.point=self.grid.nearest(*self.mouse.position())
                    return 'Full grid on. Type A1 to click, move to A1 to move only, double click A1, scroll down on G4, or exit grid. F8 stops and releases.'
                if not self.active:return None
                if re.match(r'^\s*(?:please\s+)?open\s+',task,re.I) and len(actions)==1 and actions[0].get('label'):
                    try:self.grid.cell(actions[0]['label'])
                    except ValueError:return None # A folder/app name, not a full-grid coordinate.
                if [tuple(b) for b in self.displays()]!=self.grid.monitors:
                    self.mouse.release();self.grid=GridMap(self.displays(),self.grid.columns,self.grid.rows);self.point=self.grid.nearest(*(self.point or self.mouse.position()));self.picture()
                    return 'Display layout changed. Grid refreshed; repeat the command. No mouse action was sent.'
                messages=[]
                for action in actions:
                    if self.stop.is_set():raise InterruptedError('Stopped')
                    messages.append(self.execute(action))
                return ' '.join(messages)
            except Exception:
                self.mouse.release();raise

    def execute(self,a):
        op=a['action'];label=a.get('label')
        if a.get('bare_label') and self.mouse.held:op='move'
        if op in ('zoom','reset','back','density'):
            self.mouse.release()
            if op=='zoom':self.grid.zoom(label)
            elif op=='reset':self.grid.reset()
            elif op=='back':self.grid.back()
            else:
                c,r=a['columns'],a['rows']
                if not(2<=c<=60 and 2<=r<=40 and c*r<=1200):raise ValueError('Use 2–60 columns, 2–40 rows, and at most 1,200 cells per screen.')
                self.grid=GridMap(self.grid.monitors,c,r)
            self.picture();return 'Grid updated. Labels refer to the displayed grid.'
        if op=='drag':
            if self.mouse.held:raise ValueError('Release the held button before starting a new drag.')
            source=self.grid.cell(a['source'])['point'];target=self.grid.cell(label)['point'];self.move(source)
            try:
                self.mouse.down()
                for step in range(1,21):
                    if self.stop.wait(.02):raise InterruptedError('Stopped during drag')
                    point=tuple(round(source[i]+(target[i]-source[i])*step/20) for i in (0,1));self.move(self.grid.nearest(*point),animate_held=False)
            finally:self.mouse.release()
            return f"Dragged {a['source'].upper()} to {label.upper()} and released."
        if op=='pixel':
            point=(a['x'],a['y'])
            if self.grid.nearest(*point)!=point:raise ValueError('That pixel is outside the connected displays.')
            self.move(point);return f'Moved to pixel {point[0]}, {point[1]}.'
        if op=='nudge':
            amount=a['amount']
            if not 1<=amount<=10000:raise ValueError('Use a movement of 1–10,000 pixels.')
            dx,dy={'left':(-amount,0),'right':(amount,0),'up':(0,-amount),'down':(0,amount)}[a['direction']]
            x,y=self.point or self.mouse.position();point=self.grid.nearest(x+dx,y+dy);self.move(point)
            return f'Moved {a["direction"]} to {point[0]}, {point[1]}.'
        if op in ('release','drop'):
            if self.mouse.held and self.point:self.move(self.point)
            self.mouse.release();return 'Mouse buttons released.'
        if op=='scroll' and not 1<=a['amount']<=30:raise ValueError('Use 1–30 scroll steps at a time.')
        if label:self.move(self.grid.cell(label)['point'])
        elif self.point:self.move(self.point)
        if op=='move':return 'Moved to '+label.upper()+'.'
        if op in ('hold','hold left','hold right'):
            self.mouse.down('right' if op=='hold right' else 'left');return 'Mouse held. Move to another cell or say release; F8 releases immediately.'
        if op=='scroll':self.mouse.scroll(a['direction'],a['amount']);return 'Scrolled '+a['direction']+'.'
        button='right' if op in ('right click','rightclick') else 'middle' if op=='middle click' else 'left'
        self.mouse.click(button,2 if op in ('double click','doubleclick') else 1,self.stop)
        return op.capitalize()+' completed'+(' at '+label.upper() if label else '')+'.'

    def move(self,point,animate_held=True):
        # Give the target app time to receive held-button motion before a later
        # release. A single instantaneous move/up can be coalesced by Windows.
        start=self.mouse.position();distance=max(abs(point[i]-start[i]) for i in (0,1))
        if self.mouse.held and animate_held and distance:
            steps=min(20,max(2,int(distance/12)))
            for step in range(1,steps+1):
                if self.stop.wait(.015):raise InterruptedError('Stopped during held movement')
                next_point=self.grid.nearest(*(round(start[i]+(point[i]-start[i])*step/steps) for i in (0,1)))
                self.mouse.move(next_point);self.point=tuple(next_point)
        else:self.mouse.move(point);self.point=tuple(point)

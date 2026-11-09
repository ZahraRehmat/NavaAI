"""Shared pointer actions for the adaptive smart-target grid."""
import json, threading
from pathlib import Path

class SmartMouseActions:

    def __init__(self, mouse, displays, render=lambda _: None, stop=None, config=None):
        self.mouse = mouse
        self.displays = displays
        self.render = render
        self.stop = stop or threading.Event()
        self.config = config or json.loads(Path(__file__).with_name('smart_grid_config.json').read_text())
        self.active = False
        self.grid = None
        self.point = None
        self.lock = threading.RLock()

    def emergency_stop(self):
        with self.lock:
            self.mouse.release()
            self.active = False
            self.picture()

    def execute(self, a):
        op = a['action']
        label = a.get('label')
        if a.get('bare_label') and self.mouse.held:
            op = 'move'
        if label and op in ('click','left click','double click','doubleclick') and not self.mouse.held:
            if self.grid.cell(label).get('type')=='TabItem' and hasattr(self.mouse,'tab_action'):
                selected=self.mouse.tab_action(self.grid.cell(label),self.stop)
                if selected is not None:return selected
            result=self.mouse.switch_taskbar(self.grid.cell(label),getattr(self,'chooser',None),self.stop) if hasattr(self.mouse,'switch_taskbar') else None
            if result is not None:return result
        if op == 'drag':
            if self.mouse.held:
                raise ValueError('Release the held button before starting a new drag.')
            source = self.grid.cell(a['source'])['point']
            target = self.grid.cell(label)['point']
            self.move(source)
            try:
                self.mouse.down()
                for step in range(1, 21):
                    if self.stop.wait(0.02):
                        raise InterruptedError('Stopped during drag')
                    point = tuple((round(source[i] + (target[i] - source[i]) * step / 20) for i in (0, 1)))
                    self.move(self.grid.nearest(*point), animate_held=False)
            finally:
                self.mouse.release()
            return f'Dragged {a['source'].upper()} to {label.upper()} and released.'
        if op == 'pixel':
            point = (a['x'], a['y'])
            if self.grid.nearest(*point) != point:
                raise ValueError('That pixel is outside the connected displays.')
            self.move(point)
            return f'Moved to pixel {point[0]}, {point[1]}.'
        if op == 'nudge':
            amount = a['amount']
            if not 1 <= amount <= 10000:
                raise ValueError('Use a movement of 1–10,000 pixels.')
            dx, dy = {'left': (-amount, 0), 'right': (amount, 0), 'up': (0, -amount), 'down': (0, amount)}[a['direction']]
            x, y = self.point or self.mouse.position()
            point = self.grid.nearest(x + dx, y + dy)
            self.move(point)
            return f'Moved {a['direction']} to {point[0]}, {point[1]}.'
        if op in ('release', 'drop'):
            if self.mouse.held and self.point:
                self.move(self.point)
            self.mouse.release()
            return 'Mouse buttons released.'
        if op == 'scroll' and (not 1 <= a['amount'] <= 30):
            raise ValueError('Use 1–30 scroll steps at a time.')
        if label:
            self.move(self.grid.cell(label)['point'])
        elif self.point:
            self.move(self.point)
        if label and (op=='expand' or (op in ('double click','doubleclick') and self.grid.cell(label).get('expandable'))):
            if self.mouse.held:raise ValueError('Release the held mouse button before opening a dropdown.')
            return self.mouse.expand(self.grid.cell(label),self.stop)
        if op == 'move':
            return 'Moved to ' + label.upper() + '.'
        if op in ('hold', 'hold left', 'hold right'):
            self.mouse.down('right' if op == 'hold right' else 'left')
            return 'Mouse held. Move to another cell or say release; F8 releases immediately.'
        if op == 'scroll':
            self.mouse.scroll(a['direction'], a['amount'])
            return 'Scrolled ' + a['direction'] + '.'
        button = 'right' if op in ('right click', 'rightclick') else 'middle' if op == 'middle click' else 'left'
        self.mouse.click(button, 2 if op in ('double click', 'doubleclick') else 1, self.stop)
        return op.capitalize() + ' completed' + (' at ' + label.upper() if label else '') + '.'

    def move(self, point, animate_held=True):
        start = self.mouse.position()
        distance = max((abs(point[i] - start[i]) for i in (0, 1)))
        if self.mouse.held and animate_held and distance:
            steps = min(20, max(2, int(distance / 12)))
            for step in range(1, steps + 1):
                if self.stop.wait(0.015):
                    raise InterruptedError('Stopped during held movement')
                next_point = self.grid.nearest(*(round(start[i] + (point[i] - start[i]) * step / steps) for i in (0, 1)))
                self.mouse.move(next_point)
                self.point = tuple(next_point)
        else:
            self.mouse.move(point)
            self.point = tuple(point)

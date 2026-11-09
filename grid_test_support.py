"""Deterministic mouse recorder for smart-grid regressions."""
class FakeMouse:

    def __init__(self):
        self.point = (0, 0)
        self.held = set()
        self.events = []
        self.fail = False

    def position(self):
        return self.point

    def move(self, p):
        if self.fail:
            raise PermissionError('blocked')
        self.point = p
        self.events.append(('move', p))

    def down(self, button='left'):
        self.held.add(button)
        self.events.append(('down', button))

    def release(self):
        self.held.clear()
        self.events.append(('release',))

    def click(self, button='left', count=1, stop=None):
        self.events.append(('click', button, count, self.point))

    def scroll(self, direction, amount):
        self.events.append(('scroll', direction, amount, self.point))

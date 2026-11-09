"""Short, target-bound dictation backlog; never queue unrelated agent tasks."""
from collections import deque
import time


class DictationQueue:
    def __init__(self,limit=8):self.items=deque();self.limit=limit
    def clear(self):self.items.clear()
    def push(self,text,context,epoch):
        if len(self.items)>=self.limit:return False
        self.items.append((text,dict(context),epoch,time.monotonic()));return True
    def pop(self,current,epoch):
        if not self.items:return None
        text,context,saved_epoch,when=self.items.popleft()
        before=context.get('interaction') or {};after=current.get('interaction') or {}
        if saved_epoch!=epoch or time.monotonic()-when>30 or not before or (before.get('hwnd'),before.get('pid'))!=(after.get('hwnd'),after.get('pid')):
            self.clear();raise ValueError('Queued dictation cancelled because the active app changed or the phrase expired.')
        return text,context.get('interaction')

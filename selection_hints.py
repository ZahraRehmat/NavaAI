"""Nonblocking, app-bound visible vocabulary for offline endpoint recognition."""
import re,threading,time
from collections import deque


def read_visible_words(target):
    from pywinauto.uia_defines import IUIA
    from comtypes.gen.UIAutomationClient import IUIAutomationTextPattern
    uia=IUIA().iuia;walker=uia.ControlViewWalker
    pending=deque([uia.ElementFromHandle(target['hwnd'])]);seen=0;fallback=[];deadline=time.monotonic()+1
    while pending and seen<350 and time.monotonic()<deadline:
        el=pending.popleft();seen+=1
        try:
            if el.CurrentIsOffscreen or el.CurrentIsPassword:continue
            if el.CurrentControlType in (50030,50004,50020):
                try:
                    words=[];known=set()
                    pattern=el.GetCurrentPattern(10014).QueryInterface(IUIAutomationTextPattern)
                    ranges=pattern.GetVisibleRanges()
                    for i in range(min(120,ranges.Length)):
                        if time.monotonic()>=deadline:break
                        for word in re.findall(r"[\w]+(?:[-’'][\w]+)*",ranges.GetElement(i).GetText(500)):
                            key=word.casefold()
                            if len(word)>=3 and key not in known:
                                words.append(word);known.add(key)
                            if len(words)>=100:break
                        if len(words)>=100:break
                    if words and el.CurrentControlType==50030:return ' '.join(words)[:600]
                    if words:fallback.extend(words)
                except Exception:pass
            child=walker.GetFirstChildElement(el);count=0
            while child and count<150 and len(pending)<350 and time.monotonic()<deadline:
                pending.append(child);count+=1;child=walker.GetNextSiblingElement(child)
        except Exception:pass
    return ' '.join(dict.fromkeys(fallback))[:600]


class VisibleWordHints:
    def __init__(self,reader=read_visible_words):
        self.reader=reader;self.lock=threading.Lock();self.cached={};self.pending=set();self.generation=0

    def clear(self):
        with self.lock:self.cached.clear();self.generation+=1

    def get(self,target):
        if not target or not target.get('hwnd'):return ''
        key=(target['hwnd'],target.get('pid'),target.get('title'),tuple(target.get('bounds') or ()))
        with self.lock:
            now=time.monotonic();saved=self.cached.get(key);value=saved[1] if saved and now-saved[0]<10 else ''
            if key not in self.pending and (not saved or now-saved[0]>2):
                self.pending.add(key);generation=self.generation
                threading.Thread(target=self.refresh,args=(key,dict(target),generation),daemon=True).start()
        return value

    def refresh(self,key,target,generation):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            try:value=self.reader(target)
            except Exception:value=''
            with self.lock:
                if generation==self.generation:
                    if len(self.cached)>4:self.cached.clear()
                    self.cached[key]=(time.monotonic(),value)
        finally:
            with self.lock:self.pending.discard(key)
            pythoncom.CoUninitialize()

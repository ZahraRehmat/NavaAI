"""Focused text editing via Windows TextPattern, without selecting whole documents."""
import re


class SelectionResolutionError(ValueError):
    """An endpoint needs clarification, or the user cancelled it."""


def endpoint_spec(phrase):
    # Literal matching is attempted first, so text such as "first day" stays literal.
    ordinals={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,
              'sixth':6,'seventh':7,'eighth':8,'ninth':9,'tenth':10,'last':-1}
    match=re.fullmatch(r'(?:the\s+)?(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last|\d+(?:st|nd|rd|th)?)(?:\s+occurrence\s+of)?\s+(.+)',phrase,re.I)
    if match:
        word=match[1].lower()
        return match[2],ordinals[word] if word in ordinals else int(re.match(r'\d+',word)[0])
    match=re.fullmatch(r'(.+?)\s+occurrence\s+(\d+)',phrase,re.I)
    return (match[1],int(match[2])) if match else (phrase,None)


def span_offsets(text,start,end,chooser=None,locate=None):
    def matches(phrase):
        pattern=r'(?<!\w)'+r'\s+'.join(re.escape(w) for w in phrase.split())+r'(?!\w)'
        found=list(re.finditer(pattern,text,re.I))
        if found:return found
        # Homophones only resolve against actual text, never rewrite dictation.
        groups=[('sun','son'),('there','their'),('to','too','two'),('for','four')]
        alternatives=next((g for g in groups if phrase.casefold() in g),())
        found=sorted([m for word in alternatives if word!=phrase.casefold() for m in re.finditer(r'(?<!\w)'+re.escape(word)+r'(?!\w)',text,re.I)],key=lambda m:m.start())
        if found:return found
        from rapidfuzz.fuzz import ratio
        words=list(re.finditer(r"\w+(?:[-’']\w+)*",text));count=len(phrase.split());scores={}
        wanted=re.sub(r'\W','',phrase.casefold())
        if len(wanted)<5:return []
        for size in range(max(1,count-1),min(6,count+1)+1):
            for i in range(len(words)-size+1):
                value=text[words[i].start():words[i+size-1].end()]
                key=re.sub(r'\W','',value.casefold());score=ratio(wanted,key)
                if score>=85:scores[key]=(score,value)
        ranked=sorted(scores.values(),reverse=True)
        if not ranked:return []
        if len(ranked)>1 and ranked[0][0]-ranked[1][0]<8:raise ValueError('Several similar words match. Say a longer endpoint phrase.')
        value=ranked[0][1]
        return list(re.finditer(r'(?<!\w)'+r'\s+'.join(re.escape(w) for w in value.split())+r'(?!\w)',text,re.I))
    def endpoint(phrase):
        # Prefer a complete literal phrase over interpreting ordinal words.
        literal=r'(?<!\w)'+r'\s+'.join(re.escape(w) for w in phrase.split())+r'(?!\w)'
        found=list(re.finditer(literal,text,re.I))
        if found:return found
        value,ordinal=endpoint_spec(phrase);found=matches(value)
        if ordinal is not None:
            if not found:raise ValueError('Those words were not found in the focused text field.')
            index=len(found)-1 if ordinal==-1 else ordinal-1
            if not 0<=index<len(found):
                raise SelectionResolutionError(f'Cannot find occurrence {ordinal} of "{value}"; found {len(found)}.')
            return [found[index]]
        return found

    def pick(found,role,phrase):
        if len(found)==1:return found[0]
        if not chooser:
            raise SelectionResolutionError('Those words occur more than once. Say first, second, or last before the endpoint, or choose an occurrence.')
        # Page within the existing A-Z voice chooser; never hide later occurrences.
        offset=0
        while True:
            batch=found[offset:offset+24];options=[]
            for i,item in enumerate(batch,offset+1):
                left=max(0,item.start()-55);right=min(len(text),item.end()+75)
                snippet=' '.join(text[left:item.start()].split())+' ['+item.group()+'] '+' '.join(text[item.end():right].split())
                option={'label':f'Occurrence {i}: '+snippet,
                        'detail':f'Line {text.count(chr(10),0,item.start())+1}, character {item.start()+1}',
                        'selection_role':role,'selection_phrase':phrase,'occurrence':i}
                if locate:
                    box=locate(item.start(),item.end())
                    if box:option['bounds']=box
                options.append(option)
            if offset+24<len(found):options.append({'label':'More occurrences','detail':'Show the next choices.',
                                                   'selection_role':role,'selection_phrase':phrase})
            choice=chooser(f'Which {role} occurrence of "{phrase}"?',options)
            if choice is None:raise SelectionResolutionError('Selection cancelled. Nothing was selected or copied.')
            if not isinstance(choice,int) or not 0<=choice<len(options):raise SelectionResolutionError('Invalid selection choice.')
            if choice<len(batch):return batch[choice]
            offset+=24

    starts=endpoint(start);ends=endpoint(end)
    last_end=max((b.start() for b in ends),default=-1)
    starts=[a for a in starts if a.start()<=last_end]
    if not starts:raise ValueError('Those words were not found in the focused text field.')
    a=pick(starts,'start',start)
    ends=[b for b in ends if b.start()>=a.start()]
    if not ends:raise ValueError('The end word must occur at or after the selected start.')
    b=pick(ends,'end',end)
    return a.start(),b.end()


def native_span(region,text,left,right):
    """Map actual provider characters, verifying the result before using it.

    Chromium FindText can return a different prefix across block boundaries.
    Neither a successful search nor a moved-character count proves the range.
    """
    wanted=text[left:right]
    result=region.Clone();result.MoveEndpointByRange(1,result,0)
    result.MoveEndpointByUnit(1,0,right)
    result.MoveEndpointByUnit(0,0,left)
    if result.GetText(100001)==wanted:return result
    # Some providers count surrogate pairs/line breaks differently. A search
    # fallback is usable only when both the prefix and final span are exact.
    search=region.Clone()
    if left:
        prefix=region.FindText(text[:left],False,False)
        if not prefix or prefix.GetText(100001)!=text[:left]:
            raise ValueError('The app could not map the requested text range accurately.')
        search.MoveEndpointByRange(0,prefix,1)
    result=search.FindText(wanted,False,False)
    if not result or result.GetText(100001)!=wanted:
        raise ValueError('The app could not map the requested text range accurately.')
    return result


def native_locator(region,text):
    def locate(left,right):
        import math
        if region.GetText(100001)!=text:
            raise SelectionResolutionError('The text changed while marking choices; repeat selection.')
        try:
            values=list(native_span(region,text,left,right).GetBoundingRectangles())
            for i in range(0,len(values)-3,4):
                x,y,w,h=map(float,values[i:i+4])
                if all(math.isfinite(v) for v in (x,y,w,h)) and w>0 and h>0:
                    return [x,y,x+w,y+h]
        except SelectionResolutionError:raise
        except Exception:pass
        return None
    return locate



def spaced_text(value,before=None,selected=False):
    if selected or not before or not value:return value
    if before[-1].isspace() or value[0].isspace() or value[0] in '.,!?;:)]}':return value
    if before[-1] in '([{\n':return value
    return ' '+value


class FocusedText:
    def __init__(self,target):
        import windows_api as win
        from pywinauto.uia_defines import IUIA
        from comtypes.gen.UIAutomationClient import IUIAutomationTextPattern
        self.target=target;self.win=win;self.uia=IUIA().iuia
        self.element=self.uia.GetFocusedElement()
        if self.element.CurrentProcessId!=target['pid']:raise ValueError('The focused text belongs to another app.')
        if self.element.CurrentIsPassword:raise ValueError('Text inspection is unavailable in password fields.')
        self.identity=tuple(self.element.GetRuntimeId())
        el=self.element;self.pattern=None
        for _ in range(6):
            if not el or el.CurrentProcessId!=target['pid']:break
            try:
                self.pattern=el.GetCurrentPattern(10014).QueryInterface(IUIAutomationTextPattern)
                break
            except Exception:el=self.uia.ControlViewWalker.GetParentElement(el)
        if self.pattern is None:raise ValueError('This app does not expose text selection through Windows accessibility.')

    def check(self):
        if self.win.foreground()!=self.target['hwnd']:raise ValueError('The active app changed; repeat the text command.')
        if tuple(self.uia.GetFocusedElement().GetRuntimeId())!=self.identity:raise ValueError('The focused field changed; repeat the text command.')

    def preceding(self):
        self.check();ranges=self.pattern.GetSelection()
        if ranges.Length!=1:return None,False
        selection=ranges.GetElement(0)
        if selection.GetText(1):return None,True
        before=selection.Clone();before.MoveEndpointByUnit(0,0,-1)
        return before.GetText(4),False

    def select(self,start,end,copy=False,chooser=None):
        self.check();document=self.pattern.DocumentRange
        text=document.GetText(100001)
        if len(text)>100000:raise ValueError('Focus a smaller text field before selecting by words.')
        left,right=span_offsets(text,start,end,chooser=chooser,locate=native_locator(document,text))
        self.check()
        if document.GetText(100001)!=text:raise SelectionResolutionError('The text changed while choosing; repeat selection.')
        result=native_span(document,text,left,right)
        self.check();result.Select()
        if copy:return copy_selected(text[left:right])
        return 'Selected text from '+start+' to '+end+'.'


def copy_selected(text):
    import pyperclip
    pyperclip.copy(text)
    if pyperclip.paste()!=text:raise ValueError('The clipboard changed before copying could be verified.')
    return 'Selected and copied '+str(len(text))+' characters.'


def select_screen_text(target,start,end,copy=False,chooser=None):
    """Try the focused provider, then visible document/edit providers in this app."""
    try:return FocusedText(target).select(start,end,copy=copy,chooser=chooser)
    except ValueError as exc:
        if isinstance(exc,SelectionResolutionError) or 'Several similar' in str(exc):raise
    import time
    import windows_api as win
    from collections import deque
    from pywinauto.uia_defines import IUIA
    from comtypes.gen.UIAutomationClient import IUIAutomationTextPattern
    uia=IUIA().iuia;walker=uia.ControlViewWalker
    pending=deque([uia.ElementFromHandle(target['hwnd'])]);candidates=[];seen=0;deadline=time.monotonic()+2
    identities=set()
    while pending and seen<900 and time.monotonic()<deadline:
        el=pending.popleft();seen+=1
        try:
            # Embedded Chromium/Electron documents may use a renderer PID.
            # Membership in this HWND's UIA subtree binds them to the app.
            if el.CurrentIsOffscreen or el.CurrentIsPassword:continue
            identity=tuple(el.GetRuntimeId())
            if identity in identities:continue
            identities.add(identity);matched=False
            if el.CurrentControlType in (50030,50004,50020,50025,50026,50033):
                try:
                    pattern=el.GetCurrentPattern(10014).QueryInterface(IUIAutomationTextPattern)
                    if pattern.SupportedTextSelection==0:raise RuntimeError('Provider cannot select text')
                    visible=pattern.GetVisibleRanges()
                    if visible.Length:
                        region=visible.GetElement(0).Clone();region.MoveEndpointByRange(1,visible.GetElement(visible.Length-1),1)
                    else:
                        # Some browser providers omit GetVisibleRanges. Require
                        # real endpoint geometry before using their document.
                        region=pattern.DocumentRange
                    text=region.GetText(100001)
                    if text and len(text)<=100000:
                        left,right=span_offsets(text,start,end,chooser=lambda *args:0)
                        if not visible.Length:
                            locator=native_locator(region,text)
                            if not locator(left,left+1) or not locator(right-1,right):
                                raise ValueError('The endpoints are not visible.')
                        candidates.append((region,text,el));matched=True
                except Exception:pass
            # A matching document covers its nested paragraphs too.
            if matched:continue
            child=walker.GetFirstChildElement(el);children=0
            while child and children<200 and len(pending)<900 and time.monotonic()<deadline:
                pending.append(child);children+=1;child=walker.GetNextSiblingElement(child)
        except Exception:continue
    if not candidates:raise ValueError('Could not find both endpoints in selectable text in the active app. Bring that text into view and repeat.')
    index=0
    if len(candidates)>1:
        if not chooser:raise SelectionResolutionError('More than one selectable text area matches. Focus the intended text or say longer endpoint phrases.')
        options=[]
        for _,text,el in candidates[:26]:
            name=el.CurrentName or 'Selectable text'
            option={'label':name[:100],'detail':' '.join(text.split())[:160],
                    'selection_role':'text area','selection_phrase':'matching text'}
            try:
                box=el.CurrentBoundingRectangle
                option['bounds']=[box.left,box.top,box.right,box.bottom]
            except Exception:pass
            options.append(option)
        index=chooser('Which text area?',options)
        if index is None:raise SelectionResolutionError('Selection cancelled. Nothing was selected or copied.')
        if not isinstance(index,int) or not 0<=index<len(options):raise SelectionResolutionError('Invalid text area choice.')
    region,text,el=candidates[index]
    left,right=span_offsets(text,start,end,chooser=chooser,locate=native_locator(region,text))
    if win.foreground()!=target['hwnd']:raise SelectionResolutionError('The active app changed; repeat selection.')
    if region.GetText(100001)!=text:raise SelectionResolutionError('The text changed while choosing; repeat selection.')
    chosen=native_span(region,text,left,right);chosen.Select()
    return copy_selected(text[left:right]) if copy else 'Selected the requested text.'



def prepare_text(value,target):
    try:
        before,selected=FocusedText(target).preceding()
        return spaced_text(value,before,selected)
    except Exception:
        # Never probe by cutting/copying neighbouring user text or guess a caret position.
        return value


def browser_type(page,value):
    state=page.evaluate("""()=>{const e=document.activeElement;if(!e||e.type==='password')return null;
      if(typeof e.selectionStart==='number')return {before:e.value.slice(0,e.selectionStart),selected:e.selectionStart!==e.selectionEnd};
      const s=getSelection();if(e.isContentEditable&&s.rangeCount&&e.contains(s.anchorNode)){
        const r=s.getRangeAt(0).cloneRange();r.selectNodeContents(e);r.setEnd(s.anchorNode,s.anchorOffset);
        return {before:r.toString(),selected:!s.isCollapsed};}return null;}""")
    page.keyboard.insert_text(spaced_text(value,**state) if state else value)


def browser_select(page,start,end,copy=False,chooser=None):
    handle=page.evaluate_handle('document.activeElement')
    try:
        text=handle.evaluate("e=>e.type==='password'?null:(['INPUT','TEXTAREA'].includes(e.tagName)?e.value:e.isContentEditable?e.textContent:null)")
        if text is None:
            from rendered_text import browser_document_select
            return browser_document_select(page,start,end,copy,chooser)
        try:left,right=span_offsets(text,start,end,chooser=chooser)
        except SelectionResolutionError:raise
        except ValueError:
            from rendered_text import browser_document_select
            return browser_document_select(page,start,end,copy,chooser)
        selected_text=text[left:right]
        # DOM Range offsets use UTF-16 units, including surrogate pairs.
        left=len(text[:left].encode('utf-16-le'))//2;right=len(text[:right].encode('utf-16-le'))//2
        handle.evaluate("""(e,p)=>{if(document.activeElement!==e||!e.isConnected||(typeof e.value==='string'?e.value:e.textContent)!==p.text)throw Error('The focused text changed');
          if(e.setSelectionRange){e.setSelectionRange(p.left,p.right);return;}
          const walk=document.createTreeWalker(e,NodeFilter.SHOW_TEXT),r=document.createRange();let n,at=0,found=false;
          while(n=walk.nextNode()){const end=at+n.length;if(!found&&p.left<=end){r.setStart(n,p.left-at);found=true;}
            if(found&&p.right<=end){r.setEnd(n,p.right-at);const s=getSelection();s.removeAllRanges();s.addRange(r);return;}at=end;}
          throw Error('Text range is unavailable');} """,{'text':text,'left':left,'right':right})
        return copy_selected(selected_text) if copy else 'Selected text from '+start+' to '+end+'.'
    finally:handle.dispose()

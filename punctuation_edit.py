"""Apply verified punctuation to the selected text or current editing scope."""
from dictation_punctuation import engine,edits


def u16(text):return len(text.encode('utf-16-le'))//2


def check_target(context,stop):
    import windows_api as win
    if stop and stop.is_set():raise InterruptedError('Stopped punctuation')
    if context and win.foreground()!=context['hwnd']:raise ValueError('The active app changed. Nothing further was edited.')


def office_punctuation(app,kind,context=None,stop=None):
    check_target(context,stop)
    if kind=='word':
        document=app.ActiveDocument;scope=app.Selection.Range.Duplicate
        if scope.Start==scope.End:scope=document.Content.Duplicate
        before=scope.Text
    elif kind=='excel':
        scope=app.ActiveCell
        if scope.HasFormula:raise ValueError('Formula cells are not punctuated.')
        before=scope.Value2
        if not isinstance(before,str):raise ValueError('Select a cell containing text to punctuate.')
    else:
        try:scope=app.ActiveWindow.Selection.TextRange
        except Exception:raise ValueError('Place the caret in a PowerPoint text box first.')
        before=scope.Text
    after=engine().restore(before,stop);changes=edits(before,after)
    if not changes:return 'The text already has the predicted punctuation.'
    check_target(context,stop)
    current=scope.Value2 if kind=='excel' else scope.Text
    if current!=before:raise ValueError('The text changed during punctuation. Nothing was edited.')
    if kind=='excel':scope.Value2=after
    elif kind=='word':
        start=scope.Start;record=False
        try:
            try:app.UndoRecord.StartCustomRecord('Gwen punctuation');record=True
            except Exception:pass
            for left,right,value in reversed(changes):
                check_target(context,stop)
                document.Range(start+u16(before[:left]),start+u16(before[:right])).Text=value
        finally:
            if record:app.UndoRecord.EndCustomRecord()
    else:
        for left,right,value in reversed(changes):
            check_target(context,stop)
            a=u16(before[:left]);n=u16(before[left:right])
            if n:scope.Characters(a+1,n).Text=value
            elif a==u16(before):scope.Characters(a,1).InsertAfter(value)
            else:scope.Characters(a+1,1).InsertBefore(value)
    return 'Punctuated the selected text or current '+('cell' if kind=='excel' else 'document' if kind=='word' else 'text box')+'.'


def accessible_punctuation(context,stop=None):
    from text_input import FocusedText
    access=FocusedText(context)
    element=access.element
    writable=element.CurrentControlType==50004 or context.get('class_name')=='Notepad'
    try:writable=writable or bool(element.GetCurrentPropertyValue(30149))
    except Exception:pass
    if not writable:raise ValueError('Focus an editable text field before saying punctuate it.')
    selection=access.pattern.GetSelection();scope=access.pattern.DocumentRange;selected=False
    if selection.Length==1 and selection.GetElement(0).GetText(1):scope=selection.GetElement(0);selected=True
    before=scope.GetText(20001);after=engine().restore(before,stop);edits(before,after)
    if after==before:return 'The text already has the predicted punctuation.'
    access.check();check_target(context,stop)
    if scope.GetText(20001)!=before:raise ValueError('The text changed during punctuation. Nothing was edited.')
    if not selected:
        try:
            from comtypes.gen.UIAutomationClient import IUIAutomationValuePattern
            value=element.GetCurrentPattern(10002).QueryInterface(IUIAutomationValuePattern)
        except Exception:value=None
        if value is not None:
            if value.CurrentIsReadOnly:raise ValueError('This text field is read-only.')
            if value.CurrentValue==before:
                value.SetValue(after)
                try:
                    caret=access.pattern.DocumentRange.Clone();caret.MoveEndpointByRange(0,caret,1);caret.Select()
                except Exception:pass
                return 'Punctuated the current text field.'
    if any(c in after for c in '\r\n\t'):raise ValueError('Select a single paragraph in this app, or use Word for multi-paragraph punctuation.')
    scope.Select();check_target(context,stop)
    from unicode_keyboard import type_unicode
    type_unicode(after,context['hwnd'],stop)
    return 'Punctuated the selected text or current text field.'


def browser_punctuation(page,stop=None):
    handle=page.evaluate_handle('document.activeElement')
    try:
        state=handle.evaluate("""e=>{if(e.type==='password')throw Error('Password fields are not read');if(e.readOnly||e.disabled)throw Error('The field is read-only');
          if(typeof e.selectionStart==='number'){let a=e.selectionStart,b=e.selectionEnd;if(a===b){a=0;b=e.value.length;}return {text:e.value,start:a,end:b,plain:true};}
          if(e.isContentEditable){const s=getSelection();let a=0,b=e.textContent.length;
            if(s.rangeCount&&!s.isCollapsed&&e.contains(s.anchorNode)&&e.contains(s.focusNode)){const r=s.getRangeAt(0),p=r.cloneRange();p.selectNodeContents(e);p.setEnd(r.startContainer,r.startOffset);a=p.toString().length;b=a+r.toString().length;}
            return {text:e.textContent,start:a,end:b,plain:false};}throw Error('Focus an editable text field first');}""")
        before=state['text'].encode('utf-16-le')[state['start']*2:state['end']*2].decode('utf-16-le')
        after=engine().restore(before,stop);changes=edits(before,after)
        if stop and stop.is_set():raise InterruptedError('Stopped punctuation')
        operations=[{'a':state['start']+u16(before[:a]),'b':state['start']+u16(before[:b]),'text':value} for a,b,value in reversed(changes)]
        handle.evaluate("""(e,p)=>{if(document.activeElement!==e||(p.state.plain?e.value:e.textContent)!==p.state.text)throw Error('The text field changed');
          if(p.state.plain){e.setRangeText(p.after,p.state.start,p.state.end,'end');e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertReplacementText'}));return;}
          function point(offset){const w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n,last;while(n=w.nextNode()){last=n;if(offset<=n.length)return [n,offset];offset-=n.length;}if(last)return [last,last.length];throw Error('No text node');}
          for(const op of p.ops){const a=point(op.a),b=point(op.b),r=document.createRange();r.setStart(...a);r.setEnd(...b);const s=getSelection();s.removeAllRanges();s.addRange(r);if(!document.execCommand('insertText',false,op.text))throw Error('The editor refused punctuation');}
        }""",{'state':state,'after':after,'ops':operations})
        return 'Punctuated the selected text or current text field.'
    finally:handle.dispose()

"""Small native Office adapter. Fixed operations only; no VBA/code execution."""
import re

APPS={'word':'Word.Application','excel':'Excel.Application','powerpoint':'PowerPoint.Application'}

def office_hwnd(app,kind):
    owner=app.ActiveWindow if kind=='word' else app
    try:value=owner.HWND if kind=='powerpoint' else owner.Hwnd
    except AttributeError:
        import pythoncom
        dispatch=owner._oleobj_
        value=dispatch.Invoke(dispatch.GetIDsOfNames('Hwnd'),0,pythoncom.DISPATCH_PROPERTYGET,True)
    return int(value() if callable(value) else value)

def column_name(number):
    result=''
    while number:
        number,remainder=divmod(number-1,26);result=chr(65+remainder)+result
    return result

def unquote(text):
    return text[1:-1] if len(text)>1 and text[0]==text[-1] and text[0] in ('"',"'") else text

def office_kind(context):
    if not context:return None
    kind={'OpusApp':'word','XLMAIN':'excel','PPTFrameClass':'powerpoint'}.get(context.get('class_name'))
    if kind:return kind
    title=context.get('title','')
    for name in APPS:
        if re.search(r'(?:^| - )(?:Microsoft )?'+name+r'$',title,re.I):return name
    return None

def parse_office(task):
    from office_language import parse_extended
    extended=parse_extended(task)
    if extended:return extended
    raw=re.sub(r'^\s*(?:please\s+|can you\s+|could you\s+)','',task,flags=re.I).strip()
    clean=raw.rstrip('.!')
    clean=re.sub(r'\s+(?:in|on|using)\s+(?:microsoft\s+)?(?:word|excel|powerpoint|ppt)$','',clean,flags=re.I)
    text=clean.casefold()
    if text in ('new document','new blank document','create document','create blank document','open blank document','click new blank document','new workbook','blank workbook','open blank workbook','click blank workbook','new presentation'):
        return {'action':'new'}
    m=re.fullmatch(r'(?:make|set)\s+(.+?)\s+(bold|italic|underlined?)',clean,re.I)
    if m:return {'action':'format','style':m[2].lower().replace('underlined','underline'),'target':unquote(m[1]),'value':True}
    m=re.fullmatch(r'(bold|italic|italicize|underline|unbold)(?:\s+(.*))?',clean,re.I)
    if m:return {'action':'format','style':{'italicize':'italic','unbold':'bold'}.get(m[1].lower(),m[1].lower()),'target':unquote(m[2] or ''),'value':m[1].lower()!='unbold'}
    m=re.fullmatch(r'(?:click|apply|turn on)\s+(?:the\s+)?(bold|italic|underline)(?:\s+button)?',clean,re.I)
    if m:return {'action':'format','style':m[1].lower(),'target':'','value':'toggle' if text.startswith('click') else True}
    if re.match(r'^(?:insert|add|create|make|put)\b',text) and re.search(r'\btable\b',text):
        if re.search(r'\b(?:then|containing|with data|with headers|and (?:fill|write|type|bold|format))\b',text):return None
        numbers={'one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9','ten':'10'}
        dims=re.sub(r'\b('+ '|'.join(numbers)+r')\b',lambda m:numbers[m[0]],text)
        pair=re.search(r'(\d+)\s*(?:x|by|×)\s*(\d+)',dims)
        row=re.search(r'(\d+)\s*rows?',dims);col=re.search(r'(\d+)\s*(?:columns?|cols?)',dims)
        r,c=(int(pair[1]),int(pair[2])) if pair else (int(row[1]) if row else 3,int(col[1]) if col else 3)
        if not(1<=r<=50 and 1<=c<=20):raise ValueError('Use a table size of 1–50 rows and 1–20 columns.')
        return {'action':'table','rows':r,'columns':c,'explicit_size':bool(pair or row or col)}
    m=re.fullmatch(r'(?:write|enter|put)\s+(.+?)\s+(?:in|into|at)\s+([A-Z]{1,3}\d+(?::[A-Z]{1,3}\d+)?)[.!]?',raw,re.I|re.S)
    if m:return {'action':'write','text':unquote(m[1]),'range':m[2].upper()}
    m=re.fullmatch(r'(?:type|write|enter)\s+(.+)',raw,re.I|re.S)
    if m:return {'action':'write','text':unquote(m[1]),'range':None}
    return None

def _set_font(font,kind,style,value):
    prop={'bold':'Bold','italic':'Italic','underline':'Underline'}[style]
    if value=='toggle':value=not(getattr(font,prop) in (True,-1,1,2))
    if style=='underline':desired=(2 if value else -4142) if kind=='excel' else (-1 if value else 0) if kind=='powerpoint' else (1 if value else 0)
    else:desired=bool(value) if kind=='excel' else (-1 if value else 0)
    setattr(font,prop,desired)
    if getattr(font,prop)!=desired:raise RuntimeError('Office did not verify the requested formatting.')

def apply_office(app,kind,command,stop=None):
    if stop and stop.is_set():raise InterruptedError('Stopped')
    action=command['action']
    if kind=='excel' and action.startswith('excel_'):
        from excel_commands import apply
        return apply(app,command,stop)
    if action=='punctuate':
        from punctuation_edit import office_punctuation
        return office_punctuation(app,kind,command.get('target_window'),stop)
    if action=='batch':
        messages=[]
        for step in command['steps']:
            try:messages.append(apply_office(app,kind,step,stop))
            except InterruptedError:raise
            except Exception as exc:
                raise RuntimeError('Completed '+str(len(messages))+' step(s). Next step stopped: '+str(exc)) from exc
        return '\n'.join(messages)
    from office_tools import apply_tool
    native=apply_tool(app,kind,command,stop)
    if native is not None:return native
    if action=='new':
        if kind=='word':app.Documents.Add()
        elif kind=='excel':app.Workbooks.Add()
        else:app.Presentations.Add()
        return 'Created a new '+{'word':'document','excel':'workbook','powerpoint':'presentation'}[kind]+'.'
    if action=='write':
        text=command['text']
        if command.get('range') and kind!='excel':raise ValueError('Cell addresses such as A1 apply to Excel. Select Excel or type at the current cursor.')
        if len(text)>20000:raise ValueError('Split text into chunks under 20,000 characters.')
        if kind=='word':
            if not app.Documents.Count:raise ValueError('Open a document or say new document first.')
            app.Selection.TypeText(text)
        elif kind=='excel':
            if not app.Workbooks.Count:raise ValueError('Open a workbook or say new workbook first.')
            destination=app.ActiveSheet.Range(command['range']) if command.get('range') else app.ActiveCell
            if destination.CountLarge>10000:raise ValueError('Choose a smaller range for text entry.')
            destination.Value=text
        else:
            selection=app.ActiveWindow.Selection
            if selection.Type!=3:raise ValueError('Select a text box and place the caret inside it first.')
            selection.TextRange.Text=text
        return 'Entered text in '+kind+'.'
    if action=='table':
        r,c=command['rows'],command['columns']
        if kind=='word':
            rng=app.Selection.Range.Duplicate;rng.Collapse(0)
            table=app.ActiveDocument.Tables.Add(rng,r,c)
            from office_tools import word_borders
            word_borders(table)
            actual=(table.Rows.Count,table.Columns.Count)
        elif kind=='excel':
            import pythoncom
            active=app.ActiveCell;top,left=int(active.Row),int(active.Column)
            address=f'{column_name(left)}{top}:{column_name(left+c-1)}{top+r-1}'
            source=app.ActiveSheet.Range(address)
            if not command.get('explicit_size'):
                selected=app.Selection
                if selected.CountLarge>1:
                    if selected.Areas.Count!=1 or selected.CountLarge>1000:raise ValueError('Select one range of at most 1,000 cells.')
                    source=selected
            table=app.ActiveSheet.ListObjects.Add(1,source,pythoncom.Missing,1)
            actual=(table.Range.Rows.Count,table.Range.Columns.Count)
        else:
            slide=app.ActiveWindow.View.Slide
            width=app.ActivePresentation.PageSetup.SlideWidth*.8;height=min(r*24,app.ActivePresentation.PageSetup.SlideHeight*.65)
            shape=slide.Shapes.AddTable(r,c,40,100,width,height)
            actual=(shape.Table.Rows.Count,shape.Table.Columns.Count)
        return f'Inserted a table with {actual[0]} rows and {actual[1]} columns in {kind}.'
    if action=='format':
        target=command.get('target','').strip();style=command['style'];value=command['value']
        if target.casefold() in ('it','this','that','selection','selected text','selected cells','the selection','the selected text'):target=''
        if kind=='word' and target:
            doc=app.ActiveDocument;start=0;end=doc.Content.End;count=0
            while start<end and count<1000:
                if stop and stop.is_set():raise InterruptedError('Stopped')
                rng=doc.Range(start,end)
                rng.Find.ClearFormatting()
                if not rng.Find.Execute(target,False,False,False,False,False,True,0,False):break
                _set_font(rng.Font,kind,style,value);count+=1;start=rng.End
            if not count:raise ValueError('The requested text was not found in the active document.')
            return f'Applied {style} to {count} text match(es) in Word.'
        if kind=='excel':
            if target and re.fullmatch(r'[A-Z]{1,3}\d+(?::[A-Z]{1,3}\d+)?',target,re.I):selection=app.ActiveSheet.Range(target)
            elif target:
                used=app.ActiveSheet.UsedRange
                cell=used.Find(What=target,LookIn=-4163,LookAt=2,SearchOrder=1,SearchDirection=1,MatchCase=False,SearchFormat=False)
                if cell is None:raise ValueError('No cell contains that text in the active sheet.')
                first=cell.Address;count=0
                while cell is not None and count<1000:
                    if stop and stop.is_set():raise InterruptedError('Stopped')
                    _set_font(cell.Font,kind,style,value);count+=1
                    cell=used.FindNext(cell)
                    if cell is None or cell.Address==first:break
                return f'Applied {style} to {count} matching cell(s) in Excel.'
            else:selection=app.Selection
            if selection.CountLarge>10000:raise ValueError('Select at most 10,000 cells for formatting.')
            font=selection.Font
        elif kind=='word':font=app.Selection.Font
        else:
            if target:
                slide=app.ActiveWindow.View.Slide;count=0
                for index in range(1,slide.Shapes.Count+1):
                    if stop and stop.is_set():raise InterruptedError('Stopped')
                    shape=slide.Shapes(index)
                    if not shape.HasTextFrame or not shape.TextFrame.HasText:continue
                    text=shape.TextFrame.TextRange
                    for found in re.finditer(re.escape(target),text.Text,re.I):
                        _set_font(text.Characters(found.start()+1,len(target)).Font,kind,style,value);count+=1
                if not count:raise ValueError('The requested text was not found on the active slide.')
                return f'Applied {style} to {count} text match(es) in PowerPoint.'
            font=app.ActiveWindow.Selection.TextRange.Font
        _set_font(font,kind,style,value)
        return 'Applied '+style+' to the selection in '+kind+'.'
    raise ValueError('Unsupported Office operation')

def execute_office(kind,command,context,stop=None):
    import pythoncom,win32com.client
    import windows_api as win
    pythoncom.CoInitialize()
    try:
        if kind=='powerpoint':
            # HWND is a restricted PowerPoint member: typed vtable access is
            # required; late-bound IDispatch reports Member not found.
            import comtypes.client
            app=comtypes.client.GetActiveObject(APPS[kind])
        else:app=win32com.client.GetActiveObject(APPS[kind])
        hwnd=office_hwnd(app,kind)
        import ctypes
        from ctypes import wintypes as w
        pid=w.DWORD();win.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        expected=w.DWORD();win.user.GetWindowThreadProcessId(context['hwnd'],ctypes.byref(expected))
        if not expected.value or pid.value!=expected.value:raise ValueError('The connected Office instance is not the selected app. Select its document and retry.')
        win.user.GetAncestor.argtypes=[w.HWND,w.UINT];win.user.GetAncestor.restype=w.HWND
        if win.user.GetAncestor(hwnd,2)!=win.user.GetAncestor(context['hwnd'],2):raise ValueError('Office is connected to a different document window. Select the intended document and retry.')
        if win.action_window(hwnd)!=hwnd:raise ValueError('Finish the open Office dialog before editing its document.')
        return apply_office(app,kind,command,stop=stop)
    finally:
        app=None;pythoncom.CoUninitialize()

"""Direct cell/range grammar, scoped to Excel by the command router."""
import re
from speech_context import codes,excel_ref


def address(text):
    text=re.sub(r'^(?:the\s+)?(?:cells?|range)\s+|\s+cells?$','',text.strip(),flags=re.I).strip()
    text=re.sub(r'\b([A-Z]{1,3}\d+)\s*(?:to|through|-)\s*([A-Z]{1,3}\d+)\b',r'\1:\2',text,flags=re.I)
    parts=re.split(r'\s*(?::|\bto\b|\bthrough\b|\buntil\b)\s*',text,flags=re.I)
    if len(parts)>2:return None
    result=[]
    for part in parts:
        part=re.sub(r'^(?:the\s+)?cells?\s+|\s+cells?$','',part.strip(),flags=re.I).strip()
        direct=part.replace('$','').upper().replace(' ','')
        if excel_ref(direct):result.append(direct);continue
        found=[value for value in codes(part) if excel_ref(value)]
        if len(found)!=1:return None
        result.append(found[0])
    return ':'.join(result)


def parse(task):
    raw=re.sub(r'^(?:please|can you|could you)\s+','',task.strip(),flags=re.I).rstrip('.!?')
    raw=re.sub(r'\b(?:doubel|doubkle|duble)\b','double',raw,flags=re.I)
    raw=re.sub(r'\b(?:clikc|clik|lcick)\b','click',raw,flags=re.I)
    dictate=False
    suffix=re.search(r'\s+(?:and\s+)?(?:start|enable|turn on)\s+dictation$',raw,re.I)
    if suffix:dictate=True;raw=raw[:suffix.start()]
    m=re.fullmatch(r'(?:select|choose|go to|goto|click)\s+(?:from\s+)?(.+)',raw,re.I)
    if m:
        target=address(m[1])
        if target:return {'action':'excel_select','target':target,'value':''}
    m=re.fullmatch(r'(?:double[ -]?click(?:\s+on)?|edit)\s+(.+)',raw,re.I)
    if m:
        target=address(m[1])
        if target and ':' not in target:return {'action':'excel_edit','target':target,'dictate':dictate}
        if target:return {'action':'ask','message':'Choose one cell to edit, for example edit J7.'}
    if re.fullmatch(r'copy\s+(?:the\s+)?(?:selected\s+cells|selection)',raw,re.I):return {'action':'excel_copy','target':''}
    m=re.fullmatch(r'(?:copy|copy the data (?:in|from)|copy data (?:in|from))\s+(.+)',raw,re.I)
    if m:
        target=address(m[1])
        if target:return {'action':'excel_copy','target':target}
        if re.fullmatch(r'(?:the\s+)?cell\s+\d+',m[1],re.I):
            number=re.search(r'\d+',m[1])[0]
            return {'action':'ask','message':'Which column? Say copy cell A'+number+', for example.'}
    m=re.fullmatch(r'paste(?:\s+(?:the\s+)?(?:copied\s+)?(?:data|text|cells?|stuff|it))?\s+(?:in(?:to)?|to|at|on)\s+(.+)',raw,re.I)
    if m:
        target=address(m[1])
        if target:return {'action':'excel_paste','target':target}
    if re.fullmatch(r'(?:make|create|insert|add)\s+(?:a\s+)?table',raw,re.I):return {'action':'excel_table','target':''}
    if re.fullmatch(r'(?:make|create|insert|convert|format)(?:\s+(?:a|the|these))?\s+(?:selected\s+cells?\s+(?:in)?to\s+(?:a\s+)?table|table\s+(?:of|from|using|with)\s+(?:the\s+)?selected\s+(?:cells?|range)|table\s+from\s+(?:the\s+)?selection)',raw,re.I):
        return {'action':'excel_table','target':''}
    if re.fullmatch(r'(?:format|convert)\s+(?:as|into|to)\s+(?:a\s+)?table',raw,re.I):return {'action':'excel_table','target':''}
    m=re.fullmatch(r'(?:make|create|convert|format)\s+(.+?)\s+(?:into|to|as)\s+(?:a\s+)?table',raw,re.I)
    if m:
        target=address(m[1])
        if target:return {'action':'excel_table','target':target}
        if m[1].casefold() in ('selected cells','the selected cells','selection','the selection'):
            return {'action':'excel_table','target':''}
    m=re.fullmatch(r'(?:open|expand|show)\s+(?:the\s+)?(?:cell\s+dropdown(?:\s+(?:in|for|at)\s+(.+))?|dropdown\s+(?:in|for|at)\s+(.+))',raw,re.I)
    if m:
        value=m[1] or m[2];target=address(value) if value else ''
        if target is not None:return {'action':'excel_dropdown','target':target}
    return None


def cell_range(app,target):
    if not app.Workbooks.Count:raise ValueError('Open a workbook first.')
    result=app.ActiveSheet.Range(target) if target else app.Selection
    if result.Areas.Count!=1 or result.CountLarge>10000:raise ValueError('Choose a single range of at most 10,000 cells.')
    return result


def apply(app,command,stop=None):
    from office_tools import check_stop
    check_stop(stop);action=command['action'];target=command.get('target','')
    cell=cell_range(app,target)
    if action=='excel_select':
        app.Goto(cell,True)
        return 'Selected Excel '+target+'.'
    if action=='excel_dropdown_info':
        if cell.CountLarge!=1:return None
        try:valid=cell.Validation.Type==3 and bool(cell.Validation.InCellDropdown)
        except Exception:valid=False
        return {'cell':str(cell.Address).replace('$','')} if valid else None
    if action=='excel_table':
        if cell.Rows.Count<2:raise ValueError('Select at least two rows for an Excel table, including its header.')
        if cell.ListObject is not None:raise ValueError('The selected cells already belong to a table.')
        import pythoncom
        # Let Excel detect headers instead of silently treating data as a header.
        table=app.ActiveSheet.ListObjects.Add(1,cell,pythoncom.Missing,0)
        table.TableStyle='TableStyleMedium2'
        return 'Created an Excel table from '+(target or 'the selected cells')+'.'
    if action=='excel_copy':
        cell.Copy()
        return 'Copied Excel '+(target or 'selection')+' (including its cell formatting and formulas).'
    app.Goto(cell,True);check_stop(stop)
    if action=='excel_paste':
        # Excel handles its rich cell clipboard and external text/TSV itself.
        app.ActiveSheet.Paste()
        return 'Pasted clipboard data into Excel '+target+'.'
    if action in ('excel_edit','excel_dropdown'):
        if cell.CountLarge!=1:raise ValueError('Choose one cell for editing or its dropdown.')
        if action=='excel_dropdown':
            try:valid=cell.Validation.Type==3 and bool(cell.Validation.InCellDropdown)
            except Exception:valid=False
            if not valid:raise ValueError('This cell does not have a list-validation dropdown.')
        import windows_api as win
        from office_control import office_hwnd
        hwnd=office_hwnd(app,'excel')
        if win.foreground()!=hwnd:raise ValueError('Excel focus changed before cell input.')
        import desktop_control
        desktop_control.act({'action':'press','key':'f2'} if action=='excel_edit' else {'action':'hotkey','keys':['alt','down']})
        return 'Editing Excel cell '+target+'.' if action=='excel_edit' else 'Opened the selected Excel cell dropdown.'
    raise ValueError('Unknown Excel cell command.')

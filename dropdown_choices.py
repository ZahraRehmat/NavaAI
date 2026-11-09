"""Offer observed dropdown controls with on-screen speech-friendly marks."""
from dropdown_control import grid_dropdown_name


def candidates(controls):
    combos={grid_dropdown_name(row.get('source_name') or row['name']) for row in controls if row['type']=='ComboBox'}
    result=[];seen=set()
    for row in controls:
        if row['type']!='ComboBox' and not row.get('expandable'):continue
        name=row.get('source_name') or row['name'];canonical=grid_dropdown_name(name)
        if canonical and row['type']!='ComboBox' and canonical in combos:continue
        identity=(name.casefold(),row['type'],tuple(row.get('bounds') or ()))
        if identity in seen:continue
        seen.add(identity)
        result.append(dict(row,label=canonical or name or row.get('automation_id') or 'Dropdown',
                           dropdown_choice=True,selection_role='dropdown',selection_phrase='dropdown to open'))
    return sorted(result,key=lambda row:(0 if row['label']=='Font selection dropdown' else 1 if row['label']=='Font size dropdown' else 2,row['label'].casefold()))


def choose(agent):
    if not agent.choose:return 'Which dropdown? Say open Font selection dropdown, open Font size dropdown, or name the menu.'
    from accessibility import NativeControls
    import windows_api as win
    from office_control import office_kind,execute_office
    if not agent.interaction:agent.interaction=win.snapshot()
    agent._focus_native();target=dict(agent.interaction or win.snapshot() or {})
    if not target:raise ValueError('Select the app containing the dropdown first.')
    probe=NativeControls();rows=candidates(probe.observe(hwnd=target['hwnd'],depth=24,limit=1200))
    if office_kind(target)=='excel':
        try:info=execute_office('excel',{'action':'excel_dropdown_info','target':''},target,stop=agent.stop)
        except Exception:info=None
        if info:rows.append({'label':'Cell '+info['cell']+' dropdown','cell':info['cell'],
                            'dropdown_choice':True,'selection_role':'dropdown','selection_phrase':'dropdown to open'})
    if not rows:return 'No accessible dropdowns are visible. Open the ribbon tab or select a cell with a dropdown first.'
    selected=agent.choose_targets('Which dropdown should open?',rows)
    if selected is None or agent.stop.is_set():raise InterruptedError('Dropdown selection cancelled.')
    if not isinstance(selected,int) or not 0<=selected<len(rows):raise ValueError('Invalid dropdown choice.')
    row=rows[selected]
    if not win.target_alive(target):raise ValueError('The app closed while choosing a dropdown.')
    if row.get('cell'):
        win.focus_handle(target['hwnd'],target['title'])
        return execute_office('excel',{'action':'excel_dropdown','target':row['cell']},target,stop=agent.stop)
    result=probe.act({'action':'ui_click','id':row['id'],'expected_name':row.get('source_name',row['name']),'expand':True})
    return 'Opened '+row['label']+'. '+(result or '')

"""Bounded visible accessibility branch traversal; platform-neutral target decoding."""
import json,time

ROLES={'ComboBox', 'SplitButton', 'ListItem', 'HeaderItem', 'Document', 'Hyperlink', 'RadioButton', 'DataItem', 'ScrollBar', 'Slider', 'TreeItem', 'Button', 'CheckBox', 'Spinner', 'Edit', 'Thumb', 'TabItem', 'MenuItem'}

def decode_target(el,hwnd,pid,scope,bounds,uia):
    role=uia.known_control_type_ids.get(el.CachedControlType,'Custom')
    # Embedded WebView hosts can be disabled or have empty rectangles while
    # their accessible descendants are enabled and visible.
    host_role=role if role in ('Pane','Group','Custom','Document','Window') else None
    if el.CachedIsOffscreen:return None,host_role
    if not el.CachedIsEnabled:return None,host_role
    box=el.CachedBoundingRectangle
    l,t,r,b=max(box.left,bounds[0]),max(box.top,bounds[1]),min(box.right,bounds[2]),min(box.bottom,bounds[3])
    if r-l<3 or b-t<3:return None,host_role
    if role not in ROLES:
        if role not in ('Pane','Custom','Group','Image','Text'):return None,role
        if not any(el.GetCachedPropertyValue(p) for p in (30031,30034,30043)):return None,role
    name=el.CachedName or '';runtime=tuple(el.GetCachedPropertyValue(30000) or ())
    if role=='MenuItem' and name=='System' and t<bounds[1]+80:runtime=('title-system-menu',)
    key=json.dumps((pid,hwnd,runtime or (el.CachedAutomationId,role,name,l,t),role,name))
    row={'key':key,'name':name or role,'type':role,'bounds':(l,t,r,b),'hwnd':hwnd,'scope':scope}
    if role=='ComboBox':
        from dropdown_control import grid_dropdown_name
        specific_name=grid_dropdown_name(name)
        if specific_name:
            row['name']=specific_name;row['source_name']=name;row['dropdown_name']=specific_name
    try:row['expandable']=bool(el.GetCachedPropertyValue(30028)) and el.GetCachedPropertyValue(30070)!=3
    except Exception:row['expandable']=role in ('SplitButton','ComboBox')
    if scope=='taskbar':row['taskbar_bounds']=tuple(bounds)
    return row,role


def item_text_point(element,row,uia,request):
    """Use Explorer's filename text, avoiding row checkboxes and action icons."""
    try:
        children=element.FindAllBuildCache(2,uia.true_condition,request)
        for index in range(min(40,children.Length)):
            child=children.GetElement(index)
            if child.CachedIsOffscreen:continue
            role=uia.known_control_type_ids.get(child.CachedControlType,'')
            if role!='Text':continue
            if child.CachedAutomationId!='DisplayNameTextBlock' and child.CachedName!=row['name']:continue
            box=child.CachedBoundingRectangle;l,t,r,b=row['bounds']
            l,t,r,b=max(l,box.left),max(t,box.top),min(r,box.right),min(b,box.bottom)
            if r>l and b>t:return ((l+r-1)//2,(t+b-1)//2)
    except Exception:pass
    return None


def scan_visible_branches(root,hwnd,pid,scope,bounds,uia,request,budget,file_rows=False,excel_sheet=False,diagnostics=None):
    from collections import deque
    containers={'Pane','Group','Custom','Document','Window','List','Tree','Tab',
                'ToolBar','AppBar','SemanticZoom','TabItem','ComboBox','Menu','MenuBar','DataGrid','Table','SplitButton','Header','TitleBar','StatusBar'}
    pending=deque([(root,0)]);rows=[];seen=set();count=0;start=time.monotonic()
    stats=diagnostics if diagnostics is not None else {}
    stats.update(visited=0,property_errors=0,branch_errors=0)
    while pending and count<2500 and len(rows)<600 and time.monotonic()-start<budget:
        parent,depth=pending.popleft()
        if depth>=18:continue
        try:children=parent.FindAllBuildCache(2,uia.true_condition,request)
        except Exception as exc:
            stats['branch_errors']+=1;stats['last_error']=(str(exc).strip() or type(exc).__name__)[:160];continue
        for index in range(min(children.Length,2500-count)):
            count+=1
            try:
                el=children.GetElement(index)
                try:role=uia.known_control_type_ids.get(el.CachedControlType,'Custom')
                except Exception:role='Custom'
                if excel_sheet:
                    try:sheet_class=el.CachedClassName
                    except Exception:sheet_class=''
                    if sheet_class in ('XLSpreadsheetGrid','XLSpreadsheetCell','XLGridRowHeader','XLGridColumnHeader','XLSelectAllHeader'):
                        continue  # Excel addresses are the worksheet's own grid.
                try:row,role=decode_target(el,hwnd,pid,scope,bounds,uia)
                except Exception as exc:
                    # UIA providers differ across Windows/app versions. A failed
                    # cached property must not hide a container's valid children.
                    row=None;stats['property_errors']+=1
                    stats['last_error']=(str(exc).strip() or type(exc).__name__)[:160]
                if row and row['key'] not in seen:
                    try:
                        from dropdown_control import arrow_name
                        parent_role=uia.known_control_type_ids.get(parent.CachedControlType,'')
                        row['name']=arrow_name(row['name'],parent.CachedName,parent_role)
                        if parent_role in ('ComboBox','SplitButton') and role in ('Edit','Text','Button','MenuItem'):
                            row['expandable']=True;row['dropdown_owner']=parent.CachedName
                    except Exception:pass
                    if file_rows and role in ('ListItem','DataItem'):
                        point=item_text_point(el,row,uia,request)
                        if point:row['point']=point
                    rows.append(row);seen.add(row['key'])
                # Text and atomic item/button descendants do not need a walk.
                # Host wrappers remain traversable even when they report a
                # disabled/offscreen state for enabled visible descendants.
                if role in containers:pending.append((el,depth+1))
            except Exception:continue
    stats['visited']=count;stats['targets']=len(rows);stats['pending_branches']=len(pending)
    return rows

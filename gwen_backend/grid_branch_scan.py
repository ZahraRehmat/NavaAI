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
    return {'key':key,'name':name or role,'type':role,'bounds':(l,t,r,b),'hwnd':hwnd,'scope':scope},role


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


def scan_visible_branches(root,hwnd,pid,scope,bounds,uia,request,budget,file_rows=False):
    from collections import deque
    containers={'Pane','Group','Custom','Document','Window','List','Tree','Tab',
                'ToolBar','AppBar','SemanticZoom','TabItem','Menu','MenuBar','DataGrid','Table','SplitButton','Header','TitleBar','StatusBar'}
    pending=deque([(root,0)]);rows=[];seen=set();count=0;start=time.monotonic()
    while pending and count<2500 and len(rows)<600 and time.monotonic()-start<budget:
        parent,depth=pending.popleft()
        if depth>=18:continue
        try:children=parent.FindAllBuildCache(2,uia.true_condition,request)
        except Exception:continue
        for index in range(min(children.Length,2500-count)):
            count+=1
            try:
                el=children.GetElement(index);row,role=decode_target(el,hwnd,pid,scope,bounds,uia)
                if row and row['key'] not in seen:
                    if file_rows and role in ('ListItem','DataItem'):
                        point=item_text_point(el,row,uia,request)
                        if point:row['point']=point
                    rows.append(row);seen.add(row['key'])
                # Text and atomic item/button descendants do not need a walk.
                # Host wrappers remain traversable even when they report a
                # disabled/offscreen state for enabled visible descendants.
                if role in containers:pending.append((el,depth+1))
            except Exception:continue
    return rows

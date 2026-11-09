"""Find virtual popup providers omitted by HWND-to-UIA resolution."""
import time
from grid_branch_scan import scan_visible_branches


def inside(box,outer,tolerance=2):
    return box[0]>=outer[0]-tolerance and box[1]>=outer[1]-tolerance and box[2]<=outer[2]+tolerance and box[3]<=outer[3]+tolerance


def rect(element):
    b=element.CurrentBoundingRectangle
    return b.left,b.top,b.right,b.bottom


def popup_provider(element,pid,bounds,walker):
    """Climb from a hit-tested child, staying inside the popup and process."""
    chosen=None
    for _ in range(14):
        if not element:break
        try:
            box=rect(element)
            if element.CurrentProcessId!=pid or element.CurrentIsOffscreen:break
            if min(box[2],bounds[2])<=max(box[0],bounds[0]) or min(box[3],bounds[3])<=max(box[1],bounds[1]):break
            # Virtualized lists can report thousands of offscreen pixels.
            # Walk through that host to its correctly bounded popup ancestor.
            if inside(box,bounds):chosen=element
            element=walker.GetParentElement(element)
        except Exception:break
    return chosen


def scan_popup(hwnd,pid,scope,bounds,uia,request,budget=.8,hit_test=None):
    if hit_test is None:
        from pywinauto.uia_element_info import UIAElementInfo
        hit_test=lambda x,y:UIAElementInfo.from_point(x,y).element
    l,t,r,b=bounds;deadline=time.monotonic()+budget;seen=set();rows=[]
    # A small set of semantic probes finds a provider root; its actual tree
    # supplies all labels and rectangles. No synthetic screen cells are added.
    for fx,fy in ((.5,.5),(.25,.25),(.75,.25),(.25,.75),(.75,.75)):
        if time.monotonic()>=deadline:break
        try:
            el=popup_provider(hit_test(int(l+(r-l)*fx),int(t+(b-t)*fy)),pid,bounds,uia.iuia.RawViewWalker)
            if el is None:continue
            identity=tuple(el.GetRuntimeId())
            if identity in seen:continue
            seen.add(identity)
            found=scan_visible_branches(el,hwnd,pid,scope,bounds,uia,request,max(.05,deadline-time.monotonic()))
            # Decode the seed itself too when it is an atomic control/provider.
            from grid_branch_scan import decode_target
            row,_=decode_target(el.BuildUpdatedCache(request),hwnd,pid,scope,bounds,uia)
            if row:found.append(row)
            rows.extend(found)
            if found:break
        except Exception:continue
    return list({row['key']:row for row in rows}.values())

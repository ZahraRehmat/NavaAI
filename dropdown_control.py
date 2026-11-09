"""Open observed dropdowns through ExpandCollapse, never by invoking the main action."""
import re,time


def missing_target(text):
    return bool(re.fullmatch(r'(?:please\s+)?(?:open|expand|show|click|press)(?:\s+on)?\s+(?:the\s+)?drop[ -]?down(?:\s+(?:menu|arrow))?[.!]?',text.strip(),re.I))


def normalize_target(name):
    aliases={'font selection':'Font','font selector':'Font','font selecting':'Font','font list':'Font','font names':'Font','font name':'Font','font family':'Font','text size':'Font Size','font size selector':'Font Size'}
    return aliases.get(name.casefold(),name)


def grid_dropdown_name(name):
    clean=re.sub(r'\s+',' ',name.strip().replace('&','').rstrip(':')).casefold()
    clean={'fontname':'font','font name':'font','font family':'font','fontsize':'font size'}.get(clean,clean)
    if clean in ('font','font selection','font selector','font selection dropdown','font dropdown'):return 'Font selection dropdown'
    if clean in ('font size','text size','font size dropdown','text size dropdown'):return 'Font size dropdown'
    return None


def dropdown_intent(text):
    text=text.strip().rstrip('.!')
    bare=re.fullmatch(r'(font(?:\s+(?:selection|selector|size))?|text\s+size)\s+drop[ -]?down',text,re.I)
    if bare:return normalize_target(bare[1])
    if re.search(r'\bthen\b|;|\s+and\s+(?=(?:click|press|select|open|move|hold|release|scroll)\b)',text,re.I):return None
    patterns=[
        r'(?:open|expand|show|click|press)(?:\s+on)?\s+(?:the\s+)?(?:drop[ -]?down(?:\s+menu)?|menu\s+arrow)(?:\s+(?:for|of|on))?\s+(.+)',
        r'(?:open|expand|show|click|press)(?:\s+on)?\s+(?:the\s+)?(.+?)\s+(?:drop[ -]?down(?:\s+(?:menu|arrow))?|menu\s+arrow)',
        r'(?:drop[ -]?down|expand)\s+(.+)']
    for pattern in patterns:
        match=re.fullmatch(pattern,text,re.I)
        if match:return normalize_target(match[1].strip())
    return None


def arrow_name(name,parent_name,parent_role):
    if parent_role in ('SplitButton','ComboBox') and name.casefold() in ('more options','open','drop down','dropdown','expand'):
        if parent_role=='ComboBox' and grid_dropdown_name(parent_name):return grid_dropdown_name(parent_name)+' arrow'
        return parent_name+' dropdown'
    return name


def expandable(wrapper):
    try:return wrapper.iface_expand_collapse.CurrentExpandCollapseState!=3
    except Exception:return False


def owning_dropdown(wrapper):
    """An edit/arrow label inside a combo is not itself the dropdown provider."""
    current=wrapper
    for _ in range(4):
        try:
            role=current.element_info.control_type
            if role in ('ComboBox','SplitButton'):return current
            if role not in ('Edit','Text','Button','MenuItem','Pane','Custom'):return None
            parent=current.parent()
            if parent is None:return None
            # Do not wander out through ribbon groups into unrelated controls.
            if parent.element_info.control_type not in ('ComboBox','SplitButton','Pane','Custom'):return None
            current=parent
        except Exception:return None
    return None


def expand_wrapper(wrapper,timeout=.7):
    owner=owning_dropdown(wrapper)
    if owner is not None and owner is not wrapper:return expand_wrapper(owner,timeout)
    try:pattern=wrapper.iface_expand_collapse
    except Exception:pattern=None
    if pattern is not None:
        state=pattern.CurrentExpandCollapseState
        if state==3:raise ValueError('That control has no expandable menu.')
        if state!=1:pattern.Expand()
        deadline=time.monotonic()+timeout
        while pattern.CurrentExpandCollapseState!=1:
            if time.monotonic()>=deadline:raise ValueError('Windows did not confirm that the dropdown opened. No main-button action was invoked.')
            time.sleep(.03)
        return 'Dropdown open.'
    # Some providers expose only a real arrow child. Its observed control is
    # used directly; there is no guessed right/bottom edge of the main button.
    for child in wrapper.children()[:40]:
        if not child.is_visible() or not child.is_enabled():continue
        if child.element_info.name.casefold() not in ('more options','open','drop down','dropdown','expand'):continue
        if expandable(child):return expand_wrapper(child,timeout)
        try:invoke=child.iface_invoke
        except Exception:invoke=None
        if invoke is not None:invoke.Invoke()
        else:child.click_input()
        return 'Requested the dropdown through its observed arrow.'
    raise ValueError('No expandable pattern or separate dropdown arrow is exposed by this control.')


def expand_observed(cell):
    import json
    import windows_api as win
    from pywinauto.uia_defines import IUIA
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_element_info import UIAElementInfo
    pid,hwnd,runtime,role,name=json.loads(cell['key'])
    if hwnd!=cell['hwnd'] or not runtime:raise ValueError('The dropdown has no stable observed identity.')
    if win.focus_handle(hwnd,'dropdown target')!=hwnd:raise ValueError('The target dialog changed. Refresh before opening the dropdown.')
    uia=IUIA().iuia
    el=UIAElementInfo.from_point(*cell['point']).element
    for _ in range(12):
        if not el:break
        if el.CurrentProcessId==pid and tuple(el.GetRuntimeId())==tuple(runtime):
            if el.CurrentName!=name or el.CurrentIsOffscreen or not el.CurrentIsEnabled:break
            if win.foreground()!=hwnd:raise ValueError('The active app changed before dropdown expansion.')
            return expand_wrapper(UIAWrapper(UIAElementInfo(el)))
        el=uia.ControlViewWalker.GetParentElement(el)
    raise ValueError('The observed dropdown moved or changed. Refresh the grid and retry.')


def expand_cell(cell,stop=None):
    """Keep the UIA action in its own process, bounded and cancellable."""
    import json,subprocess,sys
    from pathlib import Path
    executable=Path(sys.executable).with_name('python.exe')
    process=subprocess.Popen([str(executable),str(Path(__file__))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        process.stdin.write(json.dumps(cell)+'\n');process.stdin.flush();deadline=time.monotonic()+4
        while process.poll() is None:
            if stop and stop.is_set():raise InterruptedError('Stopped before dropdown expansion completed')
            if time.monotonic()>=deadline:raise ValueError('The dropdown provider timed out. No repeated click was attempted.')
            time.sleep(.03)
        answer=json.loads(process.stdout.read())
        if answer.get('error'):raise ValueError(answer['error'])
        return answer['result']
    finally:
        if process.poll() is None:process.kill()
        process.communicate()


if __name__=='__main__':
    import sys,json
    from grid_display import enable_dpi_awareness
    enable_dpi_awareness()
    try:
        cell=json.loads(sys.stdin.readline());answer={'result':expand_observed(cell)}
    except Exception as exc:answer={'error':str(exc).strip() or type(exc).__name__}
    print(json.dumps(answer),flush=True)

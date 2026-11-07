"""Bound Windows accessibility elements to a single current observation."""
import ctypes
from catalog import norm

def named_control_id(controls,label):
    from label_matching import choose_label,NoLabelMatch,AmbiguousLabel,dialog_action,normalize_label
    if dialog_action(label):
        controls=[c for c in controls if c.get('type')=='Button' and normalize_label(c['name'])==normalize_label(label)]
    try:return choose_label(controls,label,merge_overlaps=True)['row']['id']
    except NoLabelMatch:raise ValueError('Could not find '+label+' among the visible controls. Nothing was clicked.')
    except AmbiguousLabel as exc:raise ValueError(str(exc)+'. Please give a more specific name. Nothing was clicked.')

class NativeControls:
    def __init__(self): self.controls={}; self.hwnd=None; self.target=None

    def focus_app(self,name):
        if not name: return
        from windows_api import focus
        return focus(name)

    def observe(self,hwnd=None,depth=12,limit=200):
        from pywinauto import Desktop
        from windows_api import stable_foreground,action_window,rect
        self.hwnd=action_window(hwnd or stable_foreground())
        self.bounds=rect(self.hwnd)
        window=Desktop(backend='uia').window(handle=self.hwnd).wrapper_object()
        if window.window_text().startswith('Gwen Doer'):
            raise ValueError('Gwen is still in the foreground. Select the target app first. Nothing was clicked.')
        self.target=window; self.controls={}; result=[]
        for el in window.iter_descendants(depth=depth):
            if len(result)>=limit: break
            try:
                info=el.element_info
                if info.control_type not in ('Button','Edit','ComboBox','Hyperlink','CheckBox','RadioButton','TabItem','ListItem','MenuItem','Group','Text','Image'): continue
                if not el.is_visible() or not el.is_enabled(): continue
                rect=info.rectangle
                if rect.width()<=0 or rect.height()<=0 or (not info.name and info.control_type in ('Group','Text','Image')): continue
                left,top,right,bottom=self.bounds
                if rect.right<=left or rect.left>=right or rect.bottom<=top or rect.top>=bottom:continue
                index=len(result); self.controls[index]=el
                result.append({'id':index,'name':info.name,'type':info.control_type,'focused':el.has_keyboard_focus(),'automation_id':info.automation_id,'bounds':[rect.left,rect.top,rect.right,rect.bottom]})
            except Exception: continue
        return result

    def act(self,a):
        from windows_api import focus_handle,rect
        focused=focus_handle(self.hwnd,'observed control window')
        if focused!=self.hwnd or rect(self.hwnd)!=self.bounds:
            raise ObservationChanged('The target dialog or its position changed; observe again before input')
        el=self.controls.get(a['id'])
        if el is None: raise ValueError('Unknown accessibility element ID')
        if not el.is_visible() or not el.is_enabled():raise ObservationChanged('The observed control is no longer available')
        if a.get('expected_name') is not None and el.element_info.name!=a['expected_name']:raise ObservationChanged('The chosen control label changed; observe again before input')
        if a['action']=='ui_fill':
            el.set_edit_text(a['text'])
            if el.get_value()!=a['text']: raise ValueError('Text entry verification failed')
        else:
            # Prefer semantic invocation; fallback targets the observed control rectangle.
            try:pattern=el.iface_invoke
            except Exception:pattern=None
            if pattern is None:el.click_input()
            else:pattern.Invoke()
        return 'Accessibility action completed'

class ObservationChanged(ValueError):pass

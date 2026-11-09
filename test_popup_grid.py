import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from grid_popup_scan import popup_provider,scan_popup
from test_grid_branches import Element


class Provider(Element):
    def __init__(self,*args,parent=None,**kwargs):
        super().__init__(*args,**kwargs);self.parent=parent;self.CurrentProcessId=7;self.CurrentIsOffscreen=self.CachedIsOffscreen
        self.CurrentBoundingRectangle=self.CachedBoundingRectangle
        for child in self.children:child.parent=self
    def GetRuntimeId(self):return [7,id(self)]
    def BuildUpdatedCache(self,request):return self


class PopupGridTests(unittest.TestCase):
    def provider(self):
        leaf=Provider(3,'Aptos',box=(10,30,190,60))
        host=Provider(2,'All Fonts',children=[leaf,Provider(3,'Hidden font',offscreen=True)],box=(0,20,200,20000))
        menu=Provider(1,'Font',children=[host],box=(0,0,200,200))
        menu.parent=Provider(4,'Font combo',box=(0,-30,100,0))
        walker=SimpleNamespace(GetParentElement=lambda el:el.parent)
        uia=SimpleNamespace(known_control_type_ids={1:'Menu',2:'Group',3:'ListItem',4:'ComboBox'},true_condition=True,iuia=SimpleNamespace(RawViewWalker=walker))
        return leaf,menu,uia

    def test_hit_testing_recovers_menu_through_oversized_virtual_list(self):
        leaf,menu,uia=self.provider()
        self.assertIs(popup_provider(leaf,7,(0,0,200,200),uia.iuia.RawViewWalker),menu)
        rows=scan_popup(10,7,'app',(0,0,200,200),uia,None,hit_test=lambda x,y:leaf)
        self.assertEqual([r['name'] for r in rows],['Aptos'])
        self.assertEqual(rows[0]['hwnd'],10);self.assertEqual(rows[0]['bounds'],(10,30,190,60))

    def test_probe_does_not_adopt_another_process(self):
        leaf,menu,uia=self.provider();leaf.CurrentProcessId=99
        self.assertEqual(scan_popup(10,7,'app',(0,0,200,200),uia,None,hit_test=lambda x,y:leaf),[])

    def test_menu_descendants_under_combobox_are_walked(self):
        from grid_branch_scan import scan_visible_branches
        leaf,menu,uia=self.provider()
        root=Provider(2,children=[Provider(4,'Font',children=[menu])])
        rows=scan_visible_branches(root,10,7,'app',(0,0,200,200),uia,None,1)
        self.assertIn('Aptos',[r['name'] for r in rows])

    def test_missing_helper_falls_back_without_launch(self):
        from uiaccess_overlay import UiAccessOverlay
        with tempfile.TemporaryDirectory() as folder:
            renderer=UiAccessOverlay(folder)
            with patch('win32api.ShellExecute') as launch:
                self.assertFalse(renderer.draw({},[]));launch.assert_not_called()

    def test_installed_helper_must_match_install_record(self):
        import hashlib
        from uiaccess_overlay import UiAccessOverlay
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'GwenOverlay.exe').write_bytes(b'test fixture')
            (path/'install.json').write_text(json.dumps({'exe_sha256':hashlib.sha256(b'test fixture').hexdigest()}))
            renderer=UiAccessOverlay(folder);self.assertTrue(renderer.installed())
            (path/'GwenOverlay.exe').write_bytes(b'changed');self.assertFalse(renderer.installed())

    def test_canvas_serialization_carries_drawing_only(self):
        from uiaccess_overlay import canvas_frame
        canvas=Mock();canvas.find_all.return_value=[1,2];canvas.type.side_effect=lambda i:'rectangle' if i==1 else 'text'
        canvas.coords.side_effect=lambda i:[10,10,50,30] if i==1 else [12,12]
        values={1:{'fill':'black','outline':'cyan','width':'1'},2:{'fill':'yellow','text':'AF','anchor':'nw'}}
        canvas.itemcget.side_effect=lambda i,k:values[i][k]
        frame=canvas_frame({'areas':[{'bounds':(-100,0,400,300)}],'config':{'font_size':9}},[canvas])
        self.assertEqual(frame['areas'][0]['commands'][1]['text'],'AF')
        self.assertEqual(set(frame),{'active','areas'})

    def test_helper_token_handshake_is_required_before_using_shell_layer(self):
        from uiaccess_overlay import UiAccessOverlay
        for greeting,expected in ((b'READY UIACCESS=1\n',True),(b'READY UIACCESS=0\n',False)):
            renderer=UiAccessOverlay();handle=Mock()
            with patch.object(renderer,'installed',return_value=True),patch('win32api.ShellExecute',return_value=42),patch('win32file.CreateFile',return_value=handle) as create,patch('win32pipe.SetNamedPipeHandleState'),patch('win32pipe.PeekNamedPipe',return_value=(b'',len(greeting),0)),patch('win32file.ReadFile',return_value=(0,greeting)),patch('win32file.WriteFile',side_effect=lambda h,p:(0,len(p))):
                self.assertEqual(renderer.draw({'areas':[],'config':{'font_size':9}},[]),expected)
                self.assertTrue(create.call_args.args[0].startswith('\\\\.\\pipe\\GwenOverlay-'))
                self.assertEqual(renderer.verified,expected)
            renderer.close()

    def test_reused_overlay_moves_above_new_popup_without_activation(self):
        import tkinter as tk,ctypes
        from ctypes import wintypes as w
        import windows_api as win
        from grid_overlay import GridOverlay
        root=tk.Tk();root.withdraw();root.update_idletasks();overlay=GridOverlay(root)
        popup=None
        snapshot={'active':True,'mode':'smart','config':{'line_color':'cyan','label_color':'yellow','label_background':'black','font_size':9},'areas':[{'monitor':1,'bounds':(0,0,400,300),'cells':[]}]}
        try:
            overlay.draw(snapshot);popup=tk.Toplevel(root);popup.withdraw();popup.overrideredirect(True);popup.update_idletasks()
            win.user.GetParent.argtypes=[w.HWND];win.user.GetParent.restype=w.HWND
            ph=win.user.GetParent(popup.winfo_id()) or popup.winfo_id()
            oh=win.user.GetParent(overlay.windows[0].winfo_id()) or overlay.windows[0].winfo_id()
            win.user.ShowWindow(ph,4)
            win.user.SetWindowPos(ph,w.HWND(-1),0,0,100,100,0x10|0x40)
            overlay.draw(snapshot);order=[]
            @win.ENUM
            def visit(h,_):order.append(int(h));return True
            win.user.EnumWindows(visit,0)
            self.assertLess(order.index(oh),order.index(ph))
        finally:
            overlay.close()
            if popup is not None:popup.destroy()
            root.destroy()


if __name__=='__main__':unittest.main()

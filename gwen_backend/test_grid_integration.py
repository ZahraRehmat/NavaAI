import unittest
from types import SimpleNamespace
from full_grid import FullGrid
from smart_grid import SmartMap,AdaptiveGrid
from test_full_grid import FakeMouse
from test_grid_branches import Element
from test_smart_grid import row
from grid_roots import merge_roots,interactive_shell
from grid_branch_scan import scan_visible_branches
from direct_commands import parse_direct


class GridIntegrationTests(unittest.TestCase):
    def test_keyboard_passes_through_both_grids_without_disabling(self):
        for mode in ('smart','full'):
            grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[row()])
            try:
                grid.run('gwen grid' if mode=='smart' else 'gwen full grid')
                for text in ('type hello','write hello','select all','copy','paste','press enter','press ctrl a','go back','go forward','go home','go up'):
                    before=list(grid.mouse.events)
                    self.assertIsNone(grid.run(text),text)
                    self.assertTrue(grid.active);self.assertEqual(grid.mouse.events,before)
                self.assertIsNotNone(grid.run('press A' if mode=='smart' else 'press A1'))
                self.assertEqual(grid.mouse.events[-1][0],'click')
            finally:grid.close()

    def test_native_popup_not_lost_when_uia_omits_it(self):
        native=[{'hwnd':10,'kind':'#32768'},{'hwnd':20,'kind':'CabinetWClass'}]
        accessible=[{'hwnd':30,'kind':'Windows.UI.Core.CoreWindow'},{'hwnd':20}]
        self.assertEqual([r['hwnd'] for r in merge_roots(native,accessible)],[30,10,20])
        for kind in ('NotifyIconOverflowWindow','TopLevelWindowForOverflowXamlIsland','Microsoft.UI.Content.PopupWindowSiteBridge'):
            self.assertTrue(interactive_shell(kind))
        self.assertFalse(interactive_shell('GwenOverlay'))

    def test_appbar_and_tab_controls_traversed(self):
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'Button',5:'AppBar',6:'TabItem'},true_condition=True)
        root=Element(1,children=[Element(5,children=[Element(2,'Back'),Element(2,'Forward')]),
                                  Element(6,children=[Element(2,'Close Tab')])])
        rows=scan_visible_branches(root,100,200,'app',(0,0,800,600),uia,None,1.4)
        self.assertTrue({'Back','Forward','Close Tab'}<=set(r['name'] for r in rows))

    def test_start_semantic_zoom_contains_pinned_apps(self):
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'Button',5:'SemanticZoom',6:'ListItem'},true_condition=True)
        root=Element(1,children=[Element(5,children=[Element(6,'Notepad'),Element(6,'Word')])])
        rows=scan_visible_branches(root,100,200,'app',(0,0,800,600),uia,None,1.4)
        self.assertEqual([r['name'] for r in rows],['Notepad','Word'])

    def test_filename_target_avoids_checkbox_and_row_whitespace(self):
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'Button',3:'ListItem',4:'Text'},true_condition=True)
        name=Element(4,'report.pdf',box=(120,15,240,35));name.CachedAutomationId='DisplayNameTextBlock'
        item=Element(3,'report.pdf',box=(10,10,700,60),children=[Element(2,'Select',box=(10,10,40,40)),name])
        rows=scan_visible_branches(Element(1,children=[item]),100,200,'app',(0,0,800,600),uia,None,1.4,file_rows=True)
        grid=SmartMap([(0,0,800,600)]);grid.update(rows)
        point=grid.cell('A')['point']
        self.assertTrue(120<=point[0]<240 and 15<=point[1]<35)
        self.assertEqual(len(rows),1)
        # If the caption has moved off the clipped display, use a visible point.
        grid.update([dict(rows[0],point=(9999,9999))]);self.assertLess(grid.cell('A')['point'][0],800)

    def test_direct_navigation_is_keyboard_only(self):
        self.assertEqual(parse_direct('back')['keys'],['alt','left'])
        self.assertEqual(parse_direct('go forward')['keys'],['alt','right'])
        self.assertEqual(parse_direct('go home')['keys'],['alt','home'])


if __name__=='__main__':unittest.main()

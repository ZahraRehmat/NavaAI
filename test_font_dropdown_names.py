import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from grid_branch_scan import scan_visible_branches
from test_grid_branches import Element
from smart_grid import AdaptiveGrid
from grid_test_support import FakeMouse
from command_voice import CommandVoice


class FontDropdownNameTests(unittest.TestCase):
    def rows(self):
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'ComboBox',3:'Edit',4:'MenuItem'},true_condition=True)
        root=Element(1,children=[Element(4,'Font'),Element(2,'Font',children=[Element(3,'Font')]),Element(2,'Font Size',box=(120,10,180,40))])
        return scan_visible_branches(root,10,7,'app',(0,0,800,600),uia,None,1)

    def test_grid_assigns_distinct_names_but_keeps_real_identity(self):
        rows=self.rows();combos=[r for r in rows if r['type']=='ComboBox']
        self.assertEqual([r['name'] for r in combos],['Font selection dropdown','Font size dropdown'])
        self.assertEqual([r['source_name'] for r in combos],['Font','Font Size'])
        import json
        self.assertEqual(json.loads(combos[0]['key'])[-1],'Font')

    def test_both_names_expand_correct_control_with_grid_on_without_choices(self):
        mouse=FakeMouse();mouse.expand=Mock(return_value='Dropdown open.')
        rows=self.rows()
        grid=AdaptiveGrid(mouse,lambda:[(0,0,800,600)],observer=lambda:rows,chooser=Mock(side_effect=AssertionError('Specific names must not need a chooser')))
        try:
            grid.run('open grid')
            for text,name in [('open font selection dropdown','Font selection dropdown'),('font selection dropdown','Font selection dropdown'),('open font dropdown','Font selection dropdown'),('open font size dropdown','Font size dropdown'),('font size dropdown','Font size dropdown')]:
                self.assertEqual(grid.run(text),'Dropdown open.')
                self.assertEqual(mouse.expand.call_args.args[0]['name'],name)
        finally:grid.close()

    def test_voice_accepts_specific_names_with_grid_on(self):
        session=CommandVoice({'handsfree':True})
        for text in ('font selection dropdown','font size dropdown','open font selection dropdown','open font size dropdown'):
            self.assertEqual(session.route({'text':text,'confidence':1},{'grid_active':True,'labels':['A']})['kind'],'command',text)


if __name__=='__main__':unittest.main()

import unittest
from grid_commands import parse,toggle_intent
from smart_grid import AdaptiveGrid
from grid_test_support import FakeMouse
from command_voice import CommandVoice
from grid_display import ScreenBounds


class SmartOnlyTests(unittest.TestCase):
    def controller(self):
        rows=[{'key':'one','hwnd':1,'name':'First','bounds':(10,10,90,40)},
              {'key':'two','hwnd':1,'name':'Second','bounds':(100,100,180,140)}]
        g=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:rows)
        self.addCleanup(g.close);return g

    def test_natural_on_and_off_phrases_including_typos(self):
        on=('grid','Gwen grid','open grid','open the grid','turn on grid','turn grid on','grid on','griud on','gwen grdi on','show smart grid','enable grid','start grid','activate grid','switch on grid','grid open','can you open grid please','Gwen full grid')
        off=('close grid','close the smart grid','turn off grid','turn grid off','turhn of grid','grid off','grid close','hide grid','disable grid','stop grid','exit grid','Gwen close grid')
        session=CommandVoice({'handsfree':True})
        for text in on:
            self.assertEqual(toggle_intent(text),'smart_unavailable',text)
            self.assertEqual(parse(text),[{'action':'smart_unavailable'}],text)
            self.assertEqual(session.route({'text':text,'confidence':1})['text'],'gwen grid',text)
        for text in off:
            self.assertEqual(parse(text),[{'action':'disable'}],text)
            self.assertEqual(session.route({'text':text,'confidence':1})['text'],'grid off',text)
        for text in ('open grid.txt','type open grid','close grid settings','minimize this app'):
            self.assertIsNone(toggle_intent(text),text)

    def test_only_accessible_target_boxes_no_uniform_cells(self):
        g=self.controller()
        for command in ('open grid','Gwen full grid','turn on grid'):
            g.run(command);self.assertEqual(g.mode,'smart');self.assertEqual(len(g.grid.targets),2)
            picture=g.grid.snapshot()
            self.assertEqual(len(picture[0]['cells']),2)
            self.assertNotIn('rows',g.config);self.assertNotIn('columns',g.config)
            self.assertNotIn('rows',picture[0]);self.assertNotIn('columns',picture[0])
        self.assertIsNone(parse('grid density 40 by 25',True))
        self.assertIsNone(parse('zoom A',True))

    def test_close_grid_is_idempotent_and_releases_drag(self):
        g=self.controller();g.run('close grid');self.assertFalse(g.active)
        g.run('open grid');g.run('hold A');self.assertTrue(g.mouse.held)
        g.run('turn off grid');self.assertFalse(g.active);self.assertFalse(g.mouse.held)
        self.assertIsNone(g.run('open Chrome'))

    def test_mouse_drag_nudges_and_scroll_still_work(self):
        g=self.controller();g.run('grid on');g.run('drag A to F')
        self.assertEqual(g.mouse.point,g.grid.cell('F')['point']);self.assertFalse(g.mouse.held)
        g.run('hold A');before=len(g.mouse.events);g.run('move right 100; release')
        self.assertGreater(len([x for x in g.mouse.events[before:] if x[0]=='move']),2)
        self.assertFalse(g.mouse.held)
        g.run('scroll down from F');self.assertEqual(g.mouse.events[-1][0],'scroll')

    def test_bounds_have_no_rows_columns_and_support_negative_monitors(self):
        geometry=ScreenBounds([(-200,-100,0,100),(0,0,300,200)])
        self.assertEqual(geometry.nearest(-500,-500),(-200,-100))
        self.assertEqual(geometry.nearest(999,999),(299,199))
        self.assertEqual(geometry.nearest(0,0),(0,0))


if __name__=='__main__':unittest.main()

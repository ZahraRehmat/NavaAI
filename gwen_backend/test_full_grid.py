import threading,unittest
from grid_geometry import GridMap,column_name,column_index
from grid_commands import parse
from full_grid import FullGrid

class FakeMouse:
    def __init__(self):self.point=(0,0);self.held=set();self.events=[];self.fail=False
    def position(self):return self.point
    def move(self,p):
        if self.fail:raise PermissionError('blocked')
        self.point=p;self.events.append(('move',p))
    def down(self,button='left'):self.held.add(button);self.events.append(('down',button))
    def release(self):self.held.clear();self.events.append(('release',))
    def click(self,button='left',count=1,stop=None):self.events.append(('click',button,count,self.point))
    def scroll(self,direction,amount):self.events.append(('scroll',direction,amount,self.point))

class FullGridTests(unittest.TestCase):
    def controller(self,displays=None):
        m=FakeMouse();g=FullGrid(m,displays or (lambda:[(0,0,1920,1200)]),config={'columns':16,'rows':10});g.run('gwen full grid');return g,m
    def test_exhaustive_every_pixel_covered_once_odd_negative_displays(self):
        grid=GridMap([(-97,-13,0,50),(0,0,113,79)],16,10)
        covered={}
        for area in grid.areas:
            for cell in area.cells():
                l,t,r,b=cell['bounds'];self.assertTrue(l<=cell['point'][0]<r and t<=cell['point'][1]<b)
                for y in range(t,b):
                    for x in range(l,r):covered[(x,y)]=covered.get((x,y),0)+1
        self.assertEqual(len(covered),97*63+113*79);self.assertEqual(set(covered.values()),{1})
        self.assertIsNone(grid.locate(100,-5))
    def test_corners_and_real_monitor_point_labels(self):
        grid=GridMap([(0,0,1920,1200),(1920,-200,3200,600)])
        self.assertEqual(grid.locate(0,0)['label'],'A1');self.assertEqual(grid.locate(1919,1199)['label'],'P10')
        self.assertEqual(grid.locate(3199,599)['label'],'M2-P10')
        self.assertEqual(grid.cell('m2-a1')['point'],grid.cell('M2-A1')['point'])
        self.assertEqual(grid.cell('a')['label'],'A1')
        self.assertEqual(column_index(column_name(60)),60)
    def test_zoom_reset_and_one_pixel_nudges(self):
        g,m=self.controller();g.run('zoom A1');self.assertEqual(g.grid.areas[0].bounds,(0,0,120,120))
        g.run('A1');before=m.point;g.run('move right 1');self.assertEqual(m.point,(before[0]+1,before[1]))
        g.run('reset grid');self.assertEqual(g.grid.areas[0].bounds,(0,0,1920,1200))
        g.run('pixel 1919 1199');self.assertEqual(m.point,(1919,1199))
        with self.assertRaises(ValueError):g.run('pixel 1920 1200')
    def test_inactive_leaves_agent_commands_untouched(self):
        g=FullGrid(FakeMouse(),lambda:[(0,0,100,100)])
        self.assertIsNone(g.run('open Chrome'));self.assertIsNone(g.run('A1'))
        g.run('full grid');self.assertIsNone(g.run('open Word'))
        g.run('exit grid');self.assertIsNone(g.run('open Word'))
    def test_expected_command_actions(self):
        g,m=self.controller();g.run('B2');self.assertEqual(m.point,g.grid.cell('B2')['point'])
        g.run('double click C3');self.assertEqual(m.events[-1][:3],('click','left',2))
        g.run('right click D4');self.assertEqual(m.events[-1][:3],('click','right',1))
        g.run('sroll down on G4');self.assertEqual(m.events[-1],('scroll','down',5,g.grid.cell('G4')['point']))
        g.run('hold A1 and move right 100 and release');self.assertEqual(m.held,set())
        g.run('hold right B2');self.assertEqual(m.held,{'right'});g.run('drop');self.assertEqual(m.held,set())
    def test_errors_and_emergency_stop_release_held_mouse(self):
        g,m=self.controller();g.run('hold A1');m.fail=True
        with self.assertRaises(PermissionError):g.run('B2')
        self.assertFalse(m.held)
        m.fail=False;g.run('hold A1');g.emergency_stop();self.assertFalse(m.held);self.assertFalse(g.active)
    def test_topology_change_refreshes_without_clicking(self):
        boxes=[(0,0,1920,1200)];g,m=self.controller(lambda:boxes[:]);g.run('hold A1');boxes[:]=[(0,0,1280,800)]
        count=sum(e[0]=='click' for e in m.events);result=g.run('click A1')
        self.assertIn('Display layout changed',result);self.assertFalse(m.held)
        self.assertEqual(sum(e[0]=='click' for e in m.events),count)
    def test_drag_releases_on_finish_and_stop(self):
        g,m=self.controller();g.run('drag A1 to B2');self.assertFalse(m.held);self.assertEqual(m.point,g.grid.cell('B2')['point'])
        g.stop.set();g.run('drag A1 to B2');self.assertFalse(m.held)
    def test_density_validation_and_invalid_chain_no_input(self):
        g,m=self.controller();g.run('grid size 20 by 12');self.assertEqual(len(list(g.grid.areas[0].cells())),240)
        with self.assertRaises(ValueError):g.run('grid size 100 by 100')
        before=list(m.events)
        with self.assertRaises(ValueError):g.run('click A1; nonsense command')
        self.assertEqual([e for e in m.events[len(before):] if e[0]!='release'],[])
    def test_hold_parser_typo_and_plain_labels(self):
        self.assertEqual(parse('doubkle lcick a1',True)[0]['action'],'double click')
        self.assertEqual(parse('move cursor left 5 pixels',True)[0]['amount'],5)
        self.assertEqual(parse('A1',True)[0]['action'],'click')
        self.assertEqual(parse('move to A1',True)[0]['action'],'move')
        self.assertEqual(parse('release',True)[0]['action'],'release')
    def test_bare_label_clicks_and_explicit_move_does_not(self):
        g,m=self.controller();g.run('b2')
        self.assertEqual(m.events[-1],('click','left',1,g.grid.cell('B2')['point']))
        before=len([e for e in m.events if e[0]=='click']);g.run('move to C3')
        self.assertEqual(len([e for e in m.events if e[0]=='click']),before)
        g.run('hold A1');g.run('B2');self.assertTrue(m.held)
        self.assertEqual(len([e for e in m.events if e[0]=='click']),before)
    def test_scroll_location_phrases_move_and_wheel_without_click(self):
        g,m=self.controller()
        for command in ('scroll down from G4','scroll down formg4','scroll down G4','from G4 scroll down','scroll down 3 steps over G4','scroll down on G4 3 times','scroll down a little at G4'):
            before=len(m.events);g.run(command)
            self.assertEqual(m.events[-1][0],'scroll',command)
            self.assertEqual(m.events[-1][-1],g.grid.cell('G4')['point'],command)
            self.assertFalse(any(e[0]=='click' for e in m.events[before:]),command)
        g.run('scroll up from G4 and scroll down at G4');self.assertEqual(m.events[-1][1],'down')
    def test_typing_in_chat_does_not_lose_last_grid_point(self):
        g,m=self.controller();g.run('C3');chosen=m.point
        m.point=(1800,1000) # User/GUI moved the physical mouse to the chat entry.
        g.run('click');self.assertEqual(m.events[-1],('click','left',1,chosen))
        m.point=(1700,900);g.run('move right 1');self.assertEqual(m.point,(chosen[0]+1,chosen[1]))
    def test_held_nudges_emit_intermediate_motion_before_release(self):
        g,m=self.controller();g.run('hold C3');before=len(m.events);g.run('move right 100; release')
        moves=[e for e in m.events[before:] if e[0]=='move']
        self.assertGreater(len(moves),2);self.assertFalse(m.held)

if __name__=='__main__':unittest.main()

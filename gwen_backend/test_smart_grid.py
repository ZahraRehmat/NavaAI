import threading,time,unittest
from smart_grid import SmartMap,AdaptiveGrid
from test_full_grid import FakeMouse

def row(key='one',bounds=(10,10,90,45),**extra):
    return {'key':key,'bounds':bounds,'name':key,'hwnd':100,**extra}

class SmartTests(unittest.TestCase):
    def test_scroll_without_label_uses_current_point(self):
        g=self.controller()
        for text in ('scroll down','scroll up'):
            g.run(text)
            self.assertEqual(g.mouse.events[-1][0],'scroll')
            self.assertTrue(g.active)
    def controller(self):
        self.rows=[row(),row('two',(100,10,180,45))];self.pictures=[]
        grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,1920,1200)],observer=lambda:list(self.rows),render=self.pictures.append)
        self.addCleanup(grid.close);grid.run('gwen grid');return grid

    def test_stable_identity_moves_and_no_label_recycling(self):
        m=SmartMap([(0,0,800,600)]);m.update([row(),row('two')]);self.assertEqual(m.cell('A')['name'],'one')
        m.update([row('two'),row(bounds=(200,200,240,240))]);self.assertEqual(m.cell('A')['point'],(219,219))
        m.update([row('two'),row('new')]);self.assertEqual(m.cell('H')['name'],'new')
        with self.assertRaises(ValueError):m.cell('A')

    def test_move_click_scroll_and_removed_target_rejected(self):
        g=self.controller();g.run('A');self.assertEqual(g.mouse.point,(49,27))
        self.assertEqual(g.mouse.events[-1],('click','left',1,(49,27)))
        self.rows[0]=row(bounds=(300,100,380,140));g.run('double click A')
        self.assertEqual(g.mouse.events[-1],('click','left',2,(339,119)))
        g.run('scroll down on F');self.assertEqual(g.mouse.events[-1][0],'scroll')
        self.rows=[];before=list(g.mouse.events)
        with self.assertRaises(ValueError):g.run('click A')
        self.assertFalse(any(e[0]=='click' for e in g.mouse.events[len(before):]))

    def test_bare_multiletter_target_and_move_only(self):
        g=self.controller();self.rows=[row(str(i),(i*10,10,i*10+8,40)) for i in range(163)];g.refresh()
        g.run('fg');self.assertEqual(g.mouse.events[-1],('click','left',1,g.grid.cell('FG')['point']))
        before=len([e for e in g.mouse.events if e[0]=='click']);g.run('move to FG')
        self.assertEqual(len([e for e in g.mouse.events if e[0]=='click']),before)
        g.run('hold FG');g.run('FG');self.assertTrue(g.mouse.held)
        self.assertEqual(len([e for e in g.mouse.events if e[0]=='click']),before)
    def test_smart_scroll_from_label_and_named_target_never_clicks(self):
        g=self.controller();self.rows=[row(str(i),(i*10,10,i*10+8,40)) for i in range(163)];g.refresh()
        for command in ('scroll down from fg','scroll up fg','scroll down formfg','scroll up 2 steps at FG'):
            before=len(g.mouse.events);g.run(command)
            self.assertEqual(g.mouse.events[-1][0],'scroll',command)
            self.assertEqual(g.mouse.events[-1][-1],g.grid.cell('FG')['point'],command)
            self.assertFalse(any(e[0]=='click' for e in g.mouse.events[before:]),command)
        self.rows=[row('search',name='Search chats')];g.refresh()
        g.run('scroll up from Search chats');self.assertEqual(g.mouse.events[-1][:3],('scroll','up',5))

    def test_chain_validated_before_any_input(self):
        g=self.controller();before=list(g.mouse.events)
        with self.assertRaises(ValueError):g.run('click A then click Z')
        self.assertFalse(any(e[0]=='click' for e in g.mouse.events[len(before):]))

    def test_auto_refresh_without_commands(self):
        g=self.controller();self.rows.append(row('new'))
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and len(g.grid.targets)<3:time.sleep(.02)
        self.assertEqual(g.grid.cell('H')['name'],'new')

    def test_scan_failure_clears_old_labels_and_recovers(self):
        g=self.controller()
        def failed():raise OSError('app unavailable')
        g.observer=failed;g.refresh();self.assertEqual(g.grid.targets,{});self.assertIn('unavailable',g.error)
        g.observer=lambda:[row()];g.refresh();self.assertEqual(g.grid.cell('A')['name'],'one')

    def test_mode_switch_and_emergency_release(self):
        g=self.controller();g.run('hold A');self.assertTrue(g.mouse.held)
        g.run('gwen full grid');self.assertFalse(g.mouse.held);self.assertEqual(g.mode,'full')
        g.run('click A1');g.run('gwen grid');g.run('hold A');g.emergency_stop()
        self.assertFalse(g.active);self.assertFalse(g.mouse.held);self.assertIsNone(g.run('open chrome'))

    def test_inflight_refresh_cannot_resurrect_stopped_grid(self):
        g=self.controller();entered=threading.Event();release=threading.Event()
        def slow():entered.set();release.wait(2);return [row('late')]
        g.observer=slow;t=threading.Thread(target=g.refresh);t.start();entered.wait(2)
        g.emergency_stop();release.set();t.join(3);self.assertFalse(g.active)
        self.assertFalse(self.pictures[-1]['active'])

    def test_empty_smart_grid_does_not_fall_through_to_ai(self):
        g=self.controller();self.rows=[];g.refresh()
        from label_matching import NoLabelMatch
        self.assertIsNone(g.run('open chrome')) # Launcher owns non-visible app requests.
        self.assertIn('refreshed',g.run('refresh grid'))

    def test_mouse_synonyms_and_named_taskbar_targets(self):
        g=self.controller()
        self.rows=[row('start',scope='taskbar',name='Start'),row('chrome',(100,10,180,45),scope='taskbar',name='Google Chrome - 1 running window pinned'),row('mic',(200,10,280,45),scope='taskbar',name='Privacy Microphone in use by: Google Chrome')]
        g.refresh()
        for name in ('win','windows','win button','windows button','startup button','start menu'):
            g.run('press '+name);self.assertEqual(g.mouse.events[-1],('click','left',1,(49,27)))
        g.run('select Chrome');self.assertEqual(g.mouse.events[-1],('click','left',1,(139,27)))
        g.run('open Chrome');self.assertEqual(g.mouse.events[-1],('click','left',2,(139,27)))
        label=next(x['label'] for x in g.grid.targets.values() if x['key']=='chrome')
        g.run('press '+label);self.assertEqual(g.mouse.events[-1][2],1)
        g.run('open '+label);self.assertEqual(g.mouse.events[-1][2],2)

    def test_named_and_letter_command_chain(self):
        g=self.controller();self.rows[0]=row(scope='taskbar',name='Start');g.refresh()
        g.run('press windows button then select F');self.assertEqual(g.mouse.events[-1],('click','left',1,(139,27)))

    def test_ambiguous_names_use_choice_not_guess(self):
        g=self.controller();self.rows=[row(name='Save'),row('another',(100,10,180,45),name='Save')];g.refresh()
        choices=[]
        def choose(query,options):choices.extend(options);return 1
        g.chooser=choose;g.run('press Save')
        self.assertEqual(len(choices),2);self.assertEqual(g.mouse.events[-1][-1],(139,27))

    def test_window_exposure_subtracts_covered_desktop(self):
        from grid_visibility import exposed
        self.assertEqual(exposed((0,0,100,100),[(0,0,100,100)]),[])
        regions=exposed((0,0,100,100),[(20,20,80,80)])
        self.assertEqual(sum((r-l)*(b-t) for l,t,r,b in regions),6400)

    def test_activation_handles_exceptions_with_no_message(self):
        import queue
        g=self.controller()
        def empty():raise queue.Empty()
        g.observer=empty
        result=g.run('gwen grid')
        self.assertIn('Smart grid on',result);self.assertIn('Empty',result)
        self.assertTrue(g.active);self.assertFalse(g.grid.targets)
        g.observer=lambda:[row()];g.refresh();self.assertTrue(g.grid.targets)

    def test_scanner_timeout_keeps_partial_targets_and_quarantines_stall(self):
        import queue,json
        from unittest.mock import Mock
        from smart_grid import AccessibleTargets
        observer=AccessibleTargets(lambda:None,response_timeout=.1)
        process=Mock();process.poll.return_value=None;observer.process=process
        observer.answers=queue.Queue()
        observer.answers.put(json.dumps({'partial':True,'rows':[row(scope='taskbar')]}))
        observer.answers.put(json.dumps({'scanning':9876}))
        observer.close=Mock()
        rows=observer.scan()
        self.assertEqual(rows[0]['scope'],'taskbar');self.assertIn('timed out',observer.warning)
        self.assertIn(9876,observer.quarantined);observer.close.assert_called_once()

    def test_scanner_timeout_without_partial_data_recovers_on_next_response(self):
        import queue,json
        from unittest.mock import Mock
        from smart_grid import AccessibleTargets
        observer=AccessibleTargets(lambda:None,response_timeout=.1)
        process=Mock();process.poll.return_value=None;observer.process=process;observer.answers=queue.Queue();observer.close=Mock()
        self.assertEqual(observer.scan(),[]);self.assertIn('retrying automatically',observer.warning)
        observer.answers.put(json.dumps({'rows':[row()],'timing':{}}))
        self.assertEqual(len(observer.scan()),1);self.assertEqual(observer.warning,'')

    def test_chain_reobserves_after_a_click_moves_next_target(self):
        g=self.controller();original=g.mouse.click
        def click(*args,**kwargs):
            original(*args,**kwargs)
            self.rows[1]=row('two',(600,400,700,440))
        g.mouse.click=click;g.run('click A then click F')
        self.assertEqual(g.mouse.events[-1],('click','left',1,(649,419)))

    def test_partial_offscreen_and_monitor_gaps(self):
        m=SmartMap([(-100,0,0,100),(100,0,200,100)])
        m.update([row(bounds=(-120,-10,200,90)),row('outside',(500,500,600,600))])
        self.assertEqual(len(m.targets),1);self.assertEqual(m.cell('A')['bounds'],(-100,0,0,90))
        self.assertEqual(m.cell('A')['point'],(-51,44))

    def test_mode_switch_in_chain_does_not_execute_input(self):
        g=self.controller();before=list(g.mouse.events)
        with self.assertRaises(ValueError):g.run('click A then gwen grid')
        self.assertEqual(g.mouse.events,before);self.assertEqual(g.mode,'smart')

if __name__=='__main__':unittest.main()

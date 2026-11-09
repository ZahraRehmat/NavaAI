import unittest
from unittest.mock import Mock,patch,PropertyMock
from types import SimpleNamespace
from dropdown_control import dropdown_intent,expand_wrapper
from grid_commands import parse
from smart_grid import AdaptiveGrid
from grid_test_support import FakeMouse
from test_smart_grid import row


class DropdownTests(unittest.TestCase):
    def test_natural_commands_and_grid_codes(self):
        for text in ('open Font Color dropdown','click the Font Color drop down arrow','open dropdown Font Color','expand Font Color'):
            self.assertEqual(dropdown_intent(text),'Font Color')
        self.assertEqual(parse('open dropdown HF',True),[{'action':'expand','label':'HF'}])
        self.assertEqual(parse('open dropdown A then click F',True),[{'action':'expand','label':'A'},{'action':'click','label':'F'}])
        self.assertEqual(parse('open Font Color dropdown',True),[{'action':'expand','target_name':'Font Color'}])
        self.assertIsNone(dropdown_intent('click bold'));self.assertIsNone(dropdown_intent('type open Font Color dropdown'))
        from command_voice import CommandVoice
        decision=CommandVoice({'handsfree':True}).route({'text':'open dropdown hotel foxtrot','confidence':1},{'grid_active':True,'labels':['HF']})
        self.assertEqual(decision['text'],'open dropdown HF')

    def wrapper(self,state=0):
        wrapper=Mock();pattern=Mock();wrapper.iface_expand_collapse=pattern
        pattern.CurrentExpandCollapseState=state
        pattern.Expand.side_effect=lambda:setattr(pattern,'CurrentExpandCollapseState',1)
        return wrapper,pattern

    def test_expand_never_invokes_main_action_and_already_open_is_noop(self):
        wrapper,pattern=self.wrapper()
        self.assertEqual(expand_wrapper(wrapper),'Dropdown open.')
        pattern.Expand.assert_called_once();wrapper.iface_invoke.Invoke.assert_not_called();wrapper.click_input.assert_not_called()
        self.assertEqual(expand_wrapper(wrapper),'Dropdown open.');pattern.Expand.assert_called_once()

    def test_failed_expand_does_not_invoke_main_button_or_guess_arrow(self):
        wrapper,pattern=self.wrapper();pattern.Expand.side_effect=RuntimeError('provider refused')
        with self.assertRaises(RuntimeError):expand_wrapper(wrapper)
        wrapper.iface_invoke.Invoke.assert_not_called();wrapper.click_input.assert_not_called()
        wrapper,pattern=self.wrapper(3)
        with self.assertRaises(ValueError):expand_wrapper(wrapper)
        pattern.Expand.assert_not_called()

    def test_separate_observed_arrow_when_parent_has_no_pattern(self):
        wrapper=SimpleNamespace(iface_invoke=Mock(),click_input=Mock())
        child=Mock();child.element_info.name='More Options';child.is_visible.return_value=True;child.is_enabled.return_value=True
        child.iface_expand_collapse.CurrentExpandCollapseState=3;wrapper.children=lambda:[child]
        self.assertIn('observed arrow',expand_wrapper(wrapper));child.iface_invoke.Invoke.assert_called_once()
        wrapper.iface_invoke.Invoke.assert_not_called();wrapper.click_input.assert_not_called()

    def test_grid_open_expands_but_plain_main_click_is_preserved(self):
        mouse=FakeMouse();mouse.expand=Mock(return_value='Dropdown open.')
        grid=AdaptiveGrid(mouse,lambda:[(0,0,800,600)],observer=lambda:[row('Font Color',expandable=True,type='SplitButton')])
        try:
            grid.run('open grid');grid.run('A')
            self.assertEqual(mouse.events[-1][0],'click');mouse.expand.assert_not_called()
            before=len([e for e in mouse.events if e[0]=='click'])
            self.assertEqual(grid.run('open A'),'Dropdown open.')
            self.assertEqual(grid.run('open dropdown A'),'Dropdown open.')
            self.assertEqual(len([e for e in mouse.events if e[0]=='click']),before);self.assertEqual(mouse.expand.call_count,2)
        finally:grid.close()

    def test_split_arrow_grid_name_and_real_bounds(self):
        from grid_branch_scan import scan_visible_branches
        from test_grid_branches import Element
        arrow=Element(3,'More Options',box=(85,10,100,50));main=Element(2,'Font Color',children=[arrow],box=(10,10,100,50))
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'SplitButton',3:'MenuItem'},true_condition=True)
        rows=scan_visible_branches(Element(1,children=[main]),1,2,'app',(0,0,800,600),uia,None,1.4)
        self.assertEqual([r['name'] for r in rows],['Font Color','Font Color dropdown'])
        self.assertEqual(rows[1]['bounds'],(85,10,100,50))

    def test_native_split_click_expands_and_regular_button_keeps_invoke(self):
        from accessibility import NativeControls
        probe=NativeControls();probe.hwnd=20;probe.bounds=(0,0,800,600)
        wrapper,pattern=self.wrapper();wrapper.element_info.control_type='SplitButton';probe.controls={1:wrapper}
        with patch('windows_api.focus_handle',return_value=20),patch('windows_api.rect',return_value=probe.bounds):
            self.assertEqual(probe.act({'action':'ui_click','id':1}),'Dropdown open.')
        wrapper.iface_invoke.Invoke.assert_not_called()
        wrapper.element_info.control_type='Button'
        with patch('windows_api.focus_handle',return_value=20),patch('windows_api.rect',return_value=probe.bounds):probe.act({'action':'ui_click','id':1})
        wrapper.iface_invoke.Invoke.assert_called_once()

    def test_edit_label_expands_owning_combo_without_clicking_or_changing_text(self):
        owner,pattern=self.wrapper();owner.element_info.control_type='ComboBox'
        child=SimpleNamespace(element_info=SimpleNamespace(control_type='Edit',name='Font'),parent=lambda:owner,iface_invoke=Mock(),click_input=Mock(),set_edit_text=Mock())
        self.assertEqual(expand_wrapper(child),'Dropdown open.')
        pattern.Expand.assert_called_once();child.iface_invoke.Invoke.assert_not_called();child.click_input.assert_not_called();child.set_edit_text.assert_not_called()

    def test_owner_search_does_not_escape_into_ribbon_group(self):
        group=SimpleNamespace(element_info=SimpleNamespace(control_type='Group',name='Font'))
        child=SimpleNamespace(element_info=SimpleNamespace(control_type='Edit',name='Text'),parent=lambda:group,children=lambda:[])
        with self.assertRaises(ValueError):expand_wrapper(child)

    def test_font_edit_grid_target_knows_its_dropdown_owner(self):
        from grid_branch_scan import scan_visible_branches
        from test_grid_branches import Element
        edit=Element(3,'Font',box=(10,10,90,40));combo=Element(2,'Font',children=[edit],box=(10,10,110,40))
        uia=SimpleNamespace(known_control_type_ids={1:'Pane',2:'ComboBox',3:'Edit'},true_condition=True)
        rows=scan_visible_branches(Element(1,children=[combo]),1,2,'app',(0,0,800,600),uia,None,1)
        self.assertTrue(rows[1]['expandable']);self.assertEqual(rows[1]['dropdown_owner'],'Font')

    def test_missing_dropdown_name_delegates_grid_to_agent_without_model(self):
        from agent import Agent
        chooser=Mock(side_effect=AssertionError('Do not offer unrelated target choices'))
        grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[row('Font')],chooser=chooser)
        try:
            grid.run('open grid')
            self.assertIsNone(grid.run('open dropdown'))
            chooser.assert_not_called()
        finally:grid.close()
        agent=Agent(log=lambda _:None)
        with patch('planner.Planner',side_effect=AssertionError('No model for missing dropdown name')):
            self.assertIn('Which dropdown?',agent.run('open dropdown'))
        agent.close()

    def test_font_selector_alias_has_a_specific_target(self):
        self.assertEqual(dropdown_intent('open font selecting dropdown'),'Font')
        self.assertEqual(dropdown_intent('open font selection dropdown'),'Font')
        from command_voice import CommandVoice
        gate=CommandVoice({'handsfree':True})
        result=gate.route({'text':'open font selecting dropdown','confidence':.91171,'words':[
            {'word':'open','probability':1},{'word':'font','probability':1},{'word':'selecting','probability':.64684},{'word':'dropdown','probability':1}]})
        self.assertEqual(result['kind'],'command')
        unclear=gate.route({'text':'open font color dropdown','confidence':.9,'words':[{'word':'font','probability':1},{'word':'color','probability':.4}]})
        self.assertEqual(unclear['kind'],'review')

    def test_named_font_dropdown_prefers_unique_combo_over_duplicate_menu_caption(self):
        from agent import Agent
        agent=Agent(log=lambda _:None,choose=Mock(side_effect=AssertionError('No ambiguity for a unique exact Font combo')))
        agent.native=Mock();agent.native.observe.return_value=[{'id':1,'name':'Font','type':'MenuItem','expandable':True},{'id':2,'name':'Font','type':'ComboBox','expandable':True}]
        agent.native.act.return_value='Dropdown open.'
        with patch.object(agent,'_focus_native',return_value=20),patch('windows_api.action_window',return_value=20):
            self.assertEqual(agent.click_named_native('Font',expand=True),'Dropdown open.')
        self.assertEqual(agent.native.act.call_args.args[0]['id'],2)
        agent.close()


if __name__=='__main__':unittest.main()

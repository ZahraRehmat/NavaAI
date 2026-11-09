import threading,unittest
from unittest.mock import Mock,patch
from dropdown_choices import candidates,choose
from dropdown_control import grid_dropdown_name


class DropdownChoicesTests(unittest.TestCase):
    def test_more_than_26_markers_work_without_scrolling_or_extra_grid_pages(self):
        from smart_labels import smart_label
        from dialog_voice import answer,grammar
        from choice_ui import TargetChooser
        from types import SimpleNamespace
        labels=[smart_label(i) for i in range(43)]
        self.assertEqual(answer('alpha alpha',43,labels=labels),12)
        self.assertIn('alpha alpha',grammar({'dialog_labels':labels,'dialog_count':43}))
        chooser=TargetChooser.__new__(TargetChooser);chooser.labels=labels
        chooser.key_buffer='';chooser.key_after=None;chooser.window=Mock();chooser.finish=Mock()
        chooser.key_choice(SimpleNamespace(char='a',keysym='a'))
        chooser.key_choice(SimpleNamespace(char='a',keysym='a'))
        chooser.finish.assert_called_once_with(12)
    def rows(self):
        return [dict(id=1,name='Font',source_name='Font',type='ComboBox',bounds=[10,10,100,40]),
                dict(id=2,name='FontSize',source_name='FontSize',type='ComboBox',bounds=[110,10,170,40]),
                dict(id=3,name='Font',type='MenuItem',expandable=True,bounds=[10,10,100,40]),
                dict(id=4,name='Bold',type='Button',bounds=[10,50,40,80])]

    def test_font_name_and_size_are_distinct_and_duplicate_caption_is_ignored(self):
        options=candidates(self.rows())
        self.assertEqual([r['label'] for r in options],['Font selection dropdown','Font size dropdown'])
        self.assertEqual(grid_dropdown_name('FontName'),'Font selection dropdown')
        self.assertEqual(grid_dropdown_name('FontSize'),'Font size dropdown')

    def test_excel_and_powerpoint_chooser_marks_observed_controls_and_expands_selected_arrow(self):
        for kind in ('XLMAIN','PPTFrameClass'):
            target={'hwnd':99,'pid':7,'class_name':kind,'title':'Office'}
            agent=Mock();agent.interaction=target;agent.stop=threading.Event();agent.choose=True
            agent.choose_targets.return_value=1
            with patch('accessibility.NativeControls') as cls,patch('windows_api.target_alive',return_value=True),patch('office_control.execute_office',return_value=None):
                cls.return_value.observe.return_value=self.rows();cls.return_value.act.return_value='Dropdown open.'
                self.assertIn('Font size',choose(agent))
                options=agent.choose_targets.call_args.args[1]
                self.assertEqual(options[1]['bounds'],[110,10,170,40])
                cls.return_value.act.assert_called_once_with({'action':'ui_click','id':2,'expected_name':'FontSize','expand':True})

    def test_cancel_never_opens_a_control(self):
        agent=Mock();agent.interaction={'hwnd':99,'class_name':'PPTFrameClass'};agent.stop=threading.Event();agent.choose=True
        agent.choose_targets.return_value=None
        with patch('accessibility.NativeControls') as cls:
            cls.return_value.observe.return_value=self.rows()
            with self.assertRaises(InterruptedError):choose(agent)
            cls.return_value.act.assert_not_called()

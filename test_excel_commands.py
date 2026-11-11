import threading,unittest
from unittest.mock import Mock,patch
from excel_commands import parse,address,apply
from agent import Agent
from command_voice import CommandVoice
from grid_input import keyboard_command

EXCEL={'hwnd':99,'pid':7,'class_name':'XLMAIN','title':'Book1 - Excel'}


class ExcelCommandsTests(unittest.TestCase):
    def test_cell_and_range_wordings(self):
        for task,target in [('select G6','G6'),('select H7 cell','H7'),('select b two','B2'),('select from y7 to z9','Y7:Z9'),('select cells B2 to N6','B2:N6'),('select from cell B2 to cell N6','B2:N6')]:
            self.assertEqual(parse(task)['target'],target,task)
        for value in ('XFE1','A0','A1048577'):self.assertIsNone(address(value))
        self.assertEqual(address('B2toN6'),'B2:N6')
        self.assertEqual(parse('copy cell 9')['action'],'ask')
        self.assertIsNone(parse('type select G6'))

    def test_edit_copy_paste_table_and_cell_dropdown(self):
        cases=[('double click cell a one','excel_edit','A1'),('edit J7 and start dictation','excel_edit','J7'),
               ('copy B2 to N6','excel_copy','B2:N6'),('paste copied data in cell K10','excel_paste','K10'),
               ('make a table','excel_table',''),('create table','excel_table',''),
               ('make a table from selected cells','excel_table',''),('make selected cells into a table','excel_table',''),
               ('open dropdown in G6','excel_dropdown','G6')]
        for task,action,target in cases:
            command=parse(task);self.assertEqual((command['action'],command['target']),(action,target),task)
            self.assertTrue(keyboard_command(task,EXCEL),task)
        self.assertTrue(parse('edit J7 and start dictation')['dictate'])
        self.assertFalse(parse('edit J7')['dictate'])

    def app(self):
        app=Mock();app.Workbooks.Count=1
        cell=app.ActiveSheet.Range.return_value
        cell.Areas.Count=1;cell.CountLarge=1
        return app,cell

    def test_copy_and_paste_use_excel_clipboard_not_literal_retyping(self):
        app,cell=self.app()
        apply(app,{'action':'excel_copy','target':'B2'})
        cell.Copy.assert_called_once();cell.Select.assert_not_called()
        apply(app,{'action':'excel_paste','target':'K10'})
        app.Goto.assert_called_once_with(cell,True);app.ActiveSheet.Paste.assert_called_once()

    def test_edit_selects_exact_cell_before_f2_and_checks_focus(self):
        app,cell=self.app();app.Hwnd=99
        with patch('windows_api.foreground',return_value=99),patch('desktop_control.act') as keys:
            self.assertIn('J7',apply(app,{'action':'excel_edit','target':'J7'}))
            app.ActiveSheet.Range.assert_called_with('J7');app.Goto.assert_called_once_with(cell,True)
            keys.assert_called_once_with({'action':'press','key':'f2'})
        with patch('windows_api.foreground',return_value=100),patch('desktop_control.act') as keys:
            with self.assertRaises(ValueError):apply(app,{'action':'excel_edit','target':'J7'})
            keys.assert_not_called()

    def test_table_uses_selection_and_does_not_replace_existing_table(self):
        app,cell=self.app();app.Selection=cell
        cell.Rows.Count=3;cell.ListObject=None
        apply(app,{'action':'excel_table','target':''})
        self.assertIs(app.ActiveSheet.ListObjects.Add.call_args.args[1],cell)
        self.assertEqual(app.ActiveSheet.ListObjects.Add.return_value.TableStyle,'TableStyleMedium2')
        app.ActiveSheet.ListObjects.Add.reset_mock();cell.ListObject=Mock()
        with self.assertRaises(ValueError):apply(app,{'action':'excel_table','target':''})
        app.ActiveSheet.ListObjects.Add.assert_not_called()

    def test_validation_dropdown_requires_actual_list(self):
        app,cell=self.app();app.Hwnd=99
        cell.Validation.Type=1
        with patch('desktop_control.act') as keys:
            with self.assertRaises(ValueError):apply(app,{'action':'excel_dropdown','target':'G6'})
            keys.assert_not_called()
        cell.Validation.Type=3;cell.Validation.InCellDropdown=True
        with patch('windows_api.foreground',return_value=99),patch('desktop_control.act') as keys:
            apply(app,{'action':'excel_dropdown','target':'G6'})
            keys.assert_called_once_with({'action':'hotkey','keys':['alt','down']})

    def test_agent_routes_ranges_before_text_selection_and_only_enables_requested_dictation(self):
        enabled=Mock();agent=Agent(log=lambda _:None,start_dictation=enabled)
        try:
            with patch.object(agent,'_focus_native'),patch('office_control.execute_office',return_value='OK') as execute,patch('planner.Planner',side_effect=AssertionError('No Qwen')):
                agent.run('select from B2 to N6',interaction=EXCEL)
                self.assertEqual(execute.call_args.args[1]['target'],'B2:N6');enabled.assert_not_called()
                agent.run('edit J7 and start dictation',interaction=EXCEL);enabled.assert_called_once()
        finally:agent.close()

    def test_voice_routes_cells_even_in_text_selection_or_dictation_mode(self):
        for mode in ('selecting','dictating'):
            voice=CommandVoice({'handsfree':True});setattr(voice,mode,True)
            result=voice.route({'text':'select from Y7 to Z9','confidence':1},{'office':'excel'})
            self.assertEqual(result['kind'],'command');self.assertEqual(result['text'],'select from Y7 to Z9')

import threading,unittest
from unittest.mock import Mock,patch
from browser_commands import intent,tab_index
from grid_input import keyboard_command
from speech_context import correct
from native_browser import select_tab,command
from test_existing_browser import CHROME


class ChromeGridTabTests(unittest.TestCase):
    def test_grid_label_closes_exact_tab_without_app_close_route(self):
        from smart_grid import AdaptiveGrid
        from grid_test_support import FakeMouse
        mouse=FakeMouse();mouse.tab_action=Mock(return_value='Tab selected')
        rows=[{'key':'tab','bounds':(10,10,120,40),'name':'Docs','type':'TabItem','hwnd':44}]
        grid=AdaptiveGrid(mouse,lambda:[(0,0,800,600)],observer=lambda:rows)
        try:
            grid.run('grid on');self.assertEqual(grid.run('click A'),'Tab selected')
            mouse.tab_action.assert_called_with(grid.grid.cell('A'),grid.stop)
            mouse.tab_action.return_value='Tab closed'
            self.assertEqual(grid.run('close A'),'Tab closed')
            self.assertTrue(mouse.tab_action.call_args.kwargs['close'])
        finally:grid.close()
    def test_tab_commands_bypass_grid(self):
        for text in ('close tab','close current tab','close tab two','close youtube tab',
                     'select second tab','select tab two','next tab','previous tab','new tab'):
            self.assertTrue(keyboard_command(text),text)
        self.assertEqual(intent('close tab two'),{'action':'tab_close','target':'two'})
        self.assertEqual(tab_index('two',[{'name':'One'},{'name':'Two'}]),1)
        self.assertEqual(correct('close alpha foxtrot',{'grid_active':True,'labels':['AF']}).text,'close AF')

    def test_visible_grid_vocabulary_omits_confusable_unused_letters(self):
        from vosk_speech import vocabulary
        model=Mock();model.vosk_model_find_word.return_value=1
        phrases=vocabulary({'grid_active':True,'labels':['A','B','AF','AH']},model)
        self.assertNotIn('c',phrases);self.assertNotIn('charlie',phrases)
        self.assertIn('b',phrases);self.assertIn('close tab two',phrases)
        self.assertIn('press control c',phrases)
        excel=vocabulary({'grid_active':True,'labels':['A'],'office':'excel'},model)
        self.assertIn('c',excel)  # Actual worksheet columns keep their names.

    def test_tab_selection_must_be_confirmed_before_close(self):
        tab={'name':'Docs','runtime_id':(1,2),'selected':False,'element':Mock()}
        selected={**tab,'selected':True}
        with patch('native_browser.focused'),patch('native_browser.observe_tabs',side_effect=[[tab],[tab],[selected]]),patch('native_browser.win.title',return_value=CHROME['title']):
            ctx,message=select_tab(CHROME,'one',threading.Event())
            tab['element'].iface_selection_item.Select.assert_called_once()
            self.assertIn('Docs',message)
        stop=Mock();stop.is_set.return_value=False
        with patch('native_browser.focused'),patch('native_browser.observe_tabs',return_value=[tab]),patch('native_browser.keys') as keys:
            with self.assertRaisesRegex(ValueError,'did not confirm'):command(CHROME,{'action':'tab_close','target':'one'},stop)
            keys.assert_not_called()

    def test_native_grid_click_and_close_use_observed_tab(self):
        import json
        from native_browser import grid_tab
        cell={'type':'TabItem','hwnd':44,'key':json.dumps((5,44,[8,9],'TabItem','Docs'))}
        rows=[{'name':'Docs','runtime_id':(8,9),'selected':False}]
        with patch('native_browser.win.title',return_value=CHROME['title']),patch('native_browser.observe_tabs',return_value=rows),patch('native_browser.select_tab',return_value=(CHROME,'Selected Docs')) as select,patch('native_browser.command',return_value='Closed Docs') as close:
            self.assertEqual(grid_tab(cell,threading.Event()),'Selected Docs')
            self.assertEqual(grid_tab(cell,threading.Event(),close=True),'Closed Docs')
            self.assertEqual(select.call_args.args[1],'1');close.assert_called_once()

    def test_safe_multiletter_choices_and_large_grid_codes(self):
        from smart_labels import smart_label
        from dialog_voice import answer,grammar
        from grid_commands import parse
        labels=[smart_label(i) for i in range(25)]
        self.assertEqual(labels[12],'AA')
        self.assertEqual(answer('alpha alpha',25,labels=labels),12)
        self.assertIn('alpha alpha',grammar({'dialog_labels':labels,'dialog_count':25}))
        label=smart_label(2000)
        self.assertEqual(parse('click '+label,True)[0]['label'],label)
        self.assertEqual(correct('click '+label,{'grid_active':True,'labels':[label]}).code,label)

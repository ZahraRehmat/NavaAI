import threading,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from catalog import Catalog,ALIASES
from window_commands import match_window,NoRunningWindow,open_and_activate
from speech_context import correct
from command_voice import CommandVoice
from grid_input import keyboard_command
from hybrid_speech import HybridRecognizer
from grid_test_support import FakeMouse
from smart_grid import AdaptiveGrid
from test_smart_grid import row
from file_control import resolve_file

def directory():
    c=Catalog.__new__(Catalog);c.aliases=dict(ALIASES)
    c.entries=[{'name':'Microsoft Store','kind':'app','target':'Microsoft.WindowsStore_8wekyb3d8bbwe!App'},
               {'name':'Notepad','kind':'app','target':'Microsoft.WindowsNotepad_8wekyb3d8bbwe!App'}]
    return c

def heard(text,confidence=1):
    return {'text':text,'confidence':confidence,'words':[{'word':word,'probability':confidence} for word in text.split()]}

class CommandRoutingBoundaryTests(unittest.TestCase):
    def test_store_never_matches_notepad_or_a_store_browser_page(self):
        wrong=[dict(hwnd=1,title='Notes - Notepad',app='Notepad',process='Notepad',app_id='Microsoft.WindowsNotepad_8wekyb3d8bbwe!App'),
               dict(hwnd=2,title='Microsoft Store - Google Chrome',process='chrome',app='chrome')]
        for query in ('store','Microsoft Store','ms store'):
            with self.assertRaises(NoRunningWindow):match_window(wrong,query,directory())
        store=dict(hwnd=3,title='Untitled',process='ApplicationFrameHost',app_id='Microsoft.WindowsStore_8wekyb3d8bbwe!App')
        self.assertEqual(match_window(wrong+[store],'store',directory())['hwnd'],3)

    def test_open_launches_store_if_only_notepad_is_running(self):
        c=directory();c.launch=Mock(return_value='Microsoft Store')
        target={'hwnd':3,'title':'Microsoft Store'}
        with patch('window_commands.switch_to',side_effect=[NoRunningWindow('No Store'),target]) as switch:
            self.assertEqual(open_and_activate('store',c,None,threading.Event()),(target,True))
        c.launch.assert_called_once_with('store');self.assertEqual(switch.call_args.args[0],'Microsoft Store')

    def test_spaced_on_and_nato_labels_are_the_same_visible_target(self):
        ctx={'grid_active':True,'labels':['FH','AF'],'office':''}
        for text in ('click on f h','click FH','click on eff hotel','press f h','select f h'):
            result=correct(text,ctx);self.assertEqual(result.code,'FH',text);self.assertFalse(result.review,text)
        self.assertEqual(correct('scroll down from f h',ctx).text,'scroll down from FH')
        self.assertEqual(correct('drag f h to a f',ctx).text,'drag FH to AF')
        self.assertEqual(correct('close tab f h',ctx).text,'close tab FH')
        self.assertEqual(correct('click on f h then click on a f',ctx).text,'click FH then click AF')
        self.assertEqual(correct('press win',ctx).text,'press win')

    def test_logged_label_confidence_uses_code_gate_not_named_app_gate(self):
        packet=heard('click on f h',.89562775);packet['words'][-1]['probability']=.582511
        result=CommandVoice({'handsfree':True}).route(packet,{'grid_active':True,'labels':['FH'],'busy':False})
        self.assertEqual((result['kind'],result['text'],result['code']),('command','click FH','FH'))
        packet['words'][-1]['probability']=.2
        self.assertEqual(CommandVoice({'handsfree':True}).route(packet,{'grid_active':True,'labels':['FH']})['kind'],'review')

    def test_actual_grid_dispatch_spaced_labels_clicks_without_a_name_lookup(self):
        rows=[row()];grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:rows)
        try:
            grid.run('open grid')
            with grid.lock:
                target=grid.grid.targets.pop('A');target['label']='FH';grid.grid.targets['FH']=target;grid.grid.labels[target['key']]='FH'
            for text in ('click on f h','press f h','select f h'):
                grid.run(text);self.assertEqual(grid.mouse.events[-1][0],'click',text)
        finally:grid.close()

    def test_excel_bypass_only_applies_in_excel_and_keyboard_chords_stay_keyboard(self):
        excel={'class_name':'XLMAIN','title':'Book1 - Excel'}
        chrome={'class_name':'Chrome_WidgetWin_1','title':'Page - Google Chrome'}
        self.assertTrue(keyboard_command('click A1',excel))
        self.assertTrue(keyboard_command('click on cell A1',excel))
        self.assertFalse(keyboard_command('click A1',chrome))
        self.assertFalse(keyboard_command('press f h',chrome))
        self.assertTrue(keyboard_command('press ctrl a',chrome));self.assertTrue(keyboard_command('press f5',chrome))
        self.assertFalse(keyboard_command('click on FH',excel))
        self.assertEqual(correct('make text bold',{'office':'excel'}).text,'make text bold')
        self.assertFalse(correct('make text bold',{'office':'excel'}).review)

    def test_compact_decoder_cannot_replace_targets_from_shared_verbs(self):
        for a,b in [('open youtube','open new tab'),('open reddit','open grid'),('copy it','paste it'),('dictation on','dictation off')]:
            primary=heard(a,.88);self.assertEqual(HybridRecognizer.prefer_control(primary,heard(b)),primary)
        self.assertEqual(HybridRecognizer.prefer_control(heard('start nation',.6),heard('start dictation'))['text'],'start dictation')

    def test_short_misheard_name_does_not_open_a_long_unrelated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'Assignment_1_GitHub_Issues_CLO3_Marks_20.pptx').touch()
            self.assertIsNone(resolve_file('git',[[root]])[0])
            (root/'red.jpg').touch();self.assertEqual(resolve_file('red',[[root]])[0],root/'red.jpg')

    def test_misheard_website_suffix_does_not_navigate(self):
        voice=CommandVoice({'handsfree':True})
        self.assertEqual(voice.route(heard('open you tube dot gwen'))['kind'],'review')
        self.assertEqual(voice.route(heard('open youtube dot com'))['kind'],'command')

if __name__=='__main__':unittest.main()

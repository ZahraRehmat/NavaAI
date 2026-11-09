import unittest
from unittest.mock import Mock,patch
from direct_commands import parse_direct
from command_voice import CommandVoice
from dictation_queue import DictationQueue
from text_input import span_offsets,spaced_text,FocusedText


class VoiceTypingTests(unittest.TestCase):
    def test_natural_clipboard_commands_and_keys(self):
        for text in ('paste','paste the thing','paste the stuff','paste the copied data','paste it','paste the clipboard content'):
            self.assertEqual(parse_direct(text),{'kind':'keys','keys':['ctrl','v']})
        for text in ('copy it','copy the selected text','copy this'):
            self.assertEqual(parse_direct(text)['keys'],['ctrl','c'])
        for text in ('press enter','press the enter key','hit return','enter','new line'):
            self.assertEqual(parse_direct(text)['keys'],['enter'])
        self.assertEqual(parse_direct('select all text')['keys'],['ctrl','a'])
        self.assertEqual(parse_direct('cut it')['keys'],['ctrl','x'])
        self.assertEqual(parse_direct('type paste the thing')['text'],'paste the thing')

    def test_grid_passes_text_commands_to_editor(self):
        from smart_grid import AdaptiveGrid
        from grid_test_support import FakeMouse
        grid=AdaptiveGrid(FakeMouse(),lambda:[(0,0,800,600)],observer=lambda:[])
        try:
            grid.run('open grid')
            for text in ('select from father to sun','copy it','paste the copied data','press the enter key','increase font','decrease font','type hello'):
                self.assertIsNone(grid.run(text),text)
        finally:grid.close()

    def test_editing_commands_work_during_dictation_and_literal_escape(self):
        for grid in (False,True):
            session=CommandVoice({'handsfree':True});session.dictating=True
            for phrase in ('press enter','select from father to sun','copy it','paste the stuff','increase font'):
                result=session.route({'text':phrase,'confidence':.99},{'grid_active':grid})
                self.assertEqual(result['text'],phrase);self.assertTrue(result['dictation_input'])
            self.assertEqual(session.route({'text':'type press enter','confidence':1})['text'],'type press enter')
            self.assertEqual(session.route({'text':'some ordinary words','confidence':1})['text'],'type some ordinary words')

    def test_spacing_from_real_caret_and_selection(self):
        for previous,payload,expected in [('hello','world',' world'),('hello ','world','world'),('hello\n','world','world'),('hello',', there',', there'),('(', 'hello','hello'),('', 'hello','hello')]:
            self.assertEqual(spaced_text(payload,previous),expected)
        self.assertEqual(spaced_text('replacement','previous',selected=True),'replacement')

    def test_selection_inclusive_whitespace_case_and_ambiguity(self):
        text='My Father  walks towards the SUN every day.'
        a,b=span_offsets(text,'father','sun');self.assertEqual(text[a:b],'Father  walks towards the SUN')
        self.assertEqual(span_offsets(text,'father','son'),(a,b))
        with self.assertRaises(ValueError):span_offsets('father sun father sun','father','sun')
        with self.assertRaises(ValueError):span_offsets('grandfather sunlight','father','sun')

    def test_queue_preserves_order_cancels_on_target_change_and_bounds(self):
        context={'interaction':{'hwnd':1,'pid':2}};queue=DictationQueue(limit=2)
        self.assertTrue(queue.push('type first',context,3));self.assertTrue(queue.push('press enter',context,3))
        self.assertFalse(queue.push('type overflow',context,3))
        self.assertEqual(queue.pop(context,3)[0],'type first')
        with self.assertRaises(ValueError):queue.pop({'interaction':{'hwnd':4,'pid':2}},3)
        self.assertFalse(queue.items)
        queue.push('type old',context,3)
        with self.assertRaises(ValueError):queue.pop(context,4)

    def test_text_selection_checks_focus_before_mutating(self):
        access=FocusedText.__new__(FocusedText);access.target={'hwnd':1};access.win=Mock();access.win.foreground.return_value=2
        access.pattern=Mock()
        with self.assertRaises(ValueError):access.select('father','sun')
        access.pattern.DocumentRange.FindText.assert_not_called()

    def test_hybrid_uses_english_for_prose_and_vosk_for_codes(self):
        from hybrid_speech import HybridRecognizer
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        recognizer.commands.transcribe_result.return_value={'text':'click eff gee','confidence':1}
        recognizer.english.transcribe_result.return_value={'text':'Hello world.','confidence':.98}
        result=recognizer.transcribe_result([],{'grid_active':True,'labels':['FG']})
        self.assertEqual(result['text'],'click eff gee');recognizer.english.transcribe_result.assert_not_called()
        recognizer.commands.transcribe_result.return_value={'text':'ordinary spoken text','confidence':1}
        self.assertEqual(recognizer.transcribe_result([],{'dictation':True})['text'],'Hello world.')
        recognizer.commands.transcribe_result.return_value={'text':'[unk]','confidence':.1}
        recognizer.english.reset_mock()
        self.assertEqual(recognizer.transcribe_result([],{})['text'],'[unk]')
        recognizer.english.transcribe_result.assert_not_called()

    def test_commands_and_power_do_not_wait_for_or_use_whisper(self):
        from hybrid_speech import HybridRecognizer
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        recognizer.english.transcribe_result.side_effect=AssertionError('Whisper must not replace a recognized command')
        for text,context in [('gwen turn off',{}),('gwen turn on',{'assistant_active':False}),('gwen listen open word',{}),('grid off',{}),('press enter',{'dictation':True}),('stop dictation',{'dictation':True}),('open word',{})]:
            recognizer.commands.transcribe_result.return_value={'text':text,'confidence':1}
            self.assertEqual(recognizer.transcribe_result([],context)['text'],text)
        recognizer.english.transcribe_result.assert_not_called()

    def test_unicode_packets_preserve_surrogates_and_keyup(self):
        import ctypes
        from unicode_keyboard import packets,Input
        events=list(packets('A\U0001f600'))
        self.assertEqual(len(events),6)
        self.assertEqual([e.payload.keyboard.flags for e in events],[4,6,4,6,4,6])
        self.assertEqual([e.payload.keyboard.scan for e in events[::2]],[65,0xd83d,0xde00])
        self.assertEqual(ctypes.sizeof(Input),40 if ctypes.sizeof(ctypes.c_void_p)==8 else 28)

    def test_consensus_does_not_raise_confidence_for_different_keys(self):
        from hybrid_speech import HybridRecognizer
        result={'text':'press enter','confidence':.4}
        HybridRecognizer.consensus({'text':'press delete','confidence':1},result)
        self.assertEqual(result['confidence'],.4)
        HybridRecognizer.consensus({'text':'press enter','confidence':1},result)
        self.assertEqual(result['confidence'],1)

    def test_owned_headless_browser_caret_spacing_and_selection(self):
        from playwright.sync_api import sync_playwright
        from text_input import browser_type,browser_select
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page();page.set_content('<textarea id="t"></textarea><div id="d" contenteditable="true"></div>')
                for selector in ('#t','#d'):
                    page.locator(selector).focus()
                    browser_type(page,'My father');browser_type(page,'walks towards the sun')
                    text=page.locator(selector).evaluate("e=>typeof e.value==='string'?e.value:e.textContent")
                    self.assertEqual(text,'My father walks towards the sun')
                    browser_select(page,'father','sun')
                    browser_type(page,'mother')
                    text=page.locator(selector).evaluate("e=>typeof e.value==='string'?e.value:e.textContent")
                    self.assertEqual(text,'My mother')
            finally:browser.close()


if __name__=='__main__':unittest.main()

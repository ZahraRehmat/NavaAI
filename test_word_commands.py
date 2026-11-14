import unittest
from unittest.mock import Mock,patch
from direct_commands import parse_direct
from text_input import span_offsets,SelectionResolutionError,browser_select,native_word


class WordCommands(unittest.TestCase):
    def test_named_word_edges_and_relative_caret_movement(self):
        for phrase in ('move cursor to end of word work','move cursor to the end of word work','move cursor after word work'):
            self.assertEqual(parse_direct(phrase),{'kind':'word_action','action':'move_end','word':'work'})
        for phrase in ('move cursor before word work','move cursor to start of word work'):
            self.assertEqual(parse_direct(phrase),{'kind':'word_action','action':'move','word':'work'})
        for phrase,keys in [('move cursor forward',['right']),('move cursor backward',['left']),
                            ('move cursor forward a word',['ctrl','right']),('move cursor backward a word',['ctrl','left'])]:
            self.assertEqual(parse_direct(phrase),{'kind':'keys','keys':keys})

    def test_logged_tool_and_weak_preposition_keep_target_validation(self):
        from word_commands import recover_word_packet,word_intent
        primary={'text':'move cursor tool shell'}
        words=[{'word':w,'probability':p} for w,p in [('move',1),('cursor',1),('to',.583157),('shell',1)]]
        heard={'text':'move cursor to shell','confidence':.89578925,'words':words}
        self.assertEqual(word_intent(primary['text']),'move')
        result=recover_word_packet(primary,heard)
        self.assertEqual(result['text'],'move cursor to shell')
        self.assertIsNone(parse_direct(primary['text'])) # Never change tool into to by script.
        words[-1]['probability']=.4
        self.assertIs(recover_word_packet(primary,heard),primary)

    def test_unclear_word_only_uses_bounded_english_recovery(self):
        from hybrid_speech import HybridRecognizer
        recognizer=HybridRecognizer.__new__(HybridRecognizer);recognizer.commands=Mock();recognizer.english=Mock()
        original={'text':'select word wac','confidence':.91,'word_target_unclear':True}
        recognizer.commands.transcribe_result.return_value=original
        recognizer.english.transcribe_result.return_value={'text':'Select word work.','confidence':.95,
            'words':[{'word':w,'probability':.95} for w in ('Select','word','work.')]}
        result=recognizer.transcribe_result([],{'assistant_active':True})
        self.assertEqual(parse_direct(result['text'])['word'],'work')
        self.assertEqual(result['backend'],'whisper-word')
        self.assertTrue(recognizer.english.transcribe_result.call_args.args[1]['word_command'])
        recognizer.english.transcribe_result.return_value={'text':'Erase word work.','confidence':.95,
            'words':[{'word':w,'probability':.95} for w in ('Erase','word','work.')]}
        result=recognizer.transcribe_result([],{'assistant_active':True})
        self.assertTrue(result['word_target_unclear'])
        self.assertEqual(result['text'],original['text'])

    def test_logged_work_word_error_uses_open_vocabulary_without_substitution(self):
        from word_commands import recover_word_packet
        def packet(text,p=1):return {'text':text,'confidence':p,'words':[{'word':w,'probability':p} for w in text.split()]}
        for primary,spoken in [('select word word','select word work'),('move cursor to word','move cursor to work')]:
            result=recover_word_packet(packet(primary),packet(spoken))
            self.assertEqual(parse_direct(result['text'])['word'],'work')
            self.assertEqual(result['primary_text'],primary)
        original=packet('select word word')
        for candidate in (packet('erase word work'),packet('select word work',.4),packet('select word')):
            self.assertEqual(recover_word_packet(original,candidate),original)
        self.assertEqual(parse_direct('move cursor to end of line'),{'kind':'keys','keys':['end']})
        from command_voice import CommandVoice
        for mode in ('normal','selection','dictation'):
            voice=CommandVoice({'handsfree':True});voice.selecting=mode=='selection';voice.dictating=mode=='dictation'
            self.assertEqual(voice.route({**packet('select word word'),'word_target_unclear':True})['kind'],'review')
        for phrase in ('select word','move cursor to word','erase word'):
            result=CommandVoice({'handsfree':True}).route(packet(phrase))
            self.assertEqual(result['kind'],'review');self.assertIn('Which word',result['reason'])

    def test_voice_and_grid_modes_preserve_word_payload(self):
        from command_voice import CommandVoice
        from grid_input import keyboard_command
        from speech_context import correct
        cases={'move cursor to word "tits"':'move', 'erase word "tits"':'erase',
               'select word "tits"':'select','delete the word Karachi':'erase'}
        for phrase,action in cases.items():
            parsed=parse_direct(phrase)
            self.assertEqual(parsed['action'],action)
            self.assertTrue(keyboard_command(phrase))
            self.assertEqual(correct(phrase,{'office':'excel','grid_active':True,'labels':['A']}).text,phrase)
            for mode in ('normal','selection','dictation'):
                voice=CommandVoice({'handsfree':True});voice.selecting=mode=='selection';voice.dictating=mode=='dictation'
                result=voice.route({'text':phrase,'confidence':1},{'grid_active':True,'labels':['A']})
                self.assertEqual(result['kind'],'command')
                self.assertEqual(parse_direct(result['text']),parsed)
        self.assertEqual(parse_direct('type select word Karachi')['kind'],'type')

    def test_repeated_word_asks_once_and_never_selects_between_occurrences(self):
        text='Sun sunshine\nSUN and sun.';choices=Mock(return_value=1)
        left,right=span_offsets(text,'sun','sun',single=True,chooser=choices)
        self.assertEqual(text[left:right],'SUN');self.assertEqual(left,13)
        choices.assert_called_once()
        self.assertEqual(len(choices.call_args.args[1]),3)
        self.assertEqual(span_offsets(text,'last sun','last sun',single=True),(21,24))
        with self.assertRaises(ValueError):span_offsets('Karachi','karachii','karachii',single=True)
        with self.assertRaises(SelectionResolutionError):span_offsets(text,'sun','sun',single=True,chooser=lambda *a:None)

    def test_native_word_move_erase_and_readonly_guard(self):
        from selection_test_support import TextRange
        target={'hwnd':1,'pid':2,'bounds':(0,0,500,500)}
        region=TextRange('hello sun goodbye sun')
        access=Mock();access.pattern.DocumentRange=region
        ranges=access.pattern.GetSelection.return_value;ranges.Length=1
        def selected(left,right):ranges.GetElement.return_value=TextRange(region.text,left,right)
        region.selected.side_effect=selected
        with patch('text_input.FocusedText',return_value=access),patch('desktop_control.act') as keys,patch.object(TextRange,'GetAttributeValue',return_value=False,create=True):
            native_word(target,'sun','move',chooser=lambda *a:1)
            region.selected.assert_called_with(18,18);keys.assert_not_called()
            native_word(target,'sun','move_end',chooser=lambda *a:1)
            region.selected.assert_called_with(21,21);keys.assert_not_called()
            native_word(target,'sun','erase',chooser=lambda *a:0)
            keys.assert_called_once_with({'action':'hotkey','keys':['backspace']},bounds=target['bounds'])
            keys.reset_mock()
            with patch.object(TextRange,'GetAttributeValue',return_value=True,create=True):
                with self.assertRaises(SelectionResolutionError):native_word(target,'sun','erase',chooser=lambda *a:0)
            keys.assert_not_called()

    def test_owned_browser_word_actions_and_readonly_selection(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page();page.set_content('<textarea>hello sun\nhello sun</textarea><p>hello moon and moon</p>')
                field=page.locator('textarea');field.focus()
                choices=Mock(return_value=1)
                browser_select(page,'sun','sun',single=True,word_action='move',chooser=choices)
                self.assertEqual(field.evaluate('e=>[e.selectionStart,e.selectionEnd]'),[16,16])
                choices.assert_called_once()
                browser_select(page,'sun','sun',single=True,word_action='move_end',chooser=lambda *a:1)
                self.assertEqual(field.evaluate('e=>[e.selectionStart,e.selectionEnd]'),[19,19])
                browser_select(page,'sun','sun',single=True,word_action='select',chooser=lambda *a:0)
                self.assertEqual(field.evaluate('e=>e.value.slice(e.selectionStart,e.selectionEnd)'),'sun')
                browser_select(page,'sun','sun',single=True,word_action='erase',chooser=lambda *a:1)
                self.assertEqual(field.input_value(),'hello sun\nhello ')
                field.evaluate('e=>e.readOnly=true')
                with self.assertRaises(SelectionResolutionError):browser_select(page,'sun','sun',single=True,word_action='erase')
                self.assertEqual(field.input_value(),'hello sun\nhello ')
                browser_select(page,'moon','moon',single=True,word_action='select',chooser=lambda *a:1)
                self.assertEqual(page.evaluate('getSelection().toString()'),'moon')
                field.evaluate('e=>e.readOnly=false');field.fill('sun and sun');before=field.input_value()
                with self.assertRaises(SelectionResolutionError):browser_select(page,'sun','sun',single=True,word_action='erase',chooser=lambda *a:None)
                self.assertEqual(field.input_value(),before)
                def changed(*args):field.fill('changed');return 0
                with self.assertRaises(Exception):browser_select(page,'sun','sun',single=True,word_action='erase',chooser=changed)
                self.assertEqual(field.input_value(),'changed')
            finally:browser.close()


if __name__=='__main__':unittest.main()

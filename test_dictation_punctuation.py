import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from command_voice import CommandVoice
from direct_commands import parse_direct
from dictation_punctuation import raw_dictation,engine,edits,significant


class PunctuationTests(unittest.TestCase):
    def test_raw_dictation_does_not_insert_sentence_marks(self):
        session=CommandVoice({'handsfree':True});session.dictating=True
        self.assertEqual(session.route({'text':'Hello. I am fine, thank you.','confidence':1})['text'],'type Hello I am fine thank you')
        self.assertEqual(raw_dictation('Value 3.14. Visit https://example.com.'),'Value 3.14 Visit https://example.com')
        self.assertEqual(raw_dictation("I don't know. Email a@example.com."),"I don't know Email a@example.com")
        self.assertEqual(raw_dictation('The U.S. is large.'),'The U.S. is large')

    def test_commands_in_all_modes_and_grid_keyboard_passthrough(self):
        from grid_input import keyboard_command
        for mode in ('normal','dictation','selection'):
            session=CommandVoice({'handsfree':True});session.dictating=mode=='dictation';session.selecting=mode=='selection'
            for phrase,keys in [('copy it',['ctrl','c']),('paste the copied data',['ctrl','v']),('paste here',['ctrl','v']),('paste it to this field',['ctrl','v']),('copy it to clipboard',['ctrl','c']),('erase it',['ctrl','backspace']),('backspace',['ctrl','backspace']),('press backspace',['backspace'])]:
                result=session.route({'text':phrase,'confidence':1},{'grid_active':True})
                self.assertEqual(result['kind'],'command',(mode,phrase,result));self.assertEqual(parse_direct(result['text'])['keys'],keys)
                self.assertTrue(keyboard_command(phrase))
            result=session.route({'text':'punctuate it','confidence':1},{'grid_active':True})
            self.assertEqual(result['kind'],'command');self.assertEqual(parse_direct(result['text'])['kind'],'punctuate')
            self.assertTrue(keyboard_command('punctuate it'))
        self.assertEqual(parse_direct('type erase it')['kind'],'type')

    def test_real_offline_model_punctuation_quotes_and_paragraphs(self):
        source='hello how are you i am fine thank you'
        restored=engine().restore(source)
        self.assertEqual(restored,'Hello, how are you? I am fine, thank you.')
        self.assertEqual(significant(restored),significant(source))
        self.assertEqual(engine().restore('he said hello how are you'),'He said, "Hello, how are you?"')
        self.assertEqual(engine().restore('he said open quote hello how are you close quote'),'He said, "Hello, how are you?"')
        self.assertEqual(engine().restore('hello\rthis is another paragraph\r').count('\r'),2)
        self.assertIn('3.14',engine().restore('the value is 3.14 and the price is 25.50'))

    def test_word_rewriting_is_rejected(self):
        with self.assertRaises(ValueError):edits('hello world','Hello, everyone.')

    def test_word_edits_are_minimal_and_in_one_undo_record(self):
        from punctuation_edit import office_punctuation,u16
        class Document:
            text='hello world\r'
            def __init__(self):self.calls=[]
            def Range(self,a,b):self.calls.append((a,b));return Range(self,a,b)
        class Range:
            def __init__(self,doc,a,b):self.doc=doc;self.Start=a;self.End=b
            @property
            def Duplicate(self):return Range(self.doc,self.Start,self.End)
            @property
            def Text(self):return self.doc.text.encode('utf-16-le')[self.Start*2:self.End*2].decode('utf-16-le')
            @Text.setter
            def Text(self,value):
                data=self.doc.text.encode('utf-16-le');self.doc.text=(data[:self.Start*2]+value.encode('utf-16-le')+data[self.End*2:]).decode('utf-16-le')
        document=Document();document.Content=Range(document,0,u16(document.text))
        app=SimpleNamespace(ActiveDocument=document,Selection=SimpleNamespace(Range=Range(document,0,0)),UndoRecord=Mock())
        with patch('punctuation_edit.engine') as model:
            model.return_value.restore.return_value='Hello, world.\r'
            office_punctuation(app,'word')
        self.assertEqual(document.text,'Hello, world.\r');self.assertTrue(all(b-a<=1 for a,b in document.calls))
        app.UndoRecord.StartCustomRecord.assert_called_once();app.UndoRecord.EndCustomRecord.assert_called_once()

    def test_browser_editing_updates_focused_field_and_preserves_bold(self):
        from playwright.sync_api import sync_playwright
        from punctuation_edit import browser_punctuation
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page();page.set_content('<textarea id="t">hello how are you</textarea><div id="d" contenteditable="true"><b>hello</b> world</div>')
                page.locator('#t').focus();browser_punctuation(page)
                self.assertEqual(page.locator('#t').input_value(),'Hello, how are you?')
                page.locator('#d').focus();browser_punctuation(page)
                self.assertEqual(page.locator('#d').inner_text(),'Hello, world.')
                self.assertTrue(page.locator('#d b').inner_text().startswith('Hello'))
                page.set_content('<textarea id="s">prefix hello suffix</textarea>')
                page.locator('#s').focus();page.locator('#s').evaluate('e=>e.setSelectionRange(7,12)')
                browser_punctuation(page)
                self.assertEqual(page.locator('#s').input_value(),'prefix Hello. suffix')
                page.set_content('<textarea id="r" readonly>leave this alone</textarea>');page.locator('#r').focus()
                with self.assertRaises(Exception):browser_punctuation(page)
                self.assertEqual(page.locator('#r').input_value(),'leave this alone')
            finally:browser.close()


if __name__=='__main__':unittest.main()

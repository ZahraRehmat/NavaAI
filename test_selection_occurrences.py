import unittest
from unittest.mock import Mock, patch
from text_input import span_offsets, native_span, FocusedText, SelectionResolutionError, browser_select
from direct_commands import parse_direct
from command_voice import CommandVoice


class OccurrenceTests(unittest.TestCase):
    def test_explicit_occurrences_and_literal_ordinal_phrase(self):
        text='father one sun. father two sun. father three sun.'
        a,b=span_offsets(text,'second father','second sun')
        self.assertEqual(text[a:b],'father two sun')
        a,b=span_offsets(text,'last father','last sun')
        self.assertEqual(text[a:b],'father three sun')
        self.assertEqual(span_offsets('first day ends today','first day','today'),(0,20))
        self.assertEqual(span_offsets(text,'father occurrence 2','the second occurrence of sun'),(16,30))

    def test_both_endpoints_offer_context_not_just_nearest_end(self):
        text='father one sun. father two sun.'
        chooser=Mock(side_effect=[0,1])
        a,b=span_offsets(text,'father','sun',chooser)
        self.assertEqual(text[a:b],text[:-1])
        self.assertEqual(chooser.call_count,2)
        self.assertIn('[father]',chooser.call_args_list[0].args[1][0]['label'])
        self.assertIn('character',chooser.call_args_list[0].args[1][1]['detail'])

    def test_choices_only_include_valid_forward_ranges(self):
        chooser=Mock(return_value=1)
        text='sun before father first sun then sun'
        a,b=span_offsets(text,'father','sun',chooser)
        self.assertEqual(text[a:b],'father first sun then sun')
        self.assertEqual(len(chooser.call_args.args[1]),2)

    def test_cancel_invalid_and_missing_occurrence_never_guess(self):
        for chooser in (None,Mock(return_value=None),Mock(return_value=99)):
            with self.assertRaises(SelectionResolutionError):span_offsets('father sun father sun','father','sun',chooser)
        with self.assertRaises(SelectionResolutionError):span_offsets('father sun','third father','sun')

    def test_all_occurrences_reachable_through_paging(self):
        text=('father sun. '*30).strip()
        chooser=Mock(side_effect=[24,5])
        a,b=span_offsets(text,'father','last sun',chooser)
        self.assertEqual(a,text.rindex('father'))
        self.assertLessEqual(len(chooser.call_args_list[0].args[1]),26)

    def test_native_range_is_anchored_to_second_identical_passage(self):
        from selection_test_support import TextRange
        text='father sun. father sun.';region=TextRange(text)
        chosen=native_span(region,text,12,22)
        self.assertEqual(chosen.GetText(100001),'father sun')
        self.assertEqual((chosen.left,chosen.right),(12,22))

    def test_inexact_chromium_findtext_is_never_used_to_guess_offsets(self):
        from selection_test_support import TextRange
        text='Heading\nBring this text across paragraphs\nmarkers'
        region=TextRange(text)
        result=native_span(region,text,8,len(text))
        self.assertEqual(result.GetText(100001),text[8:])

    def test_cancel_and_text_change_do_not_select_or_copy(self):
        access=FocusedText.__new__(FocusedText);access.check=Mock();access.pattern=Mock()
        document=access.pattern.DocumentRange
        document.GetText.return_value='father sun father sun'
        with patch('text_input.copy_selected') as copied:
            with self.assertRaises(SelectionResolutionError):access.select('father','sun',copy=True,chooser=lambda *a:None)
            document.FindText.return_value.Select.assert_not_called();copied.assert_not_called()
            document.FindText.reset_mock()
            document.GetText.side_effect=['father sun father sun','changed text']
            with self.assertRaisesRegex(ValueError,'text changed'):access.select('first father','last sun',copy=True)
            document.FindText.assert_not_called();copied.assert_not_called()

    def test_native_choices_carry_real_word_rectangles(self):
        from text_input import native_locator
        from selection_test_support import TextRange
        text='father sun father sun';region=TextRange(text)
        region.rectangles=lambda left,right:(10,20,50,18) if left==0 else (80,20,50,18)
        chooser=Mock(return_value=1)
        left,right=span_offsets(text,'father','last sun',chooser,locate=native_locator(region,text))
        options=chooser.call_args.args[1]
        self.assertEqual(options[0]['bounds'],[10,20,60,38])
        self.assertEqual(options[1]['bounds'],[80,20,130,38])
        self.assertEqual(options[1]['selection_role'],'start')
        self.assertEqual(left,11)

    def test_missing_or_invalid_native_geometry_is_not_guessed(self):
        from text_input import native_locator
        from selection_test_support import TextRange
        region=TextRange('father')
        for rect in ([],[float('nan'),1,2,3],[1,2,0,4]):
            region.rectangles=lambda left,right:rect
            self.assertIsNone(native_locator(region,'father')(0,6))

    def test_voice_and_direct_routes_preserve_ordinal_words(self):
        session=CommandVoice({'handsfree':True});session.selecting=True
        result=session.route({'text':'from second father to last sun','confidence':1})
        command=parse_direct(result['text'])
        self.assertEqual(command['start'],'second father');self.assertEqual(command['end'],'last sun')
        self.assertEqual(parse_direct('select from second father to last sun')['start'],'second father')

    def test_browser_uses_chosen_offsets_and_utf16(self):
        page=Mock();handle=page.evaluate_handle.return_value
        handle.evaluate.return_value='😀 father sun father sun'
        browser_select(page,'last father','last sun')
        payload=handle.evaluate.call_args.args[1]
        self.assertEqual((payload['left'],payload['right']),(14,24))

    def test_real_browser_selects_second_identical_span_and_chosen_end(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page()
                page.set_content('<textarea id="t"></textarea><div id="d" contenteditable="true"></div>')
                text='😀 father sun. father sun.'
                for selector in ('#t','#d'):
                    field=page.locator(selector)
                    field.evaluate("(e,t)=>{if(e.tagName==='TEXTAREA')e.value=t;else e.textContent=t}",text)
                    field.focus()
                    browser_select(page,'last father','last sun')
                    page.keyboard.insert_text('SECOND')
                    self.assertEqual(field.evaluate("e=>e.value??e.textContent"),'😀 father sun. SECOND.')
                    field.evaluate("(e,t)=>{if(e.tagName==='TEXTAREA')e.value=t;else e.textContent=t}",text)
                    field.focus()
                    browser_select(page,'first father','sun',chooser=lambda *args:1)
                    page.keyboard.insert_text('WHOLE')
                    self.assertEqual(field.evaluate("e=>e.value??e.textContent"),'😀 WHOLE.')
            finally:browser.close()


if __name__=='__main__':unittest.main()

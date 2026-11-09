import unittest
from unittest.mock import Mock,patch
from text_input import browser_select,select_screen_text,SelectionResolutionError


class ReadonlySelectionTests(unittest.TestCase):
    def test_native_readonly_text_in_embedded_renderer_can_select_and_copy(self):
        # The renderer PID differs from the app window; readonly Text controls
        # may expose TextPattern even though they aren't Edit/Document controls.
        el=Mock();el.CurrentIsOffscreen=False;el.CurrentIsPassword=False
        el.CurrentProcessId=99;el.CurrentControlType=50020;el.GetRuntimeId.return_value=[1,2]
        uia=Mock();uia.ElementFromHandle.return_value=el
        uia.ControlViewWalker.GetFirstChildElement.return_value=None
        pattern=el.GetCurrentPattern.return_value.QueryInterface.return_value
        pattern.SupportedTextSelection=1;pattern.GetVisibleRanges.return_value.Length=1
        from selection_test_support import TextRange
        region=TextRange('Welcome Islamabad via Lahore to Karachi today')
        pattern.GetVisibleRanges.return_value.GetElement.return_value=region
        with patch('text_input.FocusedText',side_effect=ValueError('No typing field')),patch('pywinauto.uia_defines.IUIA') as api,patch('windows_api.foreground',return_value=1),patch('text_input.copy_selected') as copied:
            api.return_value.iuia=uia
            select_screen_text({'hwnd':1,'pid':2},'Islamabad','Karachi',copy=True)
            copied.assert_called_once_with('Islamabad via Lahore to Karachi')
            region.selected.assert_called_once()

    def test_native_matching_document_does_not_duplicate_nested_text_providers(self):
        el=Mock();el.CurrentIsOffscreen=False;el.CurrentIsPassword=False;el.CurrentControlType=50030;el.GetRuntimeId.return_value=[1]
        pattern=el.GetCurrentPattern.return_value.QueryInterface.return_value
        pattern.SupportedTextSelection=1;pattern.GetVisibleRanges.return_value.Length=1
        from selection_test_support import TextRange
        pattern.GetVisibleRanges.return_value.GetElement.return_value=TextRange('father sun')
        with patch('text_input.FocusedText',side_effect=ValueError()),patch('pywinauto.uia_defines.IUIA') as api,patch('windows_api.foreground',return_value=1):
            api.return_value.iuia.ElementFromHandle.return_value=el
            select_screen_text({'hwnd':1,'pid':2},'father','sun')
            api.return_value.iuia.ControlViewWalker.GetFirstChildElement.assert_not_called()

    def test_real_browser_readonly_display_text_frames_and_guards(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page()
                page.set_content('''<textarea id="prompt"></textarea>
                  <main><p>Hello Islamabad <b>via Lahore</b> to Karachi.</p>
                  <p>father first sun. father second sun.</p></main>
                  <p hidden>hiddenStart hiddenEnd</p><p style="user-select:none">lockedStart lockedEnd</p>
                  <p style="position:absolute;top:20000px">offscreenStart offscreenEnd</p>''')
                page.locator('#prompt').focus()
                with patch('text_input.copy_selected') as copied:
                    browser_select(page,'Islamabad','Karachi',copy=True)
                    actual=page.evaluate('getSelection().toString()')
                    self.assertEqual(actual,'Islamabad via Lahore to Karachi')
                    copied.assert_called_once_with(actual)
                browser_select(page,'last father','last sun')
                self.assertEqual(page.evaluate('getSelection().toString()'),'father second sun')
                choices=Mock(side_effect=[0,1]);browser_select(page,'father','sun',chooser=choices)
                self.assertEqual(page.evaluate('getSelection().toString()'),'father first sun. father second sun')
                for start,end in [('hiddenStart','hiddenEnd'),('lockedStart','lockedEnd'),('offscreenStart','offscreenEnd')]:
                    with self.assertRaises(ValueError):browser_select(page,start,end)
                before=page.evaluate('getSelection().toString()')
                with patch('text_input.copy_selected') as copied:
                    with self.assertRaises(SelectionResolutionError):browser_select(page,'father','sun',copy=True,chooser=lambda *a:None)
                    copied.assert_not_called()
                self.assertEqual(page.evaluate('getSelection().toString()'),before)
                page.set_content('<iframe srcdoc="<p>Frame Islamabad to Karachi</p>"></iframe>')
                browser_select(page,'Islamabad','Karachi')
                self.assertEqual(page.frames[1].evaluate('getSelection().toString()'),'Islamabad to Karachi')
            finally:browser.close()

    def test_page_change_during_choice_does_not_copy(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            try:
                page=browser.new_page();page.set_content('<p>father sun father sun</p>')
                def choose(*args):
                    page.locator('p').inner_text()  # The chosen snapshot is live.
                    page.locator('p').evaluate("e=>e.textContent='changed'")
                    return 0
                with patch('text_input.copy_selected') as copied:
                    with self.assertRaises(Exception):browser_select(page,'father','sun',copy=True,chooser=choose)
                    copied.assert_not_called()
            finally:browser.close()


if __name__=='__main__':unittest.main()

import threading,unittest
from unittest.mock import Mock,patch
from browser_commands import intent
from native_media import skip_ad
from voice_controls import compact_phrases

CONTEXT={'hwnd':1,'title':'Video - YouTube - Google Chrome'}

class SkipAdTests(unittest.TestCase):
    def test_routing_and_literal_typing(self):
        for phrase in ('skip ad','skip this ad','skip the ad','skip ads','skip ad on youtube'):
            self.assertEqual(intent(phrase,True),{'action':'media_skip_ad','site':'youtube'})
        self.assertIn('skip this ad',compact_phrases())
        for phrase in ('type skip ad','skip ahead five seconds','skip this chapter'):
            self.assertNotEqual((intent(phrase,True) or {}).get('action'),'media_skip_ad')

    def test_click_available_button_once_and_confirm_disappearance(self):
        row={'element':Mock(),'name':'Skip ad'}
        with patch('native_media.check_active'),patch('native_media.skip_ad_controls',side_effect=[[row],[]]),patch('native_media.click_control') as click:
            self.assertIn('disappeared',skip_ad(CONTEXT,threading.Event()))
            click.assert_called_once_with(row,CONTEXT,unittest.mock.ANY)

    def test_unavailable_ambiguous_and_changed_target_do_not_click(self):
        for rows in ([],[{},{}]):
            with patch('native_media.check_active'),patch('native_media.skip_ad_controls',return_value=rows),patch('native_media.click_control') as click:
                if rows:
                    with self.assertRaisesRegex(ValueError,'Several'):skip_ad(CONTEXT,threading.Event())
                else:self.assertIn('not be skippable',skip_ad(CONTEXT,threading.Event()))
                click.assert_not_called()
        with patch('native_media.check_active',side_effect=ValueError('changed')),patch('native_media.click_control') as click:
            with self.assertRaisesRegex(ValueError,'changed'):skip_ad(CONTEXT,threading.Event())
            click.assert_not_called()

if __name__=='__main__':unittest.main()

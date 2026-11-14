import unittest
from taskbar_status import badge_position,badge_layout

class TaskbarPositionTests(unittest.TestCase):
    def test_fits_gap_without_covering_start_apps_or_tray(self):
        controls=[(0,1128,155,1200),(430,1128,1420,1200),(1640,1128,1920,1200)]
        x,y=badge_position((0,0,1920,1128),(0,1128,1920,1200),controls,184,68)
        self.assertGreaterEqual(y,1128);self.assertLessEqual(y+68,1200)
        self.assertTrue(all(x+184<=a or x>=c for a,b,c,d in controls))
    def test_expanded_weather_widget_shrinks_badge_into_remaining_taskbar_gap(self):
        occupied=[(9,1128,237,1200),(418,1128,1920,1200)]
        x,y,width,height=badge_layout((0,0,1920,1128),(0,1128,1920,1200),occupied,248,68)
        self.assertEqual(width,171)
        self.assertGreaterEqual(x,242);self.assertLessEqual(x+width,413)
        self.assertGreaterEqual(y,1128);self.assertLessEqual(y+height,1200)

    def test_full_or_hidden_taskbar_uses_bottom_work_area(self):
        for bar,controls in [((0,1128,1920,1200),[(0,1128,1920,1200)]),(None,[]),((0,1198,1920,1200),[])]:
            self.assertEqual(badge_position((0,0,1920,1128),bar,controls,184,68),(8,1054))
    def test_confirmation_panel_too_tall_stays_above_taskbar(self):
        self.assertEqual(badge_position((0,0,1920,1128),(0,1128,1920,1200),[],184,160),(8,962))

if __name__=='__main__':unittest.main()

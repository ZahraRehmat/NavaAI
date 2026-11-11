import unittest
from grid_scan_health import summarize,warning

class HealthTests(unittest.TestCase):
    def test_taskbar_only_is_reported_separately_from_scanning_failure(self):
        roots=[{'hwnd':1,'scope':'taskbar','kind':'Shell_TrayWnd'}, {'hwnd':2,'scope':'app','kind':'Notepad'}]
        rows=[{'hwnd':1,'scope':'taskbar'}]
        report=summarize(roots,rows,rows,[{'hwnd':2,'error':'Access denied'}])
        self.assertTrue(report['taskbar_only']);self.assertIn('Diagnose Grid.cmd',warning(report))
        self.assertEqual(report['roots'][1]['raw_targets'],0)
        self.assertEqual(report['errors'][0]['error'],'Access denied')

    def test_visibility_rejection_is_distinct_from_no_provider_controls(self):
        roots=[{'hwnd':1,'scope':'taskbar'},{'hwnd':2,'scope':'app'}]
        rows=[{'hwnd':1,'scope':'taskbar'},{'hwnd':2,'scope':'app','name':'Private document label'}]
        report=summarize(roots,rows,rows[:1])
        self.assertEqual(report['roots'][1]['raw_targets'],1)
        self.assertEqual(report['roots'][1]['visible_targets'],0)
        self.assertNotIn('Private document label',str(report))

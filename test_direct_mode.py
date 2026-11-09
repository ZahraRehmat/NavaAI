"""Runtime regressions: no planner import, inference, or screenshot fallback."""
import ast,subprocess,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
from agent import Agent
from browser_commands import intent


class DirectModeTests(unittest.TestCase):
    def test_agent_import_does_not_import_planner_or_openvino(self):
        result=subprocess.run([sys.executable,'-c',"import agent,sys; assert not any(k=='planner' or k.startswith('openvino') for k in sys.modules)"],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        tree=ast.parse(Path('agent.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):self.assertNotIn(node.module,('planner','openvino','openvino_genai'))

    def test_unknown_action_and_questions_return_without_screen_or_model(self):
        agent=Agent(log=lambda _:None)
        try:
            with patch('desktop_control.capture',side_effect=AssertionError('No visual planning')),patch('planner.Planner',side_effect=AssertionError('Qwen is removed')):
                for task in ('organize electrons into origami','what is on my screen?'):
                    before=time.monotonic();result=agent.run(task)
                    self.assertLess(time.monotonic()-before,1)
                    self.assertTrue('direct command' in result or 'computer commands' in result,result)
        finally:agent.close()

    def test_unknown_office_command_returns_without_inference(self):
        agent=Agent(log=lambda _:None)
        try:
            with patch('planner.Planner',side_effect=AssertionError('No Qwen')),patch('desktop_control.capture',side_effect=AssertionError('No screenshot')):
                result=agent.run('make the font mystical',interaction={'hwnd':99,'title':'Example - Word','class_name':'OpusApp','pid':7})
                self.assertIn('No direct command matched',result)
        finally:agent.close()

    def test_spoken_excel_reference_uses_native_tool(self):
        agent=Agent(log=lambda _:None)
        try:
            with patch('planner.Planner',side_effect=AssertionError('No Qwen')),patch.object(agent,'_focus_native'),patch('office_control.execute_office',return_value='Selected B1') as execute:
                self.assertEqual(agent.run('select b one',interaction={'hwnd':99,'title':'Book - Excel','class_name':'XLMAIN','pid':7}),'Selected B1')
                command=execute.call_args.args[1]
                self.assertIn('B1',str(command));self.assertNotIn('A1',str(command))
        finally:agent.close()

    def test_open_tab_never_falls_through_to_file_matching(self):
        self.assertEqual(intent('open tab'),{'action':'tab_new'})

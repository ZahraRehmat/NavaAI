import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock
import numpy as np
from PIL import Image
from planner import Planner,requested_point_action
from action_schema import schema_for

class PlannerInputTests(unittest.TestCase):
    def planner(self):
        p=Planner.__new__(Planner);p.config={};p.stop=threading.Event();p.gc=Mock()
        p.tokenizer=Mock();p.tokenizer.encode.return_value.input_ids=np.zeros((1,50))
        p._generate=Mock(side_effect=[Mock(texts=['{"action":"click","target":"FYP folder"}']),Mock(texts=['{"x":87,"y":552}'])])
        return p
    def test_visual_query_excludes_control_dump_and_preserves_detail(self):
        p=self.planner()
        with tempfile.TemporaryDirectory() as tmp:
            result=p.next('select FYP',{'native_controls':[{'id':123,'name':'confusing_dump_label'}]},Image.new('RGB',(1920,1200)),[],[],trace_dir=tmp)
            self.assertNotIn('confusing_dump_label',p.last_prompt)
            self.assertEqual(p.exposed_ids,set())
            self.assertEqual(p.last_input_size,[1920,1200])
            with Image.open(Path(tmp)/'model-input.png') as image:self.assertEqual(image.size,(1920,1200))
            trace=json.loads((Path(tmp)/'model-input.json').read_text())
            self.assertEqual(trace['prompt'],p._generate.call_args_list[0].args[0])
            self.assertEqual(json.loads((Path(tmp)/'model-output.txt').read_text()),result)
    def test_browser_still_receives_current_dom_ids(self):
        p=self.planner();p._generate=Mock(return_value=Mock(texts=['{"action":"browser_click","id":9}']));p.next('select Continue',{'elements':[{'id':9,'tag':'BUTTON','text':'Continue'}]},None,[],[])
        self.assertEqual(p.exposed_ids,{9})
        self.assertIn('Continue',p.last_prompt)
        self.assertIn('browser_click',p.last_prompt)
    def test_click_type_is_enforced_by_schema(self):
        for task,expected in [('Select BETA using a single click.','click'),('Select SAMPLE with a double click.','double_click'),('right click the item','right_click'),('open SAMPLE.pdf','double_click'),('open photo.png','double_click'),('open README.md','double_click'),('open something.custom','double_click')]:
            self.assertEqual(requested_point_action(task),expected)
            schema=schema_for(True,set(),expected)
            actions={v['properties']['action']['enum'][0] for v in schema['anyOf']}
            self.assertEqual(actions & {'click','double_click','right_click','move','drag'},{expected})
    def test_browser_dom_keeps_ids_with_whole_screen_image(self):
        p=self.planner();p._generate=Mock(return_value=Mock(texts=['{"action":"browser_click","id":9}']))
        result=p.next('select Continue',{'mode':'browser','elements':[{'id':9,'tag':'BUTTON','text':'Continue'}]},Image.new('RGB',(1920,1200)),[],[])
        self.assertEqual(result,{'action':'browser_click','id':9});self.assertEqual(p.exposed_ids,{9})
        self.assertEqual(p.last_input_size,[1920,1200]);self.assertEqual(len(p._generate.call_args.args[1]),1)
    def test_absent_target_returns_question_without_coordinates(self):
        p=self.planner();p._generate=Mock(side_effect=[Mock(texts=['{"action":"click","target":"missing button"}']),Mock(texts=['{"found":false}'])])
        p._ocr_point=Mock(return_value=None)
        result=p.next('select missing button',{},Image.new('RGB',(600,400)),[],[])
        self.assertEqual(result['action'],'ask');self.assertNotIn('x',result)
    def test_exact_ocr_point_can_recover_visible_file(self):
        p=self.planner();p._generate=Mock(side_effect=[Mock(texts=['{"action":"double_click","target":"SAMPLE.pdf"}']),Mock(texts=['{"found":false}'])])
        p._ocr_point=Mock(return_value={'x':125,'y':450})
        image=Image.new('RGB',(1920,1200))
        result=p.next('open SAMPLE.pdf',{'mode':'desktop'},image,[],[])
        self.assertEqual(result,{'action':'double_click','x':125,'y':450})
        self.assertEqual(p._ocr_point.call_args.args[0].size,(1920,1200));self.assertEqual(p._ocr_point.call_args.args[1],'SAMPLE.pdf')
    def test_chat_answer_can_receive_whole_screen(self):
        p=self.planner();p._generate=Mock(return_value=Mock(texts=['The screen shows a test window.']))
        result=p.answer('what is on my screen?',[],image=Image.new('RGB',(1920,1200)))
        self.assertIn('test window',result)
        self.assertEqual(p._generate.call_args.args[1][0].shape,[1,1200,1920,3])

if __name__=='__main__':unittest.main()

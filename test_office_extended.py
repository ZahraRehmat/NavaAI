import unittest
from office_control import parse_office
from office_plan import validate_plan
from office_tools import color,numeric
from office_catalog import summary

class OfficeExtended(unittest.TestCase):
    def test_user_wording(self):
        examples=[('Make E5 font bigger','font_size_delta','E5','2'),('make E5 font size 20','font_size','E5','20'),
          ('change text colour to red','font_color','','red'),('set font to Arial','font_name','','Arial'),
          ('change the font of E5 to Calibri','font_name','E5','Calibri'),('make table background blue','table_fill','table','blue'),
          ('select cell E5','select','E5',''),('remove the table','table_remove','table',''),
          ('insert bullet points: first; second','bullets','','first; second')]
        for task,action,target,value in examples:
            with self.subTest(task=task):
                result=parse_office(task);self.assertEqual((result['action'],result['target'],result['value']),(action,target,value))
    def test_literal_text(self):
        result=parse_office('type Make font size 20 red!')
        self.assertEqual(result,{'action':'write','text':'Make font size 20 red!','range':None})
    def test_combined_changes(self):
        result=parse_office('make Mahnoor bold and red')
        self.assertEqual({s['action'] for s in result['steps']},{'font_color','format'})
        self.assertTrue(all(s['target']=='Mahnoor' for s in result['steps']))
    def test_plan_registration(self):
        def step(action,value=''):return {'steps':[dict(action=action,target='E5',value=value,text='')]}
        with self.assertRaises(ValueError):validate_plan(step('__getattr__'),'excel','do it',[])
        with self.assertRaises(ValueError):validate_plan(step('save'),'excel','make red',[])
        with self.assertRaises(ValueError):validate_plan(step('mso','FakeCommand'),'excel','do it',[])
        result=validate_plan(step('font_color','red'),'excel','make E5 red',[])
        self.assertEqual(result['steps'][0]['target'],'E5')
    def test_values(self):
        self.assertEqual(color('red'),255);self.assertEqual(color('#0000ff'),16711680)
        with self.assertRaises(ValueError):numeric(float('nan'),1,100)
    def test_catalog(self):
        for kind,counts in summary().items():self.assertGreater(counts['indexed_controls'],1000)

if __name__=='__main__':unittest.main()

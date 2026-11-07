import threading, unittest
from unittest.mock import Mock,patch
from agent import Agent
from planner import Planner, PlannerUnavailable
from prompt_budget import compact_payload,fit_prompt
from routing import search_intent,first_result_intent,text_entry_intent

class ReliabilityTests(unittest.TestCase):
    def test_preserve_requested_multiword_text(self):
        self.assertEqual(text_entry_intent('Replace the Name input with Gwen complete test.')['text'],'Gwen complete test')
        self.assertEqual(text_entry_intent('Fill the Name field with "Hello world.".')['text'],'Hello world.')
        self.assertIsNone(text_entry_intent('Fill the Name field with hello then click Apply'))
    def test_youtube_search_has_its_own_route(self):
        self.assertEqual(search_intent('search mr beast on youtube','chrome')['url'],'https://www.youtube.com/results?search_query=mr+beast')
        self.assertEqual(search_intent('search cats','chrome','youtube')['url'],'https://www.youtube.com/results?search_query=cats')
        self.assertIn('google.com',search_intent('search cats on chrome','chrome','youtube')['url'])

    def test_first_result_typo(self):
        self.assertEqual(first_result_intent('cick on first result'),'result')
        self.assertEqual(first_result_intent('open first video'),'video')

    def test_blocked_followup_never_clicks_or_loads_vlm(self):
        a=Agent(log=lambda _:None); a.mode='browser'; a.active_target='chrome'; a.browser=Mock()
        a.browser.page.url='https://www.google.com/sorry/index'
        a.browser.blocked_reason.return_value='CAPTCHA: manual check required'
        with patch('planner.Planner',side_effect=AssertionError('Must not load')):
            result=a.run('cick on first result')
        self.assertIn('CAPTCHA',result); a.browser.open_first.assert_not_called(); a.browser.act.assert_not_called()

    def test_recovery_discards_gpu_and_retries_cpu_only_once(self):
        p=Planner.__new__(Planner); p.device='GPU'; p.pipe=Mock(); broken=p.pipe
        p.pipe.generate.side_effect=RuntimeError('Exceeded max size of memory object allocation')
        p.gc=Mock(); p.stop=threading.Event(); p.log=Mock(); p.tokenizer=Mock()
        cpu=Mock(); cpu.generate.return_value='healthy result'
        def load(device): self.assertEqual(device,'CPU'); p.pipe=cpu; p.device=device
        p._load=Mock(side_effect=load)
        self.assertEqual(p._generate('prompt',[],None),'healthy result')
        self.assertIs(p.pipe,cpu); broken.generate.assert_called_once(); p._load.assert_called_once_with('CPU'); cpu.generate.assert_called_once()

    def test_failed_recovery_aborts_instead_of_reusing_broken_pipeline(self):
        p=Planner.__new__(Planner); p.device='GPU'; p.pipe=Mock(); p.pipe.generate.side_effect=RuntimeError('GPU allocation failed')
        p.gc=Mock(); p.stop=threading.Event(); p.log=Mock(); p.tokenizer=Mock(); p._load=Mock(side_effect=RuntimeError('CPU failed'))
        with self.assertRaises(PlannerUnavailable): p._generate('prompt',[],None)
        self.assertIsNone(p.pipe); p._load.assert_called_once_with('CPU')

    def test_large_page_is_bounded_and_task_retained(self):
        payload=compact_payload('click target',{'elements':[{'id':i,'text':'target' if i==99 else 'x'*10000,'href':'x'*50000} for i in range(120)],'text':'x'*100000},[{'error':'x'*100000}]*10,[{'task':'x'*10000,'result':'x'*10000}]*10)
        prompt=fit_prompt('Choose JSON.',payload,len,1600)
        self.assertLessEqual(len(prompt),1600); self.assertIn('click target',prompt); self.assertIn('99',prompt)

if __name__=='__main__': unittest.main(verbosity=2)

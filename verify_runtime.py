"""Real inference with bounded large input and an injected GPU-failure recovery."""
import json,threading
from pathlib import Path
from planner import Planner
from actions import validate_action

p=Planner(json.loads(Path('config.json').read_text()),threading.Event(),print)
observation={'mode':'browser','text':'Large page data. '*50000,'elements':[{'id':i,'tag':'BUTTON','text':'Target' if i==99 else 'Other button '+str(i),'href':'x'*10000} for i in range(120)]}
a=p.next('Click the Target button.',observation,None,[{'error':'Large previous error. '*10000}],[])
validate_action(a)
assert p.last_prompt_tokens<=1600
print('PASS real bounded large-page inference:',p.last_prompt_tokens,'text tokens on',p.device,'action',a,flush=True)

class FailedGPU:
    def generate(self,*args,**kwargs): raise RuntimeError('[GPU] Exceeded max size of memory object allocation: injected test fault')

p.pipe=FailedGPU(); p.device='GPU'
simple={'mode':'browser','elements':[{'id':4,'tag':'INPUT','text':'Name','value':''}],'text':''}
a=p.next('Fill the Name input with exactly this text: "Gwen recovery test".',simple,None,[],[])
validate_action(a)
assert p.device=='CPU'
assert a['action']=='browser_fill' and a['id']==4 and a['text']=='Gwen recovery test',a
print('PASS injected GPU fault -> fresh real CPU pipeline -> valid field action',a,flush=True)
Path('runtime-verification.txt').write_text('PASS: Real large-page inference within 1,600 text tokens. Injected GPU error discarded the session; a new real CPU pipeline generated the expected action. Hardware allocation failure itself was simulated.',encoding='utf8')

"""Real Qwen generation with a typed action schema; does not execute desktop input."""
import json,threading,argparse
from pathlib import Path
from PIL import Image,ImageDraw
from planner import Planner
from actions import validate_action

ap=argparse.ArgumentParser(); ap.add_argument('--device',default='CPU'); args=ap.parse_args()
config=json.loads(Path('config.json').read_text()); config['device']=args.device
p=Planner(config,threading.Event(),print)
im=Image.new('RGB',(800,500),'white'); d=ImageDraw.Draw(im)
d.text((40,40),'Recent files',fill='black',font_size=30)
d.text((60,150),'Alpha.docx',fill='black',font_size=26)
d.text((60,250),'Beta.docx',fill='black',font_size=26)
obs={'mode':'desktop','foreground_window':'Test recent files','native_controls':[{'id':10000,'name':'Alpha.docx','type':'VisibleText'},{'id':10001,'name':'Beta.docx','type':'VisibleText'}]}
a=p.next('Open the first recent file.',obs,im,[],[])
validate_action(a)
print('Qwen constrained action:',a,flush=True)
assert (a['action']=='ui_click' and a['id']==10000) or (a['action']=='click' and 75<=a['x']<=290 and 300<=a['y']<=365),a
print('PASS actual Qwen selected the first file with schema-constrained output on',p.device,flush=True)

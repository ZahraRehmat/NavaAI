"""Local model intent check with synthetic full-screen input; no Office edits."""
import json,threading
from pathlib import Path
from PIL import Image,ImageDraw
from planner import Planner

root=Path(__file__).resolve().parent
image=Image.new('RGB',(1920,1200),'white');draw=ImageDraw.Draw(image)
draw.text((100,100),'Synthetic Excel test: E5 is selected. No user document.',fill='black')
planner=Planner(json.loads((root/'config.json').read_text()),threading.Event(),print)
task='Enlarge the lettering in E5 by 4 points and turn it red'
plan=planner.office_plan(task,'excel',image,root/'diagnostics'/'office-planner')
print(json.dumps(plan),flush=True)
assert plan['action']=='batch' and any(s['action']=='font_size_delta' and s['target']=='E5' and float(s['value'])==4 for s in plan['steps'])
assert any(s['action']=='font_color' and s['target']=='E5' and s['value'].lower()=='red' for s in plan['steps'])
(root/'diagnostics'/'office-planner'/'result.json').write_text(json.dumps({'passed':True,'task':task,'plan':plan},indent=2),encoding='utf8')

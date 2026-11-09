"""Offline check of observation/control-list effects on real model output."""
import json,threading
from pathlib import Path
from PIL import Image
from planner import Planner
from visual_targets import VisualTargets
ROOT=Path(__file__).resolve().parent
def main():
    image=Image.open('C:/Users/mahno/AppData/Local/Temp/codex-clipboard-9d964c3f-0f09-4c5d-9c6e-6cb231f1bb36.png').convert('RGB')
    rows=VisualTargets().read(image)
    controls=[{'id':10000+i,'name':r['text'],'type':'VisibleText'} for i,r in enumerate(rows) if r['score']>=.75]
    p=Planner(json.loads((ROOT/'config.json').read_text()),threading.Event(),print);out=[]
    for kind,items in [('ocr_controls',controls),('approximate_native_plus_ocr',[{'id':i,'name':e['name'],'type':'ListItem','focused':False} for i,e in enumerate(controls)]+controls)]:
        action=p.next('open FYP folder',{'mode':'desktop','foreground_window':'Program Manager','native_controls':items},image,[],[])
        row={'test':kind,'controls':items,'action':action};out.append(row);print(json.dumps({'test':kind,'action':action}),flush=True)
        (ROOT/'diagnostics'/'controls-diagnostic.json').write_text(json.dumps(out,indent=2),encoding='utf8')
if __name__=='__main__':main()

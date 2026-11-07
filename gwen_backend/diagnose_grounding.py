"""Offline model diagnostic: no desktop input, OCR, app launch, or fast routes."""
import argparse,json,threading,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import openvino as ov
import openvino_genai as genai
from planner import Planner

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--device');args=parser.parse_args()
    config=json.loads((ROOT/'config.json').read_text())
    if args.device:config['device']=args.device
    out=ROOT/'diagnostics';out.mkdir(exist_ok=True)
    rows=[]
    def emit(row):
        rows.append(row);print(json.dumps(row),flush=True)
        (out/'grounding-diagnostic.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    planner=Planner(config,threading.Event(),lambda msg:print(msg,flush=True))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',34)
    images=[]
    for n,box in enumerate(((60,90,260,190),(650,410,850,510))):
        image=Image.new('RGB',(960,600),'#f5f5f5');draw=ImageDraw.Draw(image)
        draw.rectangle(box,fill='#176bcd');draw.text((box[0]+30,box[1]+28),'TARGET',font=font,fill='white')
        image.save(out/f'fixture-{n}.png');images.append((image,box))
    for n,(image,box) in enumerate(images):
        start=time.monotonic()
        action=planner.next('Click the blue TARGET button.',{'mode':'desktop','foreground_window':'Offline diagnostic fixture','native_controls':[]},image,[],[])
        emit({'test':'existing_agent_prompt','fixture':n,'box':box,'action':action,'raw':planner.last_raw_output,'seconds':round(time.monotonic()-start,2)})
    planner.gc.structured_output_config=None
    for n,(image,box) in enumerate(images):
        scaled=image.copy();scaled.thumbnail((640,400))
        start=time.monotonic()
        response=planner._generate('Locate the center of the blue TARGET button. Give its point as (x, y) normalized to 0-1000. Return only the point.',[ov.Tensor(np.array(scaled)[None,...])],None)
        emit({'test':'simple_unconstrained','fixture':n,'box':box,'raw':response.texts[0],'seconds':round(time.monotonic()-start,2)})
    screenshot=Image.open('C:/Users/mahno/AppData/Local/Temp/codex-clipboard-9d964c3f-0f09-4c5d-9c6e-6cb231f1bb36.png').convert('RGB')
    for size in ((640,400),(1280,800)):
        scaled=screenshot.copy();scaled.thumbnail(size)
        start=time.monotonic()
        response=planner._generate('Locate the desktop folder named FYP. Return only the center point (x, y), with coordinates normalized to 0-1000.',[ov.Tensor(np.array(scaled)[None,...])],None)
        emit({'test':'desktop_fyp_simple','image_size':scaled.size,'raw':response.texts[0],'seconds':round(time.monotonic()-start,2)})
    print('Diagnostic complete; no inputs were executed.',flush=True)

if __name__=='__main__':main()

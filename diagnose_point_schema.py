"""Separate raw visual grounding from action-grammar effects; no computer input."""
import json,threading
from pathlib import Path
from PIL import Image
import numpy as np,openvino as ov,openvino_genai as genai
from planner import Planner
ROOT=Path(__file__).resolve().parent
def main():
    image=Image.open(ROOT/'logs/session-20261028-210907-474612/task-001/step-001/model-input.png').convert('RGB')
    p=Planner(json.loads((ROOT/'config.json').read_text()),threading.Event(),print);rows=[]
    prompt='Locate the center of the blue BETA button. Give its point with x,y normalized to 0-1000.'
    point={'type':'object','properties':{'x':{'type':'integer','minimum':0,'maximum':1000},'y':{'type':'integer','minimum':0,'maximum':1000}},'required':['x','y'],'additionalProperties':False}
    for name,schema,instruction in [('unconstrained',None,prompt+' Return only (x, y).'),('point_schema',point,prompt+' Return only JSON with x and y.'),('unconstrained_action',None,'Click the blue BETA button once. Coordinates are normalized to 0-1000. Return only a JSON object with action, x, y.')]:
        p.gc.structured_output_config=genai.StructuredOutputConfig(json_schema=json.dumps(schema)) if schema else None
        result=p._generate(instruction,[ov.Tensor(np.array(image)[None,...])],None)
        row={'test':name,'raw':result.texts[0]};rows.append(row);print(json.dumps(row),flush=True)
        (ROOT/'diagnostics/point-schema-diagnostic.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
if __name__=='__main__':main()

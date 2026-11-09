"""Bounded Office intent plans, containing data and registered tools only."""
import re
from office_tools import TOOL_APPS

LEGACY={'bold','italic','underline','write','table'}

def schema_for(kind,candidates,tool_names=None):
    actions=list(tool_names) if tool_names is not None else [op for op,apps in TOOL_APPS.items() if kind in apps]
    actions+=sorted(LEGACY)+['ask']
    step={'type':'object','properties':{
        'action':{'type':'string','enum':actions},'target':{'type':'string'},
        'value':{'type':'string'},'text':{'type':'string'}},
        'required':['action','target','value','text'],'additionalProperties':False}
    return {'type':'object','properties':{'steps':{'type':'array','items':step,'minItems':1,'maxItems':6}},'required':['steps'],'additionalProperties':False}

def validate_plan(plan,kind,task,candidates):
    steps=plan.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=6:raise ValueError('Office plan must contain 1–6 steps.')
    result=[]
    for step in steps:
        if not isinstance(step,dict) or set(step)!={'action','target','value','text'} or not all(isinstance(v,str) for v in step.values()):raise ValueError('Office plan fields must be strings.')
        if any(len(v)>20000 for v in step.values()):raise ValueError('Office plan text is too long.')
        op=step['action'];item=dict(step)
        if op=='ask':return {'action':'ask','message':step['text'] or step['value']}
        if op not in LEGACY and (op not in TOOL_APPS or kind not in TOOL_APPS[op]):raise ValueError('Unregistered Office tool: '+op)
        if op=='mso' and step['value'] not in {c['id'] for c in candidates}:raise ValueError('Office command was not in the supplied catalog candidates.')
        if op=='save' and not re.search(r'\bsave\b',task,re.I):raise ValueError('Saving was not requested.')
        if op in ('bold','italic','underline'):item={'action':'format','style':op,'target':step['target'],'value':step['value'].lower() not in ('off','false','no','0')}
        elif op=='write':item={'action':'write','text':step['text'] or step['value'],'range':step['target'] or None}
        elif op=='table':
            match=re.fullmatch(r'(\d+)\s*[xX]\s*(\d+)',step['value'])
            if not match:raise ValueError('Table dimensions must be rows x columns.')
            r,c=map(int,match.groups())
            if not(1<=r<=50 and 1<=c<=20):raise ValueError('Table size exceeds the supported bounds.')
            item={'action':'table','rows':r,'columns':c,'explicit_size':True}
        result.append(item)
    return {'action':'batch','steps':result}

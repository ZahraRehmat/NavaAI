"""Bound page/state input before inference, retaining task and valid element IDs."""
import json

def compact_payload(task, observation, history, context):
    if len(task)>1600: raise ValueError('Please split this instruction into shorter tasks (maximum 1,600 characters).')
    obs={k:str(observation[k])[:320] for k in ('mode','url','title','foreground_window','active_app') if observation.get(k) is not None}
    source=observation.get('elements',observation.get('native_controls',[]))
    terms=set(task.lower().split())
    controls=[]
    for e in source:
        row={k:(v[:100] if isinstance(v,str) else v) for k,v in e.items() if k in ('id','tag','type','text','name','value','focused')}
        controls.append(row)
    controls.sort(key=lambda e: -sum(t in str(e).lower() for t in terms if len(t)>2))
    obs['controls']=controls[:36]
    obs['text']=str(observation.get('text',''))[:1200]
    return {'task':task,'recent_context':[{'task':str(c.get('task',''))[:180],'result':str(c.get('result',''))[:180]} for c in context[-2:]],'recent_actions':[{k:(str(v)[:220] if k!='action' else {ak:(av[:100] if isinstance(av,str) else av) for ak,av in v.items() if ak!='reason'}) for k,v in h.items()} for h in history[-3:]],'observation':obs}

def fit_prompt(instructions,payload,count_tokens,limit=1600):
    def render(): return instructions+'\nCurrent task and state:\n'+json.dumps(payload,ensure_ascii=False,separators=(',',':'))
    prompt=render()
    while count_tokens(prompt)>limit:
        obs=payload['observation']
        if obs.get('text'): obs['text']=obs['text'][:len(obs['text'])//2] if len(obs['text'])>80 else ''
        elif len(obs.get('controls',[]))>1: obs['controls']=obs['controls'][:-1]
        elif payload.get('recent_context'): payload['recent_context']=payload['recent_context'][1:]
        elif payload.get('recent_actions'): payload['recent_actions']=payload['recent_actions'][1:]
        else: raise ValueError('Instruction exceeds the model input budget; shorten it.')
        prompt=render()
    return prompt

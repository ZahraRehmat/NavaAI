"""Confidence scores and explicit choices. Scores are similarities, not probabilities."""
import re
from rapidfuzz.fuzz import ratio
from label_matching import normalize_label,label_score,dialog_action,NoLabelMatch,AmbiguousLabel

class SelectionCancelled(InterruptedError):pass

def similarity(query,label):
    strict,warnings=label_score(query,label)
    q=normalize_label(query);c=normalize_label(label)
    if not q or not c:return 0,[]
    if dialog_action(query):return (100,[]) if q==c else (0,[])
    qe=re.search(r'\.([a-z0-9]{1,6})$',str(query),re.I);ce=re.search(r'\.([a-z0-9]{1,6})$',str(label),re.I)
    if qe and ce and qe[1].lower()!=ce[1].lower():return 0,[]
    qn={x for x in q.split() if x.isdigit()};cn={x for x in c.split() if x.isdigit()}
    if any(not(len(x)==4 and x.startswith(('19','20'))) for x in qn-cn):return 0,[]
    if q.replace(' ','')==c.replace(' ',''):return 100,[]
    # Split/combined words, partial words, omitted words and short paraphrases.
    ignored={'the','a','an','please','button','link','file','video','called','named','says','that','this','on','for','of','with'}
    qw=[w for w in q.split() if w not in ignored];cw=c.split()
    if not qw or len(cw)>max(24,len(qw)*6):return strict,warnings
    hits=[]
    for token in qw:
        best=0
        # Names such as YouTube/GitHub may be exposed as "You Tube"/"Git Hub".
        comparable=cw+[''.join(cw[i:i+2]) for i in range(max(0,len(cw)-1))]
        for word in comparable:
            score=ratio(token,word)
            if min(len(token),len(word))>=4 and (token.startswith(word) or word.startswith(token)):
                score=max(score,92 if min(len(token),len(word))/max(len(token),len(word))>=.6 else 82)
            best=max(best,score)
        hits.append(best)
    coverage=sum(s>=75 for s in hits)/len(hits)
    relaxed=sum(hits)/len(hits)*.65+coverage*30-min(7,max(0,len(cw)-len(qw))*.35)
    # Bare short fragments are too weak to auto-click.
    if len(qw)==1 and len(qw[0])<4 and strict<84:relaxed=min(relaxed,64)
    if qn-cn:relaxed-=8
    return min(100,max(strict,relaxed)),warnings

def rank_targets(rows,query,key='name',minimum=58,merge_overlaps=False):
    result=[]
    priority={'Button':6,'MenuItem':6,'TabItem':6,'Hyperlink':6,'ListItem':5,'Edit':4,'Text':2,'Group':1}
    for row in rows:
        score,warnings=similarity(query,row.get(key,''))
        if score>=minimum:result.append({'row':row,'score':round(score,1),'warnings':warnings})
    result.sort(key=lambda r:(-r['score'],-priority.get(r['row'].get('type'),0)))
    if merge_overlaps:
        kept=[]
        for candidate in result:
            row=candidate['row'];a=row.get('bounds')
            duplicate=False
            for old in kept:
                b=old['row'].get('bounds')
                if not a or not b or normalize_label(row.get(key,''))!=normalize_label(old['row'].get(key,'')):continue
                intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
                area=min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
                if area>0 and intersection/area>.8:duplicate=True;break
            if not duplicate:kept.append(candidate)
        result=kept
    return result

def select_target(rows,query,key='name',chooser=None,merge_overlaps=False):
    ranked=rank_targets(rows,query,key,merge_overlaps=merge_overlaps)
    if not ranked:raise NoLabelMatch('No plausible visible match for '+query)
    top=ranked[0]
    rivals=[r for r in ranked[1:] if top['score']-r['score']<8]
    if top['score']>=90 and not rivals:return top
    choices=[r for r in ranked if top['score']-r['score']<max(12,top['score']-62)][:26]
    if chooser is None:raise AmbiguousLabel('More than one close match or low confidence: '+'; '.join(str(r['row'].get(key,'')) for r in choices[:5]))
    options=[dict(r['row'],label=str(r['row'].get(key,'')),match_score=r['score'],detail=str(r['row'].get('path',r['row'].get('detail','')))) for r in choices]
    index=chooser(query,options)
    if index is None:raise SelectionCancelled('Selection cancelled. Nothing was clicked/opened.')
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(choices):raise ValueError('Invalid target selection; nothing was executed.')
    return choices[index]

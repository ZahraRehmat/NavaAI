"""A dynamic dictionary of actual labels, with aliases and conservative fuzzy ranking."""
import json,re,unicodedata
from functools import lru_cache
from pathlib import Path
from rapidfuzz.fuzz import ratio

class NoLabelMatch(ValueError):pass
class AmbiguousLabel(ValueError):pass
EXTENSIONS='pdf|md|txt|docx?|xlsx?|pptx?|png|jpe?g|gif|bmp|webp|mp4|mkv|avi|mov|webm|mp3|wav|csv|rtf|log|json'

def basic(value):
    value=re.sub(r'([a-z])([A-Z])',r'\1 \2',str(value))
    value=unicodedata.normalize('NFKC',value).casefold().replace('’',"'").replace("'",'')
    value=re.sub(r'\.('+EXTENSIONS+r')\b',' ',value)
    value=re.sub(r'([a-z])([0-9])|([0-9])([a-z])',lambda m:' '.join(x for x in m.groups() if x),value)
    return ' '.join(re.findall(r'\w+',value,flags=re.UNICODE)).replace('_',' ').strip()

@lru_cache(maxsize=1)
def aliases():
    rows=json.loads((Path(__file__).with_name('label_aliases.json')).read_text(encoding='utf8'))
    return sorted([(basic(alias),basic(canonical)) for canonical,items in rows.items() for alias in items],key=lambda p:-len(p[0]))

def normalize_label(value):
    value=basic(value)
    for alias,canonical in aliases():value=re.sub(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',lambda _:canonical,value)
    return ' '.join(value.split())

def dialog_action(label):
    if re.search(r'\.('+EXTENSIONS+r')\s*$',str(label),re.I):return False
    return normalize_label(label) in ('save','dont save','cancel','yes','no','ok')

def label_score(query,label):
    qe=re.search(r'\.('+EXTENSIONS+r')\b',str(query),re.I);ce=re.search(r'\.('+EXTENSIONS+r')\b',str(label),re.I)
    if qe and ce and qe[1].casefold()!=ce[1].casefold():return 0,[]
    q=normalize_label(query);c=normalize_label(label)
    if not q or not c:return 0,[]
    if q==c:return 100,[]
    qt=q.split();ct=c.split();qw=[x for x in qt if not x.isdigit()];cw=[x for x in ct if not x.isdigit()]
    if 'save' in qt and 'save' in ct:
        if bool({'dont','not','never'}&set(qt))!=bool({'dont','not','never'}&set(ct)):return 0,[]
    if len(ct)>max(12,len(qt)*4) and not re.search(r'\.('+EXTENSIONS+r')\s*$',str(label),re.I):return 0,[]
    qn={x for x in qt if x.isdigit()};cn={x for x in ct if x.isdigit()}
    if not qw:
        return (91,[]) if qn and qn<=cn and all(len(x)>=4 for x in qn) else (0,[])
    matches=[]
    for token in qw:
        best=max((ratio(token,t) if len(token)>=4 and len(t)>=4 else 100 if token==t else 0 for t in cw),default=0)
        if best<82:return 0,[]
        matches.append(best)
    missing=qn-cn
    if any(not(len(x)==4 and x.startswith(('19','20'))) for x in missing):return 0,[]
    warnings=[]
    if missing:warnings.append('requested year '+', '.join(sorted(missing))+' differs from title year '+(', '.join(sorted(x for x in cn if len(x)==4)) or '(not shown)'))
    extra=max(0,len(ct)-len(qt))
    score=96-min(4,extra*.7)-(100-sum(matches)/len(matches))*.45-(8 if missing else 0)
    return score,warnings

def choose_label(rows,query,key='name',minimum=84,margin=5,merge_overlaps=False):
    ranked=[]
    for row in rows:
        score,warnings=label_score(query,row.get(key,''))
        if score>=minimum:ranked.append({'row':row,'score':score,'warnings':warnings})
    priority={'Button':5,'MenuItem':5,'TabItem':5,'Hyperlink':5,'ListItem':4,'Edit':4,'ComboBox':4,'Text':2,'Image':2,'Group':1}
    ranked.sort(key=lambda r:(-r['score'],-priority.get(r['row'].get('type'),0)))
    if not ranked:raise NoLabelMatch('No close match for '+query)
    if ranked[0]['score']==100:ranked=[r for r in ranked if r['score']==100]
    best=ranked[0]
    def overlaps(a,b):
        a=a.get('bounds');b=b.get('bounds')
        return a and b and a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
    rivals=[r for r in ranked[1:] if best['score']-r['score']<margin and not(merge_overlaps and overlaps(best['row'],r['row']))]
    if rivals:raise AmbiguousLabel('More than one close match: '+ '; '.join(str(r['row'].get(key,'')) for r in [best,*rivals][:4]))
    return best

def match_description(query,actual):
    if str(query)==str(actual):return ''
    _,warnings=label_score(query,actual)
    return 'Matched "'+query+'" to "'+actual+'"'+(' ('+'; '.join(warnings)+')' if warnings else '')+'.'

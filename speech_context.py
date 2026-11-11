"""Small deterministic speech corrections. No language model or fuzzy code guessing."""
import re
from dataclasses import dataclass

LETTERS={}
for letter,words in {
 'A':'a ay alpha alfa','B':'b bee be bravo','C':'c see sea charlie','D':'d dee delta',
 'E':'e ee echo','F':'f eff ef foxtrot','G':'g gee golf','H':'h aitch haitch hotel',
 'I':'i eye india','J':'j jay juliet juliett','K':'k kay kilo','L':'l el ell lima',
 'M':'m em mike','N':'n en november','O':'o oh oscar','P':'p pee papa',
 'Q':'q cue queue quebec','R':'r ar romeo','S':'s ess sierra','T':'t tee tea tango',
 'U':'u you uniform','V':'v vee victor','W':'w whiskey whisky','X':'x ex xray',
 'Y':'y why yankee','Z':'z zee zed zulu'}.items():
    for word in words.split():LETTERS.setdefault(word,set()).add(letter)
DIGITS={'zero':'0','one':'1','two':'2','to':'2','too':'2','three':'3','four':'4','for':'4','five':'5','six':'6','seven':'7','eight':'8','ate':'8','nine':'9','oh':'0'}
CARDINAL={'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,
          'ten':10,'eleven':11,'twelve':12,'thirteen':13,'fourteen':14,'fifteen':15,'sixteen':16,
          'seventeen':17,'eighteen':18,'nineteen':19,'twenty':20,'thirty':30,'forty':40,'fifty':50,
          'sixty':60,'seventy':70,'eighty':80,'ninety':90,'hundred':100,'thousand':1000}

def number_words(text):
    alternatives='|'.join(CARDINAL)
    def convert(match):
        words=match[0].replace('-',' ').split();values=[CARDINAL[w] for w in words if w!='and']
        if all(v<10 for v in values):return ''.join(str(v) for v in values)
        total=current=0
        for value in values:
            if value==100:current=max(1,current)*100
            elif value==1000:total+=max(1,current)*1000;current=0
            else:current+=value
        return str(total+current)
    return re.sub(r'\b(?:'+alternatives+r')(?:[ -]+(?:and[ -]+)?(?:'+alternatives+r'))*\b',convert,text)

@dataclass(frozen=True)
class Correction:
    text:str
    review:bool=False
    reason:str=''
    code:str=''

def codes(text):
    text=re.sub(r'\bdouble\s+(?:you|u)\b','w',text.lower())
    text=re.sub(r'\bx[ -]ray\b','xray',text)
    text=number_words(text)
    words=re.findall(r'[a-z]+|\d+',text)
    if not words or len(words)>16:return []
    possibilities=['']
    for word in words:
        choices=set(LETTERS.get(word,()))
        if word in DIGITS:choices.add(DIGITS[word])
        if word.isdigit():choices.add(word)
        if not choices and word not in ('the','and','it','is','are') and re.fullmatch(r'[a-z]{1,3}',word):choices.add(word.upper())
        if not choices:return []
        possibilities=[prefix+value for prefix in possibilities for value in sorted(choices)][:32]
    return list(dict.fromkeys(possibilities))

def excel_ref(value):
    m=re.fullmatch(r'([A-Z]{1,3})([1-9]\d{0,6})',value)
    if not m:return False
    col=0
    for ch in m[1]:col=col*26+ord(ch)-64
    return col<=16384 and int(m[2])<=1048576

def correct(text,context=None):
    from direct_commands import normalize_command
    context=context or {};text=normalize_command(text.strip());clean=text.rstrip('.!?').strip()
    # Dictated content is literal. Never rewrite names, prose, passwords or
    # numeric text merely because a word sounds like a letter/number.
    if re.match(r'^(?:type|write|dictate|enter text)\b',clean,re.I):return Correction(text)
    clean=re.sub(r'^(?:please|can you|could you)\s+','',clean,flags=re.I)
    if context.get('office')=='excel':
        selection=re.fullmatch(r'(?:select|choose|go to)\s+(?:cell\s+)?(.+)',clean,re.I)
        if selection:
            options=[code for code in codes(selection[1]) if excel_ref(code)]
            if len(options)==1:return Correction('select cell '+options[0],code=options[0])
        formatting=re.fullmatch(r'(make|set)\s+(?:the\s+)?(?:cell\s+)?(.+?)\s+(bold|italic|underlined|font bigger|font smaller)',clean,re.I)
        if formatting:
            options=[code for code in codes(formatting[2]) if excel_ref(code)]
            if len(options)==1:return Correction(formatting[1].lower()+' '+options[0]+' '+formatting[3].lower(),code=options[0])
            if re.search(r'\bcell\b',clean,re.I):return Correction(clean,True,'Cell reference is unclear. Repeat its column and row separately.')
    if re.match(r'^cell\s+',clean,re.I) or re.match(r'^(?:select|go to|click)\s+(?:the\s+)?cell\s+',clean,re.I):
        m=re.fullmatch(r'(?:(?:select|go to|click)\s+(?:the\s+)?)?cell\s+(.+)',clean,re.I)
        if m:
            options=[code for code in codes(m[1]) if excel_ref(code)]
            if len(options)==1:return Correction('select cell '+options[0],code=options[0])
            return Correction(clean,True,'Cell reference is unclear. Say the column letter and row number separately.')
    if not context.get('grid_active'):
        # Common spoken spelling; keep grid codes and dictated text literal.
        wifi=re.fullmatch(r'((?:click|press|select|open)(?:\s+on)?)\s+(?:wi|why|y)[ -]+fi',clean,re.I)
        if wifi:return Correction(wifi[1].lower()+' wifi')
        return Correction(clean)
    from direct_commands import parse_direct
    direct=parse_direct(clean)
    if direct and direct['kind']=='keys':
        keys=direct['keys'];special={'enter','tab','esc','backspace','delete','space','up','down','left','right','home','end','pageup','pagedown','insert'}
        if set(keys)&{'ctrl','alt','shift'} or (len(keys)==1 and (keys[0] in special or re.fullmatch(r'f(?:[1-9]|1\d|2[0-4])',keys[0]))):return Correction(clean)
    from browser_commands import intent as browser_intent
    visible={str(label).upper() for label in context.get('labels',())}
    parts=re.split(r'\s*;\s*|\s+then\s+',clean,flags=re.I)
    if len(parts)>1:
        corrected=[correct(part,context) for part in parts]
        failed=next((item for item in corrected if item.review),None)
        if failed:return failed
        return Correction(' then '.join(item.text for item in corrected),code=next((item.code for item in reversed(corrected) if item.code),''))
    drag=re.fullmatch(r'drag\s+(.+?)\s+(?:to|onto)\s+(.+)',clean,re.I)
    if drag:
        resolved=[]
        for target in drag.groups():
            found={value for value in codes(target) if value in visible}
            if len(found)!=1:return Correction(clean,True,'Use currently visible labels for both drag endpoints.')
            resolved.append(next(iter(found)))
        return Correction('drag '+resolved[0]+' to '+resolved[1],code=resolved[1])
    # Only normalize the target slot of a known mouse command, or a bare code.
    m=re.fullmatch(r'((?:(?:double|right|left|middle)\s+)?(?:click|press|select|open)|hold(?:\s+(?:right|left))?|close(?:\s+tab)?|move\s+to|scroll\s+(?:up|down|left|right)(?:\s+\d+)?(?:\s+(?:from|on|at|in|over))?)\s+(.+)',clean,re.I)
    prefix=m[1].lower()+' ' if m else '';target=m[2] if m else clean
    if m:target=re.sub(r'^(?:on|at|the)\s+','',target,flags=re.I)
    from dropdown_control import dropdown_intent
    dropdown=dropdown_intent(clean)
    if dropdown:prefix='open dropdown ';target=dropdown
    literal=target.replace(' ','').upper()
    if literal in visible:return Correction(prefix+literal,code=literal)
    from smart_grid_names import ALIASES
    if target.lower() in ALIASES:return Correction(clean)
    options=codes(target)
    if not options:return Correction(clean)
    exact=[option for option in options if option in visible]
    if len(exact)==1:return Correction(prefix+exact[0],code=exact[0])
    if len(exact)>1:return Correction(clean,True,'Those sounds match multiple visible labels. Use NATO spelling, for example alpha bravo.')
    if browser_intent(clean,False):return Correction(clean)
    # Plain names such as "click store" continue to existing name matching.
    # Spelled letters/digits and compact codes must never snap to another label.
    compact=re.fullmatch(r'[A-Za-z]{1,3}\d{0,3}|\d+[A-Za-z]{1,3}',target.replace(' ',''))
    spelled=all(w in LETTERS or w in DIGITS or w.isdigit() for w in re.findall(r'[a-z]+|\d+',target.lower()))
    if compact or spelled:
        value=options[0] if len(options)==1 else target
        return Correction(prefix+value,True,'That code is not a currently visible grid label.',value)
    return Correction(clean)

def hint(context=None):
    # A short vocabulary prompt assists recognition without forcing any label.
    base='Gwen. Computer commands: click, double click, scroll up, scroll down, open, stop, release.'
    if (context or {}).get('grid_active'):return base+' Grid labels are spelled as letters and digits, for example F G, six M J. NATO letters alpha bravo charlie.'
    if (context or {}).get('office')=='excel':return base+' Excel commands: select cell A2, cell E5, bold, font size.'
    return base

"""Direct app, website and search routing."""
import re
from urllib.parse import quote, urlencode, urlsplit
from rapidfuzz.fuzz import ratio
from rapidfuzz.distance import DamerauLevenshtein

CHANNELS={'chrome':'chrome','google chrome':'chrome','edge':'msedge','microsoft edge':'msedge','browser':'chrome','chromium':'chromium'}
BRANDS=('instagram','youtube','facebook','whatsapp','spotify','telegram','netflix')
SITE_NAMES={'youtube':'https://www.youtube.com/','google':'https://www.google.com/','dailymotion':'https://www.dailymotion.com/','instagram':'https://www.instagram.com/','facebook':'https://www.facebook.com/','netflix':'https://www.netflix.com/'}

def browser_channel(context):
    if not context:return None
    title=re.sub(r'[\u200b\u200c\u200d\ufeff]','',context.get('title',''))
    for label,channel in (('Google Chrome','chrome'),('Microsoft Edge','msedge'),('Chromium','chromium')):
        if re.search(r'(?:^|\s[-–—]\s)'+re.escape(label)+r'(?:\s*\([^)]*\))?$',title,re.I):return channel
    return {'chrome':'chrome','msedge':'msedge','chromium':'chromium'}.get(context.get('process','').lower())

def web_url(query,allow_bare_files=False):
    query=query.strip().rstrip('.!')
    explicit=bool(re.match(r'https?://',query,re.I))
    if re.search(r'\s|\\|@',query):return None
    if explicit:
        try:
            parsed=urlsplit(query);host=parsed.hostname;port=parsed.port
            if host and (host=='localhost' or re.fullmatch(r'[a-z0-9.-]+',host,re.I)) and not re.search(r'[<>"\']',query):return query
        except ValueError:return None
        return None
    if not re.fullmatch(r'(?:https?://)?(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[/?#][^\s]*)?',query,re.I):return None
    # README.md and picture.png are file requests, not hostname guesses.
    if not explicit and not allow_bare_files:
        from file_control import DOCUMENTS
        if '.'+query.rsplit('.',1)[-1].lower() in DOCUMENTS:return None
    return query if explicit else 'https://'+query

def website_intent(task,active_target=None):
    match=re.fullmatch(r'\s*(?:please\s+)?(?:open|visit|go\s+to|navigate\s+to)\s+(?:the\s+)?(.+?)\s*',task,re.I)
    if not match:return None
    query=match[1].strip().rstrip('.!?');target=active_target
    suffix=re.fullmatch(r'(.+?)\s+(?:on|in|using|with)\s+(?:the\s+)?(google chrome|chrome|microsoft edge|edge|browser|chromium)[.!]?',query,re.I)
    if suffix:query,target=suffix.groups()
    hint=bool(re.search(r'\s+(?:website|site)$',query,re.I))
    if hint:query=re.sub(r'\s+(?:website|site)$','',query,flags=re.I)
    query=query.strip('"\'')
    from website_directory import directory,spoken_domain
    query=spoken_domain(query)
    url=web_url(query)
    if not url:
        if any(value in query for value in ('\\','/','@',':')):return None
        from file_control import DOCUMENTS
        if '.'+query.rsplit('.',1)[-1].lower() in DOCUMENTS and not hint:return None
        match=directory().lookup(query,allow_reserved=bool(hint or suffix))
        if match:url=match['url']
    if not url:return None
    return {'kind':'browser_search','channel':CHANNELS.get((target or '').lower(),'chrome'),'query':query,'url':url}

def normalize_launch_verb(task):
    # A common missing-space typo: "opengull chat" -> "open gull chat".
    if re.fullmatch(r'\s*open[^\s]+\s+chat[.!]?\s*',task,re.I): task=re.sub(r'^(\s*)open',r'\1open ',task,flags=re.I)
    m=re.fullmatch(r'(\s*(?:please\s+)?)([a-z]+)(\s+.+)',task,re.I|re.S)
    if not m: return task
    word=m[2].lower()
    # Correct only a near-identical launch verb; leave the app name untouched.
    if word not in ('open','launch','start') and len(word)>=3:
        near=[v for v in ('open','launch','start') if DamerauLevenshtein.distance(word,v)==1]
        if len(near)==1: return m[1]+near[0]+m[3]
    return task

def named_click_intent(task):
    m=re.fullmatch(r'\s*(?:please\s+)?(?:click|cick)(?:\s+on)?\s+(?:the\s+)?(.+?)(?:\s+(?:app|button|link|tab|control))?[.!]?\s*',task,re.I)
    if not m or re.search(r'\b(?:then|and|first|second|third)\b',m[1],re.I): return None
    return m[1].strip()

def open_chat_intent(task):
    m=re.fullmatch(r'\s*(?:please\s+)?(?:open|select|click(?:\s+on)?)\s+(?:the\s+)?(.+?)\s+chat(?:\s+(?:on|in)\s+whatsapp)?[.!]?\s*',task,re.I)
    return m[1].strip() if m else None

def correct_query(query):
    if ' ' in query or '.' in query: return query
    ranked=sorted(((ratio(query.lower(),brand),brand) for brand in BRANDS),reverse=True)
    return ranked[0][1] if len(query)>=5 and ranked[0][0]>=80 and DamerauLevenshtein.distance(query.lower(),ranked[0][1])<=2 else query

def search_intent(task, active_target=None, current_site=None):
    m=re.fullmatch(r'\s*(?:please\s+)?(search(?:\s+for)?|find|look\s+up|go\s+to|visit|navigate\s+to)\s+(.+?)\s*',task,re.I)
    if not m: return None
    verb,query=m.groups(); target=active_target
    suffix=re.fullmatch(r'(.+?)\s+(?:on|in|using|with)\s+(?:the\s+)?(google chrome|chrome|microsoft edge|edge|browser|chromium|microsoft store|ms store|store|youtube(?:\.com)?)[.!]?\s*',query,re.I)
    if suffix: query,target=suffix.groups()
    if re.search(r'\b(?:then|and click|and type|and install)\b',query,re.I): return None
    query=query.strip().strip('"').strip("'")
    if not query: return None
    normalized=(target or '').lower()
    if normalized=='task manager':
        return {'kind':'native_search','target':target,'query':query}
    if normalized in CHANNELS and not (suffix and suffix[2].lower().startswith('youtube')):
        direct=web_url(query)
        if direct:return {'kind':'browser_search','channel':CHANNELS[normalized],'query':query,'url':direct}
    if normalized in ('youtube','youtube.com') or (not suffix and current_site=='youtube'):
        return {'kind':'browser_search','channel':CHANNELS.get((active_target or '').lower(),'chrome'),'query':query,'url':'https://www.youtube.com/results?'+urlencode({'search_query':query})}
    if not target: return None
    if normalized in ('store','microsoft store','ms store'):
        corrected=correct_query(query)
        return {'kind':'store_search','query':corrected,'original_query':query,'uri':'ms-windows-store://search/?query='+quote(corrected,safe='')}
    if normalized in CHANNELS:
        channel=CHANNELS[normalized]
        url=web_url(query) or 'https://www.google.com/search?'+urlencode({'q':query})
        return {'kind':'browser_search','channel':channel,'query':query,'url':url}
    return None

def explicit_browser(task):
    m=re.search(r'\b(?:on|in|using|with)\s+(?:the\s+)?(google chrome|chrome|microsoft edge|edge|browser|chromium)\b',task,re.I)
    return CHANNELS[m[1].lower()] if m else None

def first_result_intent(task):
    m=re.fullmatch(r'\s*(?:please\s+)?(?:open|play|click|cick)(?:\s+on)?\s+(?:the\s+)?first\s+(video|result|link)[.!]?\s*',task,re.I)
    return m[1].lower() if m else None

def text_entry_intent(task):
    m=re.fullmatch(r'\s*(?:please\s+)?(?:replace|fill)\s+(?:the\s+)?(.+?)\s+(?:input|field|box)\s+with\s+(?:exactly\s+(?:this\s+text:\s*)?)?(.+?)\s*',task,re.I|re.S)
    if not m: return None
    label,text=m.groups()
    if re.search(r'\b(?:then|and click|and press)\b',text,re.I): return None
    text=text[:-1] if text.endswith('.') else text
    if len(text)>=2 and text[0]==text[-1] and text[0] in ('"',"'"): text=text[1:-1]
    return {'label':label,'text':text}

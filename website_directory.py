"""Cached local popular-domain directory; runtime lookup makes no web requests."""
import json,re
from pathlib import Path
from functools import lru_cache
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
RESERVED={'current','desktop','downloads','documents','pictures','screenshots','samples','reports','report','readme','folder','file','first','second','word','excel','powerpoint','chrome','edge','browser','store','notepad','tab'}


def key(text):return re.sub(r'[^a-z0-9]','',text.casefold())


def spoken_domain(text):
    if re.search(r'\bdot\b',text,re.I):
        value=re.sub(r'\s+dot\s+','.',text.strip(),flags=re.I)
        value=re.sub(r'\s+','',value)
        if re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}',value,re.I):return value
    return text


def brand(domain):
    parts=domain.split('.')
    if len(parts)>=3 and len(parts[-1])==2 and parts[-2] in ('co','com','org','net','gov','edu','ac','mil','ne','or','go','nom'):
        return parts[-3]
    return parts[-2]


class WebsiteDirectory:
    def __init__(self):
        data=json.loads((ROOT/'data/popular_websites.json').read_text(encoding='utf-8'))
        self.domains=data['domains'];self.index={};self.names=[]
        for rank,domain in self.domains:
            url='https://'+domain+'/'
            self.index.setdefault(key(domain),url)
            name=brand(domain)
            if len(name)>=4:
                self.index.setdefault(key(name),url);self.names.append(name.replace('-',' '))
        aliases=json.loads((ROOT/'website_aliases.json').read_text(encoding='utf-8'))
        self.aliases=[]
        for url,names in aliases.items():
            parsed=urlsplit(url)
            if parsed.scheme!='https' or not parsed.hostname:raise ValueError('Website alias must use an HTTPS URL.')
            for name in names:self.index[key(name)]=url;self.aliases.append(name)
        self.keys=tuple(self.index)

    def lookup(self,name,allow_reserved=False):
        name=name.strip().strip('"\'');value=key(name)
        if not value or (not allow_reserved and value in RESERVED):return None
        exact=self.index.get(value)
        if exact:return {'url':exact,'match':'exact'}
        # Correct only a uniquely strong one-character typo in a site name.
        if len(value)<5 or '.' in name:return None
        from rapidfuzz import process,fuzz
        from rapidfuzz.distance import DamerauLevenshtein
        found=process.extract(value,self.keys,scorer=fuzz.ratio,score_cutoff=90,limit=8)
        ranked={}
        for candidate,score,_ in found:
            if DamerauLevenshtein.distance(value,candidate)>1:continue
            url=self.index[candidate];ranked[url]=max(score,ranked.get(url,0))
        ranked=sorted(((score,url) for url,score in ranked.items()),reverse=True)
        if ranked and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=8):return {'url':ranked[0][1],'match':'close_name'}
        return None

    def voice_names(self,limit=300):
        return tuple(dict.fromkeys(self.aliases+self.names[:limit]))


@lru_cache(maxsize=1)
def directory():return WebsiteDirectory()

"""Discover launchable Windows apps without modifying the system."""
import json, os, re, subprocess
from pathlib import Path
from rapidfuzz import fuzz
from app_identity import compact_name,alias_value

ROOT = Path(__file__).resolve().parent
ALIASES = {'store':'microsoft store','ms store':'microsoft store', 'windows store':'microsoft store',
    'vs studio':'visual studio', 'ms visual studio':'visual studio', 'vs code':'visual studio code',
    'vscode':'visual studio code', 'chrome':'google chrome', 'edge':'microsoft edge',
    'files':'file explorer', 'explorer':'file explorer', 'calculator':'calculator', 'settings':'settings',
    'ms word':'word','microsoft word':'word','winword':'word','msword':'word',
    'ms excel':'excel','microsoft excel':'excel','spreadsheet':'excel',
    'power point':'powerpoint','ms powerpoint':'powerpoint','microsoft powerpoint':'powerpoint','ppt':'powerpoint',
    'taskmanager':'task manager','task mgr':'task manager','taskman':'task manager',
    'visual code':'visual studio code','visual studio code editor':'visual studio code',
    'google browser':'google chrome','browser':'google chrome','windows explorer':'file explorer',
    'whats app':'whatsapp','whatsap':'whatsapp','wa':'whatsapp',
    'chat gpt':'chatgpt','chat g p t':'chatgpt','co pilot':'copilot',
    'note pad':'notepad'}

class AmbiguousApp(ValueError):pass

def launch_request(task):
    """Extract an app candidate; explicit file/folder targets keep their own route."""
    match=re.fullmatch(r'\s*(?:please\s+)?(?:open|launch|start)\s+(?:the\s+)?(.+?)\s*[.!]?\s*',task,re.I)
    if not match:return None
    name=match[1].strip().strip('"\'').strip()
    if norm(name) not in ('file explorer','file explorer app') and re.search(r'\b(?:folder|file|document|image|pdf)\b',name,re.I):return None
    if re.search(r'[/\\:]|\.(?!exe$)[a-z0-9]{1,12}$',name,re.I):return None
    if norm(name) not in ALIASES:
        name=re.sub(r'^(?:app|application|program)\s+|\s+(?:app|application|program)$','',name,flags=re.I).strip()
    name=re.sub(r'\.exe$','',name,flags=re.I)
    if norm(name) in ('this','that','it','this app','that app','first','current'):return None
    return name or None

def core_name(name):
    tokens=norm(name).split()
    while len(tokens)>1 and (tokens[0] in ('microsoft','ms','office') or fuzz.ratio(tokens[0],'microsoft')>=85):tokens.pop(0)
    return ' '.join(tokens)

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

class Catalog:
    def __init__(self):
        self.aliases=dict(ALIASES)
        if (ROOT/'aliases.json').exists(): self.aliases.update(json.loads((ROOT/'aliases.json').read_text(encoding='utf-8-sig')))
        if not (ROOT/'apps.json').exists(): self.refresh()
        self.entries = json.loads((ROOT/'apps.json').read_text(encoding='utf-8-sig'))
        self.entries += [dict(name='Microsoft Store',kind='uri',target='ms-windows-store:'),
            dict(name='Settings',kind='uri',target='ms-settings:'),
            dict(name='File Explorer',kind='exe',target=str(Path(os.environ['WINDIR'])/'explorer.exe'))]

    @staticmethod
    def refresh():
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'app_catalog.ps1')], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def resolve(self, name):
        query=norm(name)
        for _ in range(3):
            expanded=alias_value(query,self.aliases)
            if expanded==query: break
            query=norm(expanded)
        exact = [e for e in self.entries if norm(e['name']) == query]
        if exact: return exact[0]
        joined=[e for e in self.entries if compact_name(e['name'])==compact_name(query)]
        if joined:return joined[0]
        core=core_name(query)
        canonical=[e for e in self.entries if core_name(e['name'])==core]
        if len({norm(e['name']) for e in canonical})==1:return canonical[0]
        # Visual Studio and Visual Studio Code are different products.
        candidates = [e for e in self.entries if not (query=='visual studio' and any(word in norm(e['name']).split() for word in ('code','installer','tools','prompt')))]
        def score(entry):
            label=core_name(entry['name']);q=core_name(query)
            base=max(fuzz.ratio(q,label),fuzz.ratio(compact_name(q),compact_name(label)))
            # Match a short actual product name within a longer installed title,
            # but do not turn arbitrary substring overlap into an app match.
            if set(q.split())<=set(label.split()) and len(q)>=4:
                base=max(base,94-min(10,max(0,len(label.split())-len(q.split()))*2))
            return base
        ranked = sorted(((score(e), e) for e in candidates), key=lambda x:x[0], reverse=True)
        if query=='visual studio' and candidates:
            ide=[e for e in candidates if norm(e['name']).startswith('visual studio')]
            if len({norm(e['name']) for e in ide})==1: return ide[0]
        if not ranked or ranked[0][0] < 78:
            raise ValueError(f'App not found: {name}. Refresh apps or use its installed name.')
        top = ranked[0]
        other = next((x for x in ranked[1:] if norm(x[1]['name'])!=norm(top[1]['name'])),None)
        if other and top[0]-other[0]<4:
            raise AmbiguousApp(f'Ambiguous app: {top[1]["name"]} or {other[1]["name"]}. Please give the full name.')
        return top[1]

    def identities(self,name):
        """The opening directory also supplies names, binaries and packaged IDs."""
        from pathlib import PureWindowsPath
        current=norm(name);names={current}
        for _ in range(3):
            expanded=norm(alias_value(current,self.aliases))
            names.add(expanded)
            if expanded==current:break
            current=expanded
        try:entry=self.resolve(name)
        except ValueError:return names
        names.add(norm(entry['name']))
        identity=compact_name(entry['name'])
        for row in self.entries:
            if compact_name(row['name'])!=identity:continue
            target=row.get('target','')
            if row.get('kind')=='exe' and target.lower().endswith('.exe'):
                names.add(norm(PureWindowsPath(target).stem))
            elif row.get('kind')=='app' and '!' in target:names.add(norm(target))
        return names

    def launch(self, name):
        e = self.resolve(name)
        if e['kind']=='app': subprocess.Popen(['explorer.exe', 'shell:AppsFolder\\'+e['target']])
        elif e['kind'] in ('shortcut','uri'): os.startfile(e['target'])
        else: subprocess.Popen([e['target']])
        return e['name']

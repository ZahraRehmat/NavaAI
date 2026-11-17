"""Record the published source/config inventory independently of runtime payloads."""
import hashlib,json,subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=root).decode().split('\0')
files=[]
for name in sorted(set(paths)):
    if not name or name=='PUBLICATION_MANIFEST.json':continue
    path=root/name
    if path.is_file():files.append({'path':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'PUBLICATION_MANIFEST.json').write_text(json.dumps({'snapshot':'2026-11-17','release':'1.0.1','mode':'direct','qwen_weights_included':False,'files':files},indent=2)+'\n',encoding='utf-8')
print('Manifest files:',len(files))

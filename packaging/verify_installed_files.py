"""Compare a fresh test installation with its complete build manifest."""
import hashlib,json,sys
from pathlib import Path

def verify(payload,installed):
    manifest=json.loads((payload/'PAYLOAD_MANIFEST.json').read_text(encoding='utf-8'))
    failures=[]
    for row in manifest['files']:
        path=installed/row['path']
        if not path.is_file():
            failures.append('Missing: '+row['path'])
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            failures.append('Changed: '+row['path'])
    result={'files_checked':len(manifest['files']),'failures':failures,'passed':not failures}
    print(json.dumps(result,indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':verify(Path(sys.argv[1]),Path(sys.argv[2]))

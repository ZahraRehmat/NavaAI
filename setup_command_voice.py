"""One-time download of the small offline command model; runtime never downloads."""
import hashlib,json,tempfile,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
URL='https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'
DEST=ROOT/'models'/'vosk-model-small-en-us-0.15'

def main():
    if (DEST/'am'/'final.mdl').is_file():print('Offline command model is already installed.');return
    models=ROOT/'models';models.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gwen-voice-download-') as folder:
        archive=Path(folder)/'model.zip';print('Downloading official Vosk small English model...',flush=True)
        urllib.request.urlretrieve(URL,archive)
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                target=(models/member.filename).resolve()
                if not target.is_relative_to(models.resolve()):raise ValueError('Unsafe model archive path')
            package.extractall(models)
        (DEST/'download-source.json').write_text(json.dumps({'url':URL,'sha256':digest,'license':'Apache-2.0','runtime':'fully offline'},indent=2),encoding='utf-8')
    print('Offline command model ready:',DEST,flush=True)

if __name__=='__main__':main()

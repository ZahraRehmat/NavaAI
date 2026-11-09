"""One-time download; all recognition afterwards runs locally on CPU."""
import json
from pathlib import Path
from faster_whisper.utils import download_model

root=Path(__file__).resolve().parent
if __name__=='__main__':
    download_model('base.en',output_dir=str(root/'models'/'whisper-base.en'))
    path=root/'voice_config.json';config=json.loads(path.read_text(encoding='utf-8'))
    config.update(engine='hybrid',dictation_model='models/whisper-base.en',dictation_silence_ms=1200,cpu_threads=2,beam_size=3)
    path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    print('Offline hybrid voice ready. Restart Gwen to use it.')

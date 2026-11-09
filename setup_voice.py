"""Fetch the small local speech model once, into this assistant's own folder."""
from pathlib import Path
from faster_whisper.utils import download_model

root=Path(__file__).resolve().parent
dest=root/'models'/'whisper-tiny.en'
print('Downloading local English speech model to',dest,flush=True)
download_model('tiny.en',output_dir=str(dest))
print('Speech model ready.',flush=True)

"""Small CPU-only offline command recognition with bounded contextual vocabulary."""
import json,re,time
from functools import lru_cache
from pathlib import Path
import numpy as np
from speech_context import LETTERS,DIGITS,CARDINAL

ROOT=Path(__file__).resolve().parent
BASE='gwen guen glen glenn hey okay listen continuously sleep wake up stop cancel now task show hide chat grid smart full exit microphone off confirm command yes no option choose click double right left middle press select open hold release drag move mouse cursor to from on at in over scroll down up pixel point cell cells range make set change the font size color colour bold italic underline underlined type write save close switch new tab browser chrome edge store word excel powerpoint whatsapp search copy paste undo redo delete clear insert table row column black blue red green increase decrease bigger smaller a little bit lot steps times seconds'.split()

NUMBER_WORDS=['zero','one','two','three','four','five','six','seven','eight','nine']
NATO='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu'.split()

@lru_cache(maxsize=1)
def application_names():
    """Local catalog hints only; never turn a similar-sounding word into an app."""
    from catalog import ALIASES
    names=set(ALIASES)|set(ALIASES.values())
    names.update(('notepad','task manager','settings','file explorer','youtube','wi fi','wifi','bluetooth','network and internet','sound','display','microphone','volume','mute','unmute','privacy','notifications'))
    try:
        names.update(row['name'] for row in json.loads((ROOT/'apps.json').read_text(encoding='utf-8-sig')) if row.get('name'))
    except (OSError,ValueError,TypeError):pass
    return tuple(sorted(names))

def vocabulary(context,model):
    # Homophone duplicates ("bee"/"be"/"b", "em"/"m") split confidence
    # across equivalent words. Keep canonical letters and NATO vocabulary.
    words=set(BASE)|set('abcdefghijklmnopqrstuvwxyz')|set(NATO)|set(CARDINAL)|{'and','quit','force','kill','terminate','dictation','finish','typing','end','mode','folder'}
    names=list(application_names())+list((context or {}).get('target_names',())[:250])
    title=((context or {}).get('interaction') or {}).get('title','')
    if title:names.append(title)
    names=[' '.join(re.findall(r'[a-z]+',name.lower())) for name in names]
    for name in names:words.update(name.split())
    words={word for word in words if model.vosk_model_find_word(word)>=0}
    phrases=['gwen listen','gwen sleep','gwen grid','gwen full grid','gwen smart grid','gwen stop','gwen confirm command','show chat','hide chat','scroll up','scroll down','double click','move to','select cell','go to cell']
    for name in names:
        if name and len(name.split())<=10:
            for prefix in ('','open ','click ','switch to ','close ','quit ','stop ','force close ','force stop ','terminate '):
                phrases.append(prefix+name)
                if prefix:phrases.append('gwen '+prefix+name)
    for label in (context or {}).get('labels',())[:1000]:
        if not re.fullmatch(r'[A-Za-z0-9]{1,8}',label):continue
        spelled=' '.join(NUMBER_WORDS[int(c)] if c.isdigit() else c.lower() for c in label)
        nato=' '.join(NUMBER_WORDS[int(c)] if c.isdigit() else NATO[ord(c.lower())-97] for c in label)
        for code in (spelled,nato):
            for prefix in ('','click ','double click ','scroll down from ','scroll up from ','move to '):
                phrases.append(prefix+code);phrases.append('gwen '+prefix+code)
    if (context or {}).get('office')=='excel':
        for column in 'abcdefghijklmnopqrstuvwxyz':
            for digit in list(CARDINAL):
                phrases.append('cell '+column+' '+digit);phrases.append('gwen cell '+column+' '+digit)
    phrases=[phrase for phrase in phrases if all(word in words for word in phrase.split())]
    return sorted(words)+list(dict.fromkeys(phrases))+['[unk]']

class VoskRecognizer:
    def __init__(self,log=lambda _:None,config=None):
        import vosk
        vosk.SetLogLevel(-1);self.vosk=vosk;self.config=config or {}
        path=ROOT/self.config.get('model','models/vosk-model-small-en-us-0.15')
        if not (path/'am'/'final.mdl').is_file():raise RuntimeError('Offline command model missing. Run setup_command_voice.py once.')
        log('Loading small offline command recognition…');self.model=vosk.Model(str(path))

    def transcribe(self,audio,context=None):return self.transcribe_result(audio,context)['text']

    def transcribe_result(self,audio,context=None):
        started=time.monotonic();context=context or {}
        if isinstance(audio,(str,Path)):
            from faster_whisper.audio import decode_audio
            audio=decode_audio(str(audio),sampling_rate=16000)
        audio=np.asarray(audio,dtype=np.float32).reshape(-1)
        if not len(audio) or float(np.sqrt(np.mean(audio*audio)))<.0005:return {'text':'','confidence':0,'words':[],'seconds':time.monotonic()-started}
        # The normal language graph handles names/prose; contextual mode limits
        # command words and phonetic codes, with [unk] available for rejection.
        recognizer=(self.vosk.KaldiRecognizer(self.model,16000) if context.get('dictation') else
                    self.vosk.KaldiRecognizer(self.model,16000,json.dumps(vocabulary(context,self.model))))
        recognizer.SetWords(True);results=[]
        pcm=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
        for offset in range(0,len(pcm),8000):
            if recognizer.AcceptWaveform(pcm[offset:offset+8000]):results.append(json.loads(recognizer.Result()))
        results.append(json.loads(recognizer.FinalResult()))
        words=[{'word':w['word'],'probability':float(w['conf'])} for result in results for w in result.get('result',())]
        text=' '.join(result.get('text','') for result in results).strip()
        dictation=bool(re.match(r'^(?:(?:hey|okay|ok)\s+)?(?:(?:gwen|guen|glen|glenn)\s+)?(?:listen\s+)?(?:type|write|dictate)\s+',text))
        if dictation or ('[unk]' in text and not context.get('grid_active') and not context.get('dialog_active')):
            general=self.vosk.KaldiRecognizer(self.model,16000);general.SetWords(True);general.AcceptWaveform(pcm)
            fallback=json.loads(general.FinalResult())
            if fallback.get('text') and (not dictation or re.match(r'^(?:(?:hey|okay|ok)\s+)?(?:(?:gwen|guen|glen|glenn|when)\s+)?(?:listen\s+)?(?:type|write|dictate)\s+',fallback['text'])):
                # Only the wake-name homophone may be canonicalized, and only
                # when the command decoder independently recognized Gwen.
                candidate=fallback['text']
                if text.startswith('gwen '):candidate=re.sub(r'^(?:when|glen|glenn)\b','gwen',candidate)
                text=candidate;words=[{'word':w['word'],'probability':float(w['conf'])} for w in fallback.get('result',())]
        confidence=sum(w['probability'] for w in words)/len(words) if words else 0
        if '[unk]' in text:confidence=min(confidence,.5)
        return {'text':text,'confidence':confidence,'words':words,'seconds':time.monotonic()-started,'backend':'vosk'}

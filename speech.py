"""Local microphone -> Whisper -> command text, and offline Windows speech replies."""
import collections,queue,threading,time
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent

class Segmenter:
    def __init__(self,silence_frames=24): self.silence_frames=silence_frames;self.reset()
    def reset(self):
        self.pre=collections.deque(maxlen=8); self.parts=[]; self.silent=0; self.voiced=0; self.noise=.0008
    def add(self,data):
        rms=float(np.sqrt(np.mean(data*data))) if len(data) else 0
        speaking=rms>max(.0025,self.noise*3)
        if not self.parts:
            self.pre.append(data)
            if not speaking:
                self.noise=.98*self.noise+.02*rms; return None
            self.parts=list(self.pre); self.pre.clear(); self.voiced=1; self.silent=0
        else:
            self.parts.append(data)
            if speaking: self.voiced+=1; self.silent=0
            else: self.silent+=1
        if self.silent>=self.silence_frames or len(self.parts)>=400:
            result=np.concatenate(self.parts) if self.voiced>=5 else None
            self.reset(); return result
        return None

class LocalRecognizer:
    def __new__(cls,log=lambda _:None,config=None):
        if (config or {}).get('engine')=='hybrid':
            from hybrid_speech import HybridRecognizer
            return HybridRecognizer(log,config)
        if (config or {}).get('engine')=='vosk':
            from vosk_speech import VoskRecognizer
            return VoskRecognizer(log,config)
        return super().__new__(cls)

    def __init__(self,log=lambda _:None,config=None):
        from faster_whisper import WhisperModel
        self.config=config or {};path=ROOT/self.config.get('model','models/whisper-tiny.en')
        if not (path/'model.bin').exists(): raise RuntimeError('Local speech model missing. Run setup_voice.py once.')
        log('Loading local speech recognition...')
        self.model=WhisperModel(str(path),device='cpu',compute_type='int8',cpu_threads=self.config.get('cpu_threads',2),num_workers=1,local_files_only=True)

    def transcribe(self,audio,context=None):return self.transcribe_result(audio,context)['text']

    def transcribe_result(self,audio,context=None):
        from speech_context import hint
        started=time.monotonic()
        prompt='Natural English dictation.' if (context or {}).get('dictation') else hint(context)
        if (context or {}).get('selection'):
            vocabulary=(context or {}).get('selection_hints','')[-600:]
            prompt='Text selection: from first, second, third, or last occurrence of a phrase to another. Vocabulary: '+vocabulary
        segments,_=self.model.transcribe(audio,language='en',beam_size=self.config.get('beam_size',3),best_of=1,temperature=0,condition_on_previous_text=False,vad_filter=True,vad_parameters={'min_silence_duration_ms':300},initial_prompt=prompt,word_timestamps=True,max_new_tokens=256)
        accepted=[s for s in segments if s.no_speech_prob<.6 and s.avg_logprob> -1.25]
        words=[{'word':w.word.strip(),'probability':float(w.probability)} for s in accepted for w in (s.words or ())]
        import re
        spoken=[w for w in words if re.search(r'\w',w['word'])]
        confidence=sum(w['probability'] for w in spoken)/len(spoken) if spoken else 0
        return {'text':' '.join(s.text.strip() for s in accepted).strip(),'confidence':confidence,'words':words,'seconds':time.monotonic()-started}

class Speaker:
    def __init__(self,on_error=lambda _:None):
        self.q=queue.Queue(); self.speaking=threading.Event(); self.cancelled=threading.Event(); self.enabled=True; self.on_error=on_error
        self.thread=threading.Thread(target=self._run,daemon=True); self.thread.start()

    def say(self,text):
        if self.enabled and text: self.q.put(str(text)[:900])
    def cancel(self):
        self.cancelled.set()
        while True:
            try: self.q.get_nowait()
            except queue.Empty: break
    def close(self): self.cancel(); self.q.put(None)
    def _run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            import win32com.client
            voice=win32com.client.Dispatch('SAPI.SpVoice'); voice.Rate=1
            while True:
                text=self.q.get()
                if text is None: break
                if not self.enabled: continue
                self.cancelled.clear(); self.speaking.set()
                try:
                    voice.Speak(text,1)
                    while not voice.WaitUntilDone(50):
                        if self.cancelled.is_set(): voice.Speak('',3); break
                finally:
                    time.sleep(.15); self.speaking.clear()
        except Exception as exc: self.on_error('Spoken replies unavailable: '+str(exc)[:180])
        finally: self.speaking.clear(); pythoncom.CoUninitialize()

class VoiceEngine:
    def __init__(self,on_text,on_status,context_fn,speaker=None,config=None,detailed=False):
        self.on_text=on_text; self.on_status=on_status; self.context_fn=context_fn; self.speaker=speaker
        self.enabled=threading.Event(); self.enabled.set(); self.shutdown=threading.Event(); self.ready=threading.Event(); self.restart=threading.Event()
        self.audio=queue.Queue(maxsize=80); self.utterances=queue.Queue(maxsize=3); self.device=None; self.level=0
        self.epoch=0
        self.microphone_open=threading.Event();self.active_device='';self.last_status='Starting';self.last_audio_at=0
        self.config=config or {};self.detailed=detailed
        self.overflow=threading.Event()
        self.threads=[threading.Thread(target=self._recognize,daemon=True),threading.Thread(target=self._capture,daemon=True)]
    def start(self):
        for thread in self.threads: thread.start()
    def report(self,message):
        self.last_status=message;self.on_status(message)
    def set_enabled(self,value):
        self.epoch+=1
        if value: self.enabled.set()
        else: self.enabled.clear(); self.level=0
    def set_device(self,value): self.epoch+=1; self.device=value; self.restart.set()
    def cancel_pending(self,restart=True):
        self.epoch+=1
        if restart:self.restart.set()
        for q in (self.audio,self.utterances):
            while True:
                try: q.get_nowait()
                except queue.Empty: break
    def close(self): self.shutdown.set(); self.enabled.clear()
    def _recognize(self):
        try:
            recognizer=LocalRecognizer(self.report,self.config); self.ready.set()
            if not self.enabled.is_set(): self.on_status('Local speech ready; microphone off. Press F9 or enable Hands-free.')
        except Exception as exc: self.report('Voice unavailable: '+str(exc)); return
        while not self.shutdown.is_set():
            try: audio,context,epoch=self.utterances.get(timeout=.2)
            except queue.Empty: continue
            if not self.enabled.is_set() or epoch!=self.epoch: continue
            try:
                self.report('Recognizing speech...')
                result=recognizer.transcribe_result(audio,context)
                if result['text'] and self.enabled.is_set() and epoch==self.epoch:self.on_text(result if self.detailed else result['text'],context)
                self.report('Microphone listening' if self.microphone_open.is_set() else 'Microphone off')
            except Exception as exc: self.report('Speech recognition error: '+str(exc)[:160])
    def _capture(self):
        import sounddevice as sd
        while not self.shutdown.is_set() and not self.ready.wait(.2): pass
        while not self.shutdown.is_set():
            if not self.enabled.wait(.2): continue
            segmenter=Segmenter(max(12,round(self.config.get('silence_ms',900)/30)));utterance_context=None;segmenter_epoch=self.epoch
            try:
                info=sd.query_devices(self.device,kind='input'); rate=16000
                try: sd.check_input_settings(device=self.device,channels=1,dtype='float32',samplerate=rate)
                except Exception: rate=int(info['default_samplerate'])
                def callback(indata,frames,timing,status):
                    if (self.speaker and self.speaker.speaking.is_set()) or not self.enabled.is_set(): return
                    chunk=indata[:,0].copy()
                    self.level=float(np.sqrt(np.mean(chunk*chunk)))
                    self.last_audio_at=time.monotonic()
                    try: self.audio.put_nowait((chunk,self.epoch))
                    except queue.Full:self.overflow.set()
                    if status:self.overflow.set()
                self.restart.clear()
                while True:
                    try: self.audio.get_nowait()
                    except queue.Empty: break
                if not self.enabled.is_set(): continue
                with sd.InputStream(device=self.device,samplerate=rate,channels=1,dtype='float32',blocksize=int(rate*.03),callback=callback):
                    self.active_device=info['name'];self.microphone_open.set()
                    self.report('Microphone listening: '+info['name'])
                    while not self.shutdown.is_set() and self.enabled.is_set() and not self.restart.is_set():
                        try: chunk,chunk_epoch=self.audio.get(timeout=.1)
                        except queue.Empty: continue
                        if segmenter_epoch!=self.epoch:
                            segmenter.reset();utterance_context=None;segmenter_epoch=self.epoch
                        if self.overflow.is_set():
                            self.overflow.clear();segmenter.reset();utterance_context=None
                            while True:
                                try:self.audio.get_nowait()
                                except queue.Empty:break
                            self.on_status('Audio buffer overflow; repeat the last command.');continue
                        if chunk_epoch!=self.epoch:segmenter.reset();utterance_context=None;continue
                        if self.speaker and self.speaker.speaking.is_set(): segmenter.reset();continue
                        was_active=bool(segmenter.parts)
                        utterance=segmenter.add(chunk)
                        if not was_active and segmenter.parts:utterance_context=self.context_fn()
                        if utterance_context:
                            segmenter.silence_frames=max(12,round(self.config.get('dictation_silence_ms',1200) / 30)) if utterance_context.get('dictation') else max(12,round(self.config.get('silence_ms',900)/30))
                        if utterance is not None:
                            if rate!=16000:
                                utterance=np.interp(np.arange(round(len(utterance)*16000/rate))*rate/16000,np.arange(len(utterance)),utterance).astype(np.float32)
                            context=utterance_context or self.context_fn();utterance_context=None
                            try: self.utterances.put_nowait((utterance,context,chunk_epoch))
                            except queue.Full: self.on_status('Speech queue busy; repeat the last command.')
                segmenter.reset()
                if not self.enabled.is_set(): self.report('Microphone off')
            except Exception as exc:
                self.enabled.clear(); self.report('Microphone unavailable: '+str(exc)[:190])
            finally:
                self.microphone_open.clear();self.level=0

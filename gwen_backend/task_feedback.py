"""Audio-only task feedback. No windows, activation, input or notification APIs."""
import array,io,math,queue,threading,wave

def cue_wave(kind='complete'):
    sequence=[(880,.10)] if kind=='complete' else [(660,.07),(0,.05),(440,.09)]
    rate=22050;samples=array.array('h')
    for frequency,duration in sequence:
        count=round(rate*duration)
        for n in range(count):
            envelope=min(1,n/(rate*.006),(count-1-n)/(rate*.006))
            samples.append(round(5200*max(0,envelope)*math.sin(2*math.pi*frequency*n/rate)) if frequency else 0)
    output=io.BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(samples.tobytes())
    return output.getvalue()

class SoundCues:
    def __init__(self,enabled=True,play=None):
        self.enabled=enabled;self.play=play or self._play;self.speaking=threading.Event()
        self.shutdown=threading.Event();self.queue=queue.Queue(maxsize=4)
        self.thread=threading.Thread(target=self._run,daemon=True,name='Gwen completion sound');self.thread.start()
    @staticmethod
    def _play(data):
        import winsound
        winsound.PlaySound(data,winsound.SND_MEMORY|winsound.SND_SYNC|winsound.SND_NODEFAULT)
    def notify(self,kind='complete'):
        if not self.enabled or self.shutdown.is_set():return
        try:self.queue.put_nowait(kind)
        except queue.Full:pass
    def close(self):self.shutdown.set()
    def _run(self):
        while not self.shutdown.is_set():
            try:kind=self.queue.get(timeout=.1)
            except queue.Empty:continue
            self.speaking.set()
            try:self.play(cue_wave(kind))
            except Exception:pass # Missing/muted output must not disrupt input or task completion.
            finally:
                self.shutdown.wait(.12);self.speaking.clear()

class BackgroundPresenter:
    """Only explicit user requests restore the panel; task results are audio-only."""
    def __init__(self,panel,cues):self.panel=panel;self.cues=cues
    def begin(self):self.panel.withdraw()
    def finished(self,result=''):
        failure=result.startswith(('Task failed:','Could not','Stopped','Cancelled'))
        self.cues.notify('attention' if failure else 'complete')
    def review(self):self.cues.notify('attention')

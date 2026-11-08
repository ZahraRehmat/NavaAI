"""Local, continuous microphone listening and Windows speech output."""
import queue
import threading
from collections import deque
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class VoiceListener(QThread):
    recognized = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event()
        self._suspend = threading.Event()

    def stop_listening(self):
        self.stop_event.set()

    def suspend_recognition(self, suspended):
        if suspended:
            self._suspend.set()
        else:
            self._suspend.clear()

    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel

            project_dir = Path(__file__).resolve().parent
            bundled_model = project_dir / 'gwen_backend' / 'models' / 'whisper-tiny.en'
            model_file = bundled_model / 'model.bin'
            has_bundled_model = model_file.is_file() and model_file.stat().st_size > 1_000_000
            model_dir = project_dir / '.venv' / 'models'
            model_dir.mkdir(parents=True, exist_ok=True)
            self.status_changed.emit('Loading local speech recognition…')
            model = WhisperModel(
                str(bundled_model) if has_bundled_model else 'tiny.en',
                device='cpu', compute_type='int8',
                download_root=str(model_dir),
            )
            if self.stop_event.is_set():
                return

            device = sd.query_devices(kind='input')
            sample_rate = int(device['default_samplerate'])
            blocksize = max(512, int(sample_rate * 0.1))
            audio_queue = queue.Queue(maxsize=40)
            preroll = deque(maxlen=5)
            captured = []
            speaking = False
            quiet_seconds = 0.0
            noise_floor = 0.002

            def callback(indata, frames, timing, status):
                if status:
                    self.status_changed.emit('Microphone active · check input level')
                block = indata[:, 0].copy()
                try:
                    audio_queue.put_nowait(block)
                except queue.Full:
                    try:
                        audio_queue.get_nowait()
                        audio_queue.put_nowait(block)
                    except queue.Empty:
                        pass

            self.status_changed.emit('Listening · speak naturally')
            with sd.InputStream(
                device=None, samplerate=sample_rate, channels=1,
                dtype='float32', blocksize=blocksize, callback=callback,
            ):
                while not self.stop_event.is_set():
                    if self._suspend.is_set():
                        speaking = False
                        captured = []
                        quiet_seconds = 0.0
                        preroll.clear()
                        while not audio_queue.empty():
                            try:
                                audio_queue.get_nowait()
                            except queue.Empty:
                                break
                        self.msleep(100)
                        continue
                    try:
                        block = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    duration = len(block) / sample_rate
                    rms = float(np.sqrt(np.mean(np.square(block))))
                    threshold = max(0.006, noise_floor * 3.0)

                    if not speaking:
                        noise_floor = min(0.02, noise_floor * 0.98 + rms * 0.02)
                        preroll.append(block)
                        if rms >= threshold:
                            speaking = True
                            captured = list(preroll)
                            quiet_seconds = 0.0
                            self.status_changed.emit('Listening…')
                    else:
                        captured.append(block)
                        if rms < threshold:
                            quiet_seconds += duration
                        else:
                            quiet_seconds = 0.0

                        captured_seconds = sum(len(part) for part in captured) / sample_rate
                        if quiet_seconds >= 0.75 or captured_seconds >= 10.0:
                            audio = np.concatenate(captured)
                            if sample_rate != 16000:
                                source_times = np.arange(len(audio), dtype=np.float32) / sample_rate
                                target_count = max(1, round(len(audio) * 16000 / sample_rate))
                                target_times = np.arange(target_count, dtype=np.float32) / 16000
                                audio = np.interp(target_times, source_times, audio).astype(np.float32)
                            self.status_changed.emit('Understanding…')
                            segments, _ = model.transcribe(
                                audio, language='en', beam_size=1,
                                vad_filter=True, condition_on_previous_text=False,
                                no_speech_threshold=0.6,
                            )
                            text = ' '.join(part.text.strip() for part in segments).strip()
                            if text:
                                self.recognized.emit(text)
                            captured = []
                            speaking = False
                            quiet_seconds = 0.0
                            preroll.clear()
                            self.status_changed.emit('Listening · speak naturally')
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class SpeechOutput(QThread):
    """Speak queued replies through Windows SAPI without blocking the UI."""

    error_occurred = Signal(str)
    speaking_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._stop = threading.Event()

    def speak(self, text):
        if text:
            self._queue.put(str(text))

    def stop_speaking(self):
        self._stop.set()
        self._queue.put(None)

    def run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init('sapi5')
            engine.setProperty('rate', 165)
            while not self._stop.is_set():
                try:
                    text = self._queue.get(timeout=0.25)
                except queue.Empty:
                    continue
                if text is None:
                    break
                self.speaking_changed.emit(True)
                try:
                    engine.say(text)
                    engine.runAndWait()
                finally:
                    self.speaking_changed.emit(False)
            engine.stop()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

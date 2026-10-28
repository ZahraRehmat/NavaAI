
import os
import tempfile
import threading

import sounddevice as sd
import soundfile as sf

from PySide6.QtCore import QThread, Signal
from faster_whisper import WhisperModel


class SpeechWorker(QThread):
    transcript_ready = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event()

    def stop_recording(self):
        """Request recording to stop."""
        self.stop_event.set()

    def run(self):
        audio_path = None

        try:
            self.status_changed.emit("Loading speech model...")

            model = WhisperModel(
                "small",
                device="cpu",
                compute_type="int8"
            )

            if self.stop_event.is_set():
                return

            # Create a temporary WAV file.
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp_file:
                audio_path = temp_file.name

            sample_rate = 16000
            device_id = 1

            self.status_changed.emit(
                "Recording... Click Stop when finished."
            )

            with sf.SoundFile(
                audio_path,
                mode="w",
                samplerate=sample_rate,
                channels=1,
                subtype="PCM_16"
            ) as wav_file:

                def audio_callback(
                    indata, frames, time_info, status
                ):
                    if status:
                        print("Audio status:", status)

                    wav_file.write(indata)

                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    device=device_id,
                    callback=audio_callback,
                    blocksize=16000
                ):
                    while not self.stop_event.wait(0.1):
                        pass

            self.status_changed.emit(
                "Recording stopped. Transcribing..."
            )

            # Check whether any audio was recorded.
            if os.path.getsize(audio_path) <= 44:
                self.transcript_ready.emit(
                    "No audio recorded. Please try again."
                )
                return

            self.status_changed.emit("Transcribing speech...")

            # Convert the recording into text.
            segments, _ = model.transcribe(
                audio_path,
                language="en",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False
            )

            text = " ".join(
                segment.text.strip()
                for segment in segments
            ).strip()

            if text:
                self.transcript_ready.emit(text)
            else:
                self.transcript_ready.emit(
                    "No speech detected. Please try again."
                )

        except Exception as error:
            self.error_occurred.emit(str(error))

        finally:
            # Remove the temporary audio file.
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
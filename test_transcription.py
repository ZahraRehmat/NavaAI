
from faster_whisper import WhisperModel

AUDIO_FILE = "microphone_test.wav"

print("Loading speech recognition model...")
print("The first run may download the model.")

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

print("Transcribing your recording...")

segments, info = model.transcribe(
    AUDIO_FILE,
    beam_size=5
)

text = " ".join(segment.text.strip() for segment in segments)

print("\n--- TRANSCRIPTION RESULT ---")
print(text if text else "No speech was detected.")
print("----------------------------")

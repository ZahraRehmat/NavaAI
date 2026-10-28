
import sounddevice as sd
import soundfile as sf

DURATION = 5
SAMPLE_RATE = 16000

print("Available microphones:")
print(sd.query_devices())

print("\nRecording starts in 2 seconds...")
import time
time.sleep(2)

print("Recording now! Speak into your microphone.")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32",
    device=1,
)

sd.wait()

sf.write("microphone_test.wav", audio, SAMPLE_RATE)

print("Recording saved as microphone_test.wav")

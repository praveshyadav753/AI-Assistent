import sounddevice as sd
from scipy.io.wavfile import write

# Settings
DURATION = 5  # seconds
SAMPLERATE = 44100  # Hz, standard for most mics
FILENAME = "output.wav"

print(f"Recording for {DURATION} seconds...")

# Record audio
try:
    recording = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=1)
    sd.wait()  # Wait until recording is finished
except Exception as e:
    print(f"Error accessing microphone: {e}")
    exit()

# Save as WAV file
write(FILENAME, SAMPLERATE, recording)
print(f"Recording saved as {FILENAME}")

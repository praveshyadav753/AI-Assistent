import struct
import pvporcupine
import pyaudio
import wave
import audioop

# -------------------------#
# CONFIG
# -------------------------#
SILENCE_THRESHOLD = 500         # Lower = more sensitive to noise
MAX_SILENCE_DURATION = 2        # Stop recording after 2 seconds of silence
OUTPUT_WAV = "input.wav"

# -------------------------#
# Utility Functions
# -------------------------#
def setup_wake_word():
    porcupine = pvporcupine.create(
        access_key="Xg0NgjiodpebDls2ulF4JYZpNy3NwuB9rdhSvuUaZiw21ZiWr7Y0Lg==",
        keyword_paths=["nesty.ppn"],
        sensitivities=[0.6]
    )
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    return porcupine, pa, stream

def listen_for_wake_word(porcupine, stream):
   
    while True:
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
        if porcupine.process(pcm_unpacked) >= 0:
            print("✅ Wake word detected!")
            break

def record_voice_command(stream, pa, sample_rate, frame_length, silence_threshold=SILENCE_THRESHOLD, max_silence_sec=MAX_SILENCE_DURATION, output_wav=OUTPUT_WAV):
    print("🎙️ Start speaking your command...")
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(sample_rate / frame_length * max_silence_sec)
    while True:
        data = stream.read(frame_length, exception_on_overflow=False)
        frames.append(data)
        rms = audioop.rms(data, 2)
        if rms < silence_threshold:
            silent_chunks += 1
        else:
            silent_chunks = 0
        if silent_chunks > max_silent_chunks:
            print("🛑 Stopped listening (silence detected).")
            break
    # Save to file
    wf = wave.open(output_wav, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"✅ Saved command to {output_wav}")

def cleanup_resources(stream, pa, porcupine):
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()

# -------------------------#
# Entry-point for Module
# -------------------------#
def handle_voice_command():
    porcupine, pa, stream = setup_wake_word()
    try:
        listen_for_wake_word(porcupine, stream)
        record_voice_command(
            stream,
            pa,
            porcupine.sample_rate,
            porcupine.frame_length,
        )
    finally:
        cleanup_resources(stream, pa, porcupine)

# Usage Example
if __name__ == "__main__":
    handle_voice_command()

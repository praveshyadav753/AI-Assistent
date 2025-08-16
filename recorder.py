
import wave
import audioop

SILENCE_THRESHOLD = 500
MAX_SILENCE_DURATION = 2
OUTPUT_WAV = "input.wav"

def record_voice_command(stream, pa, sample_rate, frame_length, silence_threshold=SILENCE_THRESHOLD, max_silence_sec=MAX_SILENCE_DURATION, output_wav=OUTPUT_WAV):
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
           
            break
    wf = wave.open(output_wav, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pa.get_sample_size(pa.get_format_from_width(2)))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
   

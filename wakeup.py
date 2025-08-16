import struct
import pvporcupine
import pyaudio

ACCESS_KEY = "Xg0NgjiodpebDls2ulF4JYZpNy3NwuB9rdhSvuUaZiw21ZiWr7Y0Lg=="
KEYWORD_PATHS = ["nesty.ppn"]

def setup_wake_word():
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=KEYWORD_PATHS,
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

def listen_for_wake_word(porcupine, stream, speak_callback=None):
    
    while True:
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
        if porcupine.process(pcm_unpacked) >= 0:
            
            if speak_callback:
                speak_callback("Yes boss....")
            break

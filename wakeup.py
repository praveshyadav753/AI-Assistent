import struct
import pvporcupine
import pyaudio
# Remove this line: from threading import Event

ACCESS_KEY = "Xg0NgjiodpebDls2ulF4JYZpNy3NwuB9rdhSvuUaZiw21ZiWr7Y0Lg=="
KEYWORD_PATHS = ["nesty.ppn"]

# Remove this line: direct_wakeup_flag = Event()

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

def listen_for_wake_word(porcupine, stream, speak_callback=None, direct_wakeup_flag=None):
    """
    Listen for wake word. Pass the flag as parameter.
    """
    try:
        while True:
            # Check if direct wakeup was triggered
            if direct_wakeup_flag and direct_wakeup_flag.is_set():
                print("[INFO] Direct wakeup detected, skipping wake word...")
                direct_wakeup_flag.clear()
                if speak_callback:
                    speak_callback("What can I help you with today?")
                return True

            # Normal wake word listening
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)

            if porcupine.process(pcm_unpacked) >= 0:
                print("Wake word detected!")
                if speak_callback:
                    speak_callback("Yes boss....")
                return True

    except Exception as e:
        print(f"[ERROR] Wake word listening failed: {e}")
        return False
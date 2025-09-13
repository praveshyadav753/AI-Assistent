import struct
import pvporcupine
import pyaudio
from typing import Callable

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

def listen_for_wake_word(porcupine, stream, speak_callback=None, direct_wakeup_flag=None,update_callback: Callable=None):
    """Efficiently listen for wake word or direct trigger."""
    unpack_fmt = f"{porcupine.frame_length}h"  # Precompute the format
    try:
        while True:
            if direct_wakeup_flag and direct_wakeup_flag.is_set():
                direct_wakeup_flag.clear()
                if speak_callback:
                    speak_callback("What can I help you with today?")
                break  # Use break instead of return for resource cleanup

            # Efficient stream read
            try:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            except IOError:
                continue  # Skip iteration if stream fails

            pcm_unpacked = struct.unpack_from(unpack_fmt, pcm)

            if porcupine.process(pcm_unpacked) >= 0:
               if update_callback:
                update_callback("wake_word_detected")

                if speak_callback:
                    speak_callback("What can I help you with today?")
                break  # Use break instead of return for cleanup
    except Exception as e:
        print(f"[ERROR] Wake word listening failed: {e}")
        return False
    finally:
        # Always release resources after detection/exception
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        porcupine.delete()
    return True

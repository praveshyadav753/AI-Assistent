import struct
import pvporcupine
import pyaudio
from typing import Callable
import time
import asyncio
ACCESS_KEY = "Xg0NgjiodpebDls2ulF4JYZpNy3NwuB9rdhSvuUaZiw21ZiWr7Y0Lg=="
KEYWORD_PATHS = ["nesty.ppn"]

def setup_wake_word():
    """Setup Porcupine wake word detection with error handling."""
    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keyword_paths=KEYWORD_PATHS,
            sensitivities=[0.6]
        )
        
        pa = pyaudio.PyAudio()
        
        # Find the best audio device
        device_index = None
        for i in range(pa.get_device_count()):
            device_info = pa.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                device_index = i
                break
        
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=porcupine.frame_length,
            start=True
        )
        
        print(f"[INFO] Wake word setup complete. Sample rate: {porcupine.sample_rate}")
        return porcupine, pa, stream
        
    except Exception as e:
        print(f"[ERROR] Failed to setup wake word detection: {e}")
        raise

def listen_for_wake_word(porcupine, stream, speak_callback=None, direct_wakeup_flag=None, update_callback: Callable=None):
    """Efficiently listen for wake word or direct trigger."""
    unpack_fmt = f"{porcupine.frame_length}h"
    consecutive_errors = 0
    max_errors = 10
    
    print("[INFO] Wake word detection active...")
    
    try:
        while True:
            # Check for direct wakeup first
            if direct_wakeup_flag and direct_wakeup_flag.is_set():

                print("[INFO] Direct wakeup flag detected")
                direct_wakeup_flag.clear()
                if update_callback:
                    update_callback("direct_wakeup")
                # if speak_callback:
                #     asyncio.run(speak_callback("What can I help you?"))
                return True

            # Read audio data with error handling
            try:
                if not stream.is_active():
                    print("[ERROR] Audio stream is not active")
                    return False
                    
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                consecutive_errors = 0  # Reset error counter on successful read
                
            except IOError as e:
                consecutive_errors += 1
                print(f"[WARN] Audio read error {consecutive_errors}/{max_errors}: {e}")
                
                if consecutive_errors >= max_errors:
                    print("[ERROR] Too many consecutive audio errors")
                    return False
                    
                time.sleep(0.01)  # Brief pause before retry
                continue

            # Process audio for wake word
            try:
                pcm_unpacked = struct.unpack_from(unpack_fmt, pcm)
                result = porcupine.process(pcm_unpacked)
                
                if result >= 0:
                    print(f"[INFO] Wake word detected! (keyword index: {result})")
                    if update_callback:
                        update_callback("wake_word_detected")
                    # if speak_callback:
                    #  asyncio.run(speak_callback("What can I help you?")) 
                    return True
                    
            except struct.error as e:
                print(f"[ERROR] Audio processing error: {e}")
                continue
            except Exception as e:
                print(f"[ERROR] Porcupine processing error: {e}")
                return False
                
    except KeyboardInterrupt:
        print("\n[INFO] Wake word detection interrupted by user")
        return False
    except Exception as e:
        print(f"[ERROR] Wake word listening failed: {e}")
        return False
    finally:
        # Cleanup is handled in main.py
        pass
        
    return False
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import time
import threading
import sys
from speak import speak_response

# Load Vosk model
try:
    model = Model("./vosk-model-en-in-0.5/vosk-model-en-in-0.5")
    print("[INFO] Vosk model loaded successfully")
except Exception as e:
    print(f"[ERROR] Failed to load Vosk model: {e}")
    sys.exit(1)

recognizer = KaldiRecognizer(model, 16000)

# Parameters
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1  # Smaller chunks for better responsiveness
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
DEFAULT_TIMEOUT = 10  # seconds
SILENCE_TIMEOUT = 3   # seconds of silence to auto-stop
MIN_SPEECH_LENGTH = 2  # minimum characters for valid speech
AUDIO_THRESHOLD = 100  # minimum audio level to consider as speech

class SpeechToText:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.last_partial_text = ""
        
    def audio_callback(self, indata, frames, time, status):
        """Audio callback function - runs in separate thread"""
        if status:
            print(f"\n[AUDIO WARNING] {status}")
        
        # Only add to queue if we're actively listening
        if self.is_listening:
            self.audio_queue.put(indata.copy())
    
    def detect_speech_activity(self, audio_data):
        """Simple voice activity detection"""
        import numpy as np
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        return rms > AUDIO_THRESHOLD
    
    def clear_line(self):
        """Clear the current line in terminal"""
        print('\r' + ' ' * 80 + '\r', end='', flush=True)
    
    def listen_and_recognize(self, timeout=DEFAULT_TIMEOUT, direct_wakeup_flag=None):
        """
        Main speech recognition function with comprehensive error handling
        """
        print(f"[INFO] Starting speech recognition (timeout: {timeout}s)")
        
        # Wait for any system audio to finish (prevent feedback)
        time.sleep(0.8)
        
        # Clear the audio queue and reset recognizer
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        recognizer.Reset()
        
        final_text = ""
        start_time = time.time()
        last_speech_time = start_time
        speech_detected = False
        partial_displayed = False
        
        try:
            # Start audio stream
            with sd.InputStream(
                channels=1, 
                samplerate=SAMPLE_RATE, 
                dtype='int16',
                blocksize=CHUNK_SIZE, 
                callback=self.audio_callback
            ):
                self.is_listening = True
                print("🎤 Listening... Speak now! (or say 'stop' to end)")
                
                while True:
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    
                    # Check for direct wakeup interruption
                    if direct_wakeup_flag and direct_wakeup_flag.is_set():
                        print("\n[INFO] Interrupted by direct wakeup")
                        break
                    
                    # Check timeout
                    if elapsed_time > timeout:
                        self.clear_line()
                        print(f"\n⏰ [TIMEOUT] No speech detected in {timeout} seconds")
                        break
                    
                    # Check silence timeout (only after speech was detected)
                    if speech_detected and (current_time - last_speech_time) > SILENCE_TIMEOUT:
                        self.clear_line()
                        print(f"\n🔇 [SILENCE] Stopped after {SILENCE_TIMEOUT}s of silence")
                        break
                    
                    # Process audio data
                    if not self.audio_queue.empty():
                        try:
                            data = self.audio_queue.get_nowait()
                            
                            # Check for speech activity
                            has_speech = self.detect_speech_activity(data)
                            if has_speech:
                                speech_detected = True
                                last_speech_time = current_time
                            
                            # Get partial results (live transcription)
                            partial_result = json.loads(recognizer.PartialResult())
                            partial_text = partial_result.get("partial", "").strip()
                            
                            # Display partial text with better formatting
                            if partial_text != self.last_partial_text:
                                self.clear_line()
                                if partial_text:
                                    print(f"🗣️  {partial_text}...", end='', flush=True)
                                    partial_displayed = True
                                self.last_partial_text = partial_text
                            
                            # Process final results
                            if recognizer.AcceptWaveform(data.tobytes()):
                                result = json.loads(recognizer.Result())
                                text = result.get("text", "").strip()
                                
                                if text:
                                    # Clear partial display
                                    if partial_displayed:
                                        self.clear_line()
                                        partial_displayed = False
                                    
                                    # Check for stop command
                                    if text.lower() in ['stop', 'quit', 'exit', 'cancel']:
                                        print(f"✅ Stop command detected: '{text}'")
                                        final_text = ""
                                        break
                                    
                                    # Add to final text
                                    if final_text:
                                        final_text += " " + text
                                    else:
                                        final_text = text
                                    
                                    print(f"✅ Recognized: '{text}'")
                                    
                                    # Continue listening for more speech
                                    continue
                                    
                        except queue.Empty:
                            continue
                        except Exception as e:
                            print(f"\n[ERROR] Audio processing failed: {e}")
                            continue
                    
                    # Small delay to prevent busy waiting
                    time.sleep(0.01)
                    
        except KeyboardInterrupt:
            print("\n[INFO] Speech recognition interrupted by user")
        except Exception as e:
            print(f"\n[ERROR] Audio stream failed: {e}")
            return ""
        finally:
            self.is_listening = False
            # Clear any remaining partial text display
            if partial_displayed:
                self.clear_line()
        
        # Process final result
        final_text = final_text.strip()
        
        if final_text:
            # Validate minimum length
            if len(final_text) < MIN_SPEECH_LENGTH:
                print(f"[WARN] Speech too short: '{final_text}' (minimum {MIN_SPEECH_LENGTH} chars)")
                return ""
            
            print(f"🎯 Final result: '{final_text}'")
            return final_text
        else:
            if speech_detected:
                print("[INFO] Speech detected but not clearly recognized")
            else:
                print("[INFO] No speech detected")
            return ""

# Global instance
speech_to_text = SpeechToText()

def listen_and_recognize(timeout=DEFAULT_TIMEOUT, direct_wakeup_flag=None):
    """
    Main function to be called from other modules
    """
    return speech_to_text.listen_and_recognize(timeout, direct_wakeup_flag)

# Test function
def test_speech_recognition():
    """Test the speech recognition system"""
    print("🧪 Testing Speech Recognition System")
    print("=" * 50)
    
    while True:
        print("\n1. Start listening")
        print("2. Exit")
        choice = input("Choose option: ").strip()
        
        if choice == '1':
            result = listen_and_recognize(timeout=15)
            if result:
                print(f"\n✅ SUCCESS: '{result}'")
            else:
                print("\n❌ No speech recognized")
        elif choice == '2':
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    test_speech_recognition()
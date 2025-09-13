# import asyncio
# import edge_tts
# import sounddevice as sd
# import soundfile as sf

# VOICE = "en-US-AvaNeural"
# OUTPUT_WAV = "response.wav"

# async def synthesize_text_to_speech(text="Hello...!", output_wav=OUTPUT_WAV, voice=VOICE):
#     communicate = edge_tts.Communicate(text, voice)
#     await communicate.save(output_wav)
#     data, samplerate = sf.read(output_wav, dtype='float32')
#     sd.play(data, samplerate)
#     sd.wait()

# def speak_response(text):
#     asyncio.run(synthesize_text_to_speech(text))


import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
import threading
import queue
import time
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
import uuid

# Optimized settings
VOICE = "en-US-AvaNeural"  # Keep your preferred voice
TEMP_DIR = tempfile.gettempdir()
SPEECH_RATE = "+10%"  # Slightly faster speech
SPEECH_PITCH = "+0Hz"  # Normal pitch

class FastEdgeTTS:
    def __init__(self):
        self.speech_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="EdgeTTS")
        self.is_speaking = False
        self.current_playback = None
        self.speech_queue = queue.Queue()
        
    async def synthesize_fast(self, text, voice=VOICE, rate=SPEECH_RATE):
        """Optimized synthesis with speed improvements"""
        # Create unique filename to avoid conflicts
        output_wav = os.path.join(TEMP_DIR, f"tts_{uuid.uuid4().hex[:8]}.wav")
        
        try:
            # Create communicate object with speed optimization
            communicate = edge_tts.Communicate(
                text, 
                voice,
                rate=rate,
                pitch=SPEECH_PITCH
            )
            
            # Save to temporary file
            await communicate.save(output_wav)
            return output_wav
            
        except Exception as e:
            print(f"[ERROR] TTS synthesis failed: {e}")
            return None
    
    def play_audio_fast(self, wav_file):
        """Fast audio playback with cleanup"""
        try:
            if not os.path.exists(wav_file):
                print(f"[ERROR] Audio file not found: {wav_file}")
                return False
                
            # Load and play audio
            data, samplerate = sf.read(wav_file, dtype='float32')
            
            # Store reference for potential interruption
            self.current_playback = (data, samplerate)
            
            # Play audio
            sd.play(data, samplerate)
            sd.wait()  # Wait for playback to complete
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Audio playback failed: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                if os.path.exists(wav_file):
                    os.remove(wav_file)
            except:
                pass
            self.current_playback = None
    
    def speak_blocking(self, text):
        """Blocking speech synthesis and playback"""
        if not text.strip():
            return
            
        try:
            self.is_speaking = True
            print(f"🔊 Speaking: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Run async synthesis in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            wav_file = loop.run_until_complete(
                self.synthesize_fast(text, rate=SPEECH_RATE)
            )
            loop.close()
            
            if wav_file:
                self.play_audio_fast(wav_file)
                
        except Exception as e:
            print(f"[ERROR] Blocking speech failed: {e}")
        finally:
            self.is_speaking = False
    
    def speak_async(self, text):
        """Non-blocking speech synthesis"""
        if not text.strip():
            return
            
        def _async_speak():
            self.speak_blocking(text)
        
        # Submit to thread pool
        future = self.speech_executor.submit(_async_speak)
        return future
    
    def speak_priority(self, text):
        """Priority speech - interrupts current speech"""
        if not text.strip():
            return
            
        try:
            # Stop current playback
            self.stop_current_speech()
            
            # Clear speech queue
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Speak immediately
            self.speak_blocking(text)
            
        except Exception as e:
            print(f"[ERROR] Priority speech failed: {e}")
    
    def stop_current_speech(self):
        """Stop current speech playback"""
        try:
            sd.stop()  # Stop sounddevice playback
            self.is_speaking = False
        except Exception as e:
            print(f"[ERROR] Failed to stop speech: {e}")
    
    def is_currently_speaking(self):
        """Check if currently speaking"""
        return self.is_speaking
    
    def wait_for_completion(self, timeout=10):
        """Wait for current speech to complete"""
        start_time = time.time()
        while self.is_speaking and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        return not self.is_speaking
    
    def shutdown(self):
        """Clean shutdown"""
        try:
            self.stop_current_speech()
            self.speech_executor.shutdown(wait=True, timeout=3)
            print("[INFO] Edge TTS shutdown complete")
        except Exception as e:
            print(f"[ERROR] TTS shutdown error: {e}")

# Global fast TTS instance
fast_tts = FastEdgeTTS()

# Compatibility functions for your existing code
async def synthesize_text_to_speech(text="Hello...!", output_wav=None, voice=VOICE):
    """Original function for backward compatibility"""
    if output_wav is None:
        output_wav = os.path.join(TEMP_DIR, f"response_{uuid.uuid4().hex[:8]}.wav")
    
    try:
        communicate = edge_tts.Communicate(text, voice, rate=SPEECH_RATE)
        await communicate.save(output_wav)
        
        data, samplerate = sf.read(output_wav, dtype='float32')
        sd.play(data, samplerate)
        sd.wait()
        
        # Cleanup
        if os.path.exists(output_wav):
            os.remove(output_wav)
            
    except Exception as e:
        print(f"[ERROR] Legacy TTS failed: {e}")

def speak_response(text, blocking=False, priority=False):
    """
    Main speech function with multiple modes:
    - blocking=False (default): Non-blocking async speech
    - blocking=True: Wait for speech to complete  
    - priority=True: Interrupt current speech
    """
    if not text or not text.strip():
        return
    
    if priority:
        fast_tts.speak_priority(text)
    elif blocking:
        fast_tts.speak_blocking(text)
    else:
        fast_tts.speak_async(text)

# Additional convenience functions
def speak_async(text):
    """Non-blocking speech"""
    return fast_tts.speak_async(text)

def speak_immediate(text):
    """Blocking speech"""
    fast_tts.speak_blocking(text)

def speak_priority(text):
    """Priority speech (interrupts current)"""
    fast_tts.speak_priority(text)

def is_speaking():
    """Check if currently speaking"""
    return fast_tts.is_currently_speaking()

def stop_speaking():
    """Stop current speech"""
    fast_tts.stop_current_speech()

def wait_for_speech(timeout=10):
    """Wait for speech to complete"""
    return fast_tts.wait_for_completion(timeout)

# Cleanup function
def cleanup_speech():
    """Clean shutdown"""
    fast_tts.shutdown()

# Quick test function
async def test_fast_tts():
    """Test the optimized TTS system"""
    print("🧪 Testing Fast Edge TTS")
    
    # Test 1: Async speech
    print("1. Testing async speech...")
    speak_async("This is asynchronous speech using Edge TTS")
    
    await asyncio.sleep(1)
    
    # Test 2: Blocking speech  
    print("2. Testing blocking speech...")
    speak_immediate("This is immediate blocking speech")
    
    # Test 3: Priority speech
    print("3. Testing priority speech...")
    speak_async("This message will be interrupted")
    await asyncio.sleep(0.5)
    speak_priority("Priority message using Edge TTS!")
    
    await asyncio.sleep(2)
    print("✅ All tests complete")

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_fast_tts())
    cleanup_speech()
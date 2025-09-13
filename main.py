from wakeup import setup_wake_word, listen_for_wake_word
from speak import speak_response
from speachtotext import listen_and_recognize
from intent_handler import handle_user_request
import asyncio
from typing import Callable 
import traceback
import time
import threading

# Shared flag for direct wakeup
direct_wakeup_flag = threading.Event()

def cleanup_resources(stream, pa, porcupine):
    """Safely close audio streams and resources."""
    try:
        if stream and hasattr(stream, 'is_active') and stream.is_active():
            stream.stop_stream()
        if stream:
            stream.close()
        if pa:
            pa.terminate()
        if porcupine:
            porcupine.delete()
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")

def handle_voice_command(update_callback: Callable):
    """Main loop for wake word listening and handling commands."""
    print("[INFO] Voice assistant thread started")
    update_callback("status_update", {"message": "Voice assistant ready. Waiting for wake word..."})
    
    while True:
        porcupine, pa, stream = None, None, None
        try:
            # Setup wake word detection
            update_callback("status_update", {"message": "Setting up wake word detection..."})
            porcupine, pa, stream = setup_wake_word()
            
            # Check if direct wakeup is triggered
            if direct_wakeup_flag.is_set():
                print("[INFO] Direct wakeup triggered. Skipping wake word detection...")
                update_callback("direct_wakeup", {"message": "Direct wakeup activated"})
                speak_response("What can I help you with?")
                direct_wakeup_flag.clear()  # Reset the flag
            else:
                # Wait for wake word
                print("[INFO] Waiting for wake word...")
                update_callback("status_update", {"message": "Waiting for wake word 'Hey Nesty'..."})
                
                wake_detected = listen_for_wake_word(
                    porcupine, 
                    stream, 
                    speak_callback=speak_response,
                    direct_wakeup_flag=direct_wakeup_flag,
                    update_callback=update_callback
                )
                
                if not wake_detected:
                    print("[INFO] Wake word detection interrupted")
                    continue

            # Listen and process command
            print("[INFO] Listening for command...")
            update_callback("listening_started", {"message": "Listening for your command..."})
            
            command_text = listen_and_recognize(
                timeout=10, 
                direct_wakeup_flag=direct_wakeup_flag
            )

            if not command_text or not command_text.strip():
                update_callback("status_update", {"message": "Didn't catch that. Try again."})
                speak_response("I didn't catch that. Please try again.")
                continue

            print(f"[INFO] Command recognized: {command_text}")
            update_callback("command_recognized", {"command": command_text})

            # Handle the command asynchronously
            update_callback("response_generated", {"message": "Processing your command..."})
            
            # Create new event loop for async operations
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(handle_user_request(command_text,update_callback=update_callback))
            except Exception as cmd_error:
                print(f"[ERROR] Command handling failed: {cmd_error}")
                update_callback("error", {"message": "Sorry, I encountered an error processing your command."})
                speak_response("Sorry, I encountered an error processing your command.")
            finally:
                try:
                    loop.close()
                except:
                    pass
            
            update_callback("speaking_finished", {"message": "Command completed."})

        except KeyboardInterrupt:
            print("\n[INFO] Voice assistant stopped by user.")
            break

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            update_callback("status_update", {"message": f"Error occurred: {str(e)}"})
            print("[INFO] Restarting loop in 2 seconds...")
            time.sleep(2)

        finally:
            cleanup_resources(stream, pa, porcupine)
            # Small delay before next iteration
            time.sleep(0.5)
            
    print("[INFO] Voice assistant thread ended")
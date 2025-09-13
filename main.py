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
        if stream:
            stream.stop_stream()
            stream.close()
        if pa:
            pa.terminate()
        if porcupine:
            porcupine.delete()
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")

def handle_voice_command(update_callback: Callable):
    """Main loop for wake word listening and handling commands."""
    while True:
        porcupine, pa, stream = None, None, None
        try:
            # Setup wake word detection
            porcupine, pa, stream = setup_wake_word()

            # Check if direct wakeup is triggered
            if direct_wakeup_flag.is_set():
                print("[INFO] Direct wakeup triggered. Skipping wake word detection...")
                speak_response("What can I help you with?")
                direct_wakeup_flag.clear()  # Reset the flag
            else:
                # Wait for wake word - PASS THE FLAG HERE
                print("[INFO] Waiting for wake word...")
                listen_for_wake_word(
                    porcupine, 
                    stream, 
                    speak_callback=speak_response,
                    direct_wakeup_flag=direct_wakeup_flag , # ← Pass the flag!
                    update_callback=update_callback # <-- Pass it down

                )

            # Listen and process command
            # print("[INFO] Listening for command...")
            update_callback("listening_started")
            command_text = listen_and_recognize()

            if not command_text.strip():
                update_callback("status_update", {"message": "Didn't catch that. Try again."})
                continue

            update_callback("command_recognized", {"command": command_text})

            # Handle the command asynchronously
            asyncio.run(handle_user_request(command_text))

        except KeyboardInterrupt:
            # print("\n[INFO] Voice assistant stopped by user.")
            break

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            # print("[INFO] Restarting loop in 2 seconds...")
            time.sleep(2)

        finally:
            cleanup_resources(stream, pa, porcupine)
            # print("\n[INFO] Ready for next wake word / direct command...\n")
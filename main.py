from wakeup import setup_wake_word, listen_for_wake_word
from speak import speak_response
from speachtotext import listen_and_recognize
from intent_handler import handle_user_request
import asyncio
import traceback
import time


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


def handle_voice_command():
    """Main loop for wake word listening and handling commands."""
    while True:
        porcupine, pa, stream = None, None, None
        try:
            # Setup wake word detection
            porcupine, pa, stream = setup_wake_word()

            # Wait for wake word
            print("[INFO] Waiting for wake word...")
            listen_for_wake_word(porcupine, stream, speak_callback=speak_response)

            # Listen and process speech
            print("[INFO] Listening for command...")
            command_text = listen_and_recognize()

            if not command_text.strip():
                print("[WARN] No command detected. Restarting wake word listening...")
                continue  # Skip to next wake word

            print(f"[DEBUG] Recognized command: {command_text}")

            # Handle the command asynchronously
            asyncio.run(handle_user_request(command_text))

        except KeyboardInterrupt:
            print("\n[INFO] Voice assistant stopped by user.")
            break

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            print("[INFO] Restarting wake word loop in 2 seconds...")
            time.sleep(2)  # Avoid rapid restart loops

        finally:
            cleanup_resources(stream, pa, porcupine)
            print("\n[INFO] Ready for next wake word...\n")


if __name__ == "__main__":
    handle_voice_command()

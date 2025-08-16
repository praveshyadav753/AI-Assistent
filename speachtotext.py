import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
from speak import speak_response

# Load Vosk model
# model = Model("./vosk-model-small-en-in-0.4/vosk-model-small-en-in-0.4")
# model = Model("./vosk-model-en-us-0.22-lgraph/vosk-model-en-us-0.22-lgraph")
model = Model("./vosk-model-en-in-0.5/vosk-model-en-in-0.5")

recognizer = KaldiRecognizer(model, 16000)

# Parameters
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.6  # seconds per chunk
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

def listen_and_recognize():
    q = queue.Queue()

    def audio_callback(indata, frames, time, status):
        q.put(indata.copy())

    final_text = ""

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16',
                        blocksize=CHUNK_SIZE, callback=audio_callback):
        print("Listening... Speak now!")

        while True:
            if not q.empty():
                data = q.get()

                # Partial recognition (live feedback)
                partial_result = json.loads(recognizer.PartialResult())
                partial_text = partial_result.get("partial", "")
                if partial_text:
                    print("Partial:", partial_text, end="\r")  # updates in place

                # Final recognition
                if recognizer.AcceptWaveform(data.tobytes()):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()

                    if text:
                        final_text += " " + text
                    else:
                        speak_response("I didn't understand that")
                        continue

                    # Stop after Vosk returns a final result
                    break

    return final_text.strip()


# Example usage
if __name__ == "__main__":
    recognized_text = listen_and_recognize()
    print("\nFinal recognized text:", recognized_text)

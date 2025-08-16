import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf

VOICE = "en-US-AvaNeural"
OUTPUT_WAV = "response.wav"

async def synthesize_text_to_speech(text="Hello...!", output_wav=OUTPUT_WAV, voice=VOICE):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_wav)
    data, samplerate = sf.read(output_wav, dtype='float32')
    sd.play(data, samplerate)
    sd.wait()

def speak_response(text):
    asyncio.run(synthesize_text_to_speech(text))



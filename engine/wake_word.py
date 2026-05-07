import numpy as np
import pyaudio
import logging
from openwakeword.model import Model

logger = logging.getLogger(__name__)

def wake_word_detection(oww_model: Model) -> None:
    
    audio = pyaudio.PyAudio()

    mic_stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1280
    )
    
    logger.info("Waiting for wake word 'Jarvis'...")
    wake_word_detected = False
    while not wake_word_detected:
        audio_chunk = np.frombuffer(mic_stream.read(1280, exception_on_overflow=False), dtype=np.int16)
        prediction = oww_model.predict(audio_chunk)

        print(f"\rListening... (jarvis: {prediction.get('jarvis', 0.0):.2f})", end="")

        if prediction.get("jarvis", 0.0) > 0.3:
            wake_word_detected = True
            print("\n[Wake Word Detected!]")
            print('\a')
    mic_stream.stop_stream()
    mic_stream.close()
    audio.terminate()



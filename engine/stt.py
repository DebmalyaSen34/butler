import speech_recognition as sr
import mlx_whisper
import numpy as np

def speech_to_text(recognizer):
    with sr.Microphone(sample_rate=16000) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("[Listening to command...]")

        audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=30)

    print("[Processing audio...]")

    raw_data = audio_data.get_raw_data()
    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

    result = mlx_whisper.transcribe(audio_np, path_or_hf_repo="mlx-community/whisper-tiny-mlx")
    user_text = str(result.get("text", "")).strip() if isinstance(result, dict) else str(result).strip()

    return user_text

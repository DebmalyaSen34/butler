from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import speech_recognition as sr


@dataclass(frozen=True)
class SpeechConfig:
    whisper_model: str = "mlx-community/whisper-small-mlx"
    initial_prompt: str = "Jarvis voice assistant commands. Transcribe concise spoken user requests accurately."
    sample_rate: int = 16000
    timeout_seconds: float = 8
    phrase_time_limit_seconds: float = 30
    follow_up_timeout_seconds: float = 6
    retry_attempts: int = 1
    ambient_noise_seconds: float = 0.5
    energy_threshold: int = 300
    dynamic_energy_threshold: bool = True
    pause_threshold: float = 0.75
    microphone_device_index: int | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    audio_seconds: float
    rms: float
    no_speech_probability: float | None = None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


def build_speech_config(settings: dict[str, Any], microphone_device_index: int | None = None) -> SpeechConfig:
    if microphone_device_index == -1:
        microphone_device_index = None

    return SpeechConfig(
        whisper_model=str(settings.get("whisper_model", "mlx-community/whisper-small-mlx")),
        initial_prompt=str(settings.get("initial_prompt", SpeechConfig.initial_prompt)),
        sample_rate=int(settings.get("sample_rate", 16000)),
        timeout_seconds=float(settings.get("timeout_seconds", 8)),
        phrase_time_limit_seconds=float(settings.get("phrase_time_limit_seconds", 30)),
        follow_up_timeout_seconds=float(settings.get("follow_up_timeout_seconds", 6)),
        retry_attempts=int(settings.get("retry_attempts", 1)),
        ambient_noise_seconds=float(settings.get("ambient_noise_seconds", 0.5)),
        energy_threshold=int(settings.get("energy_threshold", 300)),
        dynamic_energy_threshold=bool(settings.get("dynamic_energy_threshold", True)),
        pause_threshold=float(settings.get("pause_threshold", 0.75)),
        microphone_device_index=microphone_device_index,
    )


def configure_recognizer(recognizer: sr.Recognizer, config: SpeechConfig) -> None:
    recognizer.dynamic_energy_threshold = config.dynamic_energy_threshold
    recognizer.energy_threshold = config.energy_threshold
    recognizer.pause_threshold = config.pause_threshold


def _audio_rms(audio_np: np.ndarray) -> float:
    import numpy as np

    if audio_np.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_np))))


def speech_to_text(
    recognizer: sr.Recognizer,
    config: SpeechConfig,
    *,
    timeout_seconds: float | None = None,
    status_label: str = "Listening",
) -> TranscriptionResult:
    configure_recognizer(recognizer, config)

    with sr.Microphone(sample_rate=config.sample_rate, device_index=config.microphone_device_index) as source:
        recognizer.adjust_for_ambient_noise(source, duration=config.ambient_noise_seconds)
        print(f"[{status_label}] Start speaking. I will stop when you pause...")
        audio_data = recognizer.listen(
            source,
            timeout=timeout_seconds if timeout_seconds is not None else config.timeout_seconds,
            phrase_time_limit=config.phrase_time_limit_seconds,
        )

    raw_data = audio_data.get_raw_data()
    sample_width = audio_data.sample_width or 2
    audio_seconds = len(raw_data) / float(config.sample_rate * sample_width)

    import mlx_whisper
    import numpy as np

    audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    level = _audio_rms(audio_np)

    print(f"[Heard audio] {audio_seconds:.1f}s captured, level {level:.3f}. Transcribing...")

    result = mlx_whisper.transcribe(
        audio_np,
        path_or_hf_repo=config.whisper_model,
        initial_prompt=config.initial_prompt,
    )

    user_text = str(result.get("text", "")).strip() if isinstance(result, dict) else str(result).strip()
    no_speech_probability = None
    if isinstance(result, dict) and result.get("segments"):
        first_segment = result["segments"][0]
        no_speech_probability = first_segment.get("no_speech_prob")

    return TranscriptionResult(
        text=user_text,
        audio_seconds=audio_seconds,
        rms=level,
        no_speech_probability=no_speech_probability,
    )

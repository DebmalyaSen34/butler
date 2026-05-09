from __future__ import annotations

import logging
import select
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openwakeword.model import Model

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WakeWordConfig:
    models: tuple[str, ...] = ("jarvis",)
    threshold: float = 0.35
    smoothing_window: int = 4
    required_hits: int = 2
    cooldown_seconds: float = 1.2
    sample_rate: int = 16000
    frame_size: int = 1280
    debug: bool = True
    push_to_talk: bool = True
    push_to_talk_key: str = "enter"
    calibration_seconds: float = 1.5
    microphone_device_index: int | None = None


@dataclass(frozen=True)
class WakeDiagnostics:
    trigger: str
    model_scores: dict[str, float]
    smoothed_scores: dict[str, float]
    ambient_rms: float
    ambient_dbfs: float
    input_rms: float
    recommended_threshold: float


class WakeWordSmoother:
    def __init__(self, models: tuple[str, ...], window_size: int, required_hits: int, threshold: float):
        self.models = models
        self.window_size = max(1, window_size)
        self.required_hits = max(1, required_hits)
        self.threshold = threshold
        self._scores = {model: deque(maxlen=self.window_size) for model in models}

    def update(self, prediction: dict[str, float]) -> tuple[str | None, dict[str, float]]:
        smoothed: dict[str, float] = {}
        for model in self.models:
            score = float(prediction.get(model, 0.0))
            self._scores[model].append(score)
            values = list(self._scores[model])
            smoothed[model] = sum(values) / len(values)

            hits = sum(1 for value in values if value >= self.threshold)
            if hits >= self.required_hits and smoothed[model] >= self.threshold:
                return model, smoothed

        return None, smoothed


def build_wake_config(settings: dict[str, Any]) -> WakeWordConfig:
    device_index = settings.get("microphone_device_index", -1)
    if device_index == -1:
        device_index = None

    return WakeWordConfig(
        models=tuple(settings.get("models", ["jarvis"])),
        threshold=float(settings.get("threshold", 0.35)),
        smoothing_window=int(settings.get("smoothing_window", 4)),
        required_hits=int(settings.get("required_hits", 2)),
        cooldown_seconds=float(settings.get("cooldown_seconds", 1.2)),
        sample_rate=int(settings.get("sample_rate", 16000)),
        frame_size=int(settings.get("frame_size", 1280)),
        debug=bool(settings.get("debug", True)),
        push_to_talk=bool(settings.get("push_to_talk", True)),
        push_to_talk_key=str(settings.get("push_to_talk_key", "enter")),
        calibration_seconds=float(settings.get("calibration_seconds", 1.5)),
        microphone_device_index=device_index,
    )


def rms(audio_chunk: np.ndarray) -> float:
    import numpy as np

    if audio_chunk.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_chunk.astype(np.float32)))))


def rms_to_dbfs(value: float) -> float:
    import numpy as np

    if value <= 0:
        return -120.0
    return float(20 * np.log10(value / 32768.0))


def recommend_threshold(ambient_rms: float, base_threshold: float) -> float:
    if ambient_rms > 1800:
        return min(0.65, max(base_threshold, 0.5))
    if ambient_rms > 900:
        return min(0.55, max(base_threshold, 0.42))
    if ambient_rms < 150:
        return max(0.25, min(base_threshold, 0.35))
    return base_threshold


def _stdin_triggered() -> bool:
    if not sys.stdin.isatty():
        return False
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return False
    sys.stdin.readline()
    return True


def _open_stream(audio: pyaudio.PyAudio, config: WakeWordConfig):
    import pyaudio

    return audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=config.sample_rate,
        input=True,
        input_device_index=config.microphone_device_index,
        frames_per_buffer=config.frame_size,
    )


def calibrate_microphone(config: WakeWordConfig) -> tuple[float, float, float]:
    import numpy as np
    import pyaudio

    audio = pyaudio.PyAudio()
    stream = _open_stream(audio, config)
    samples = []
    frames = max(1, int(config.sample_rate * config.calibration_seconds / config.frame_size))

    try:
        for _ in range(frames):
            chunk = np.frombuffer(
                stream.read(config.frame_size, exception_on_overflow=False),
                dtype=np.int16,
            )
            samples.append(rms(chunk))
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    ambient_rms = float(sum(samples) / len(samples)) if samples else 0.0
    return ambient_rms, rms_to_dbfs(ambient_rms), recommend_threshold(ambient_rms, config.threshold)


def wake_word_detection(oww_model: Model, config: WakeWordConfig) -> WakeDiagnostics:
    import numpy as np
    import pyaudio

    audio = pyaudio.PyAudio()
    stream = _open_stream(audio, config)
    smoother = WakeWordSmoother(
        config.models,
        config.smoothing_window,
        config.required_hits,
        config.threshold,
    )

    ambient_rms = 0.0
    ambient_dbfs = -120.0
    recommended = config.threshold
    logger.info("Waiting for wake word %s...", ", ".join(config.models))

    trigger = ""
    raw_scores: dict[str, float] = {}
    smoothed_scores: dict[str, float] = {}
    input_rms = 0.0
    last_debug = 0.0

    try:
        while not trigger:
            audio_chunk = np.frombuffer(
                stream.read(config.frame_size, exception_on_overflow=False),
                dtype=np.int16,
            )
            input_rms = rms(audio_chunk)
            prediction = oww_model.predict(audio_chunk)
            raw_scores = {model: float(prediction.get(model, 0.0)) for model in config.models}
            detected_model, smoothed_scores = smoother.update(raw_scores)

            if config.debug and time.monotonic() - last_debug > 0.2:
                score_text = " ".join(
                    f"{model}: {raw_scores.get(model, 0.0):.2f}/{smoothed_scores.get(model, 0.0):.2f}"
                    for model in config.models
                )
                print(
                    f"\rSleeping | {score_text} | mic {rms_to_dbfs(input_rms):.0f} dBFS | Enter = talk",
                    end="",
                )
                last_debug = time.monotonic()

            if config.push_to_talk and _stdin_triggered():
                trigger = "push_to_talk"
                break

            if detected_model:
                trigger = detected_model
                break
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    if trigger != "push_to_talk":
        time.sleep(config.cooldown_seconds)

    print("\n[Wake Word Detected!]" if trigger != "push_to_talk" else "\n[Push-to-talk]")
    print("\a")

    return WakeDiagnostics(
        trigger=trigger,
        model_scores=raw_scores,
        smoothed_scores=smoothed_scores,
        ambient_rms=ambient_rms,
        ambient_dbfs=ambient_dbfs,
        input_rms=input_rms,
        recommended_threshold=recommended,
    )

from __future__ import annotations

from collections.abc import Callable, Iterable

import sounddevice as sd


def text_to_speech(
    pipeline,
    text_generator: Iterable[str],
    target_voice: str,
    interrupt_checker: Callable[[], bool] | None = None,
) -> bool:
    was_interrupted = False
    for sentence in text_generator:
        if not sentence:
            continue
        if interrupt_checker and interrupt_checker():
            was_interrupted = True
            break
        try:
            generator = pipeline(sentence, voice=target_voice)
            for i, (gs, ps, audio_chunk) in enumerate(generator):
                if interrupt_checker and interrupt_checker():
                    was_interrupted = True
                    break
                sd.play(audio_chunk, samplerate=24000)
                sd.wait()
            if was_interrupted:
                sd.stop()
                break
        except BaseException as e:
            print(f"TTS Error on '{sentence}': {e}")
    return was_interrupted


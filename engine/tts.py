import sounddevice as sd

def text_to_speech(pipeline, gemma_reply, target_voice):
    generator = pipeline(gemma_reply, voice=target_voice)

    for i, (gs, ps, audio_chunk) in enumerate(generator):
        sd.play(audio_chunk, samplerate=24000)
        sd.wait()



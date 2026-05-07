import logging
import speech_recognition as sr
from kokoro import KPipeline
from openwakeword.model import Model
from core.llm import generate_response
from engine.wake_word import wake_word_detection
from engine.stt import speech_to_text
from engine.tts import text_to_speech
from utils.audio import play_status_sound
from rich.console import Console
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")
console = Console()

def main():
    logger.info("Initializing TTS and engines...")
    
    recognizer = sr.Recognizer()

    pipeline = KPipeline(lang_code='a')
    target_voice = "af_heart"

    import openwakeword
    openwakeword.utils.download_models()

    console.print("[bold cyan]Loading Wake Word Engine...[/bold cyan]")
    oww_model = Model(wakeword_models=["jarvis"], inference_framework="onnx")
    
    console.print("\n[bold green]===============================[/bold green]")
    console.print("[bold green]Pipeline Ready. Say 'Jarvis' to wake me.[/bold green]")
    console.print("[bold green]===============================[/bold green]")

    while True:
        # Phase 1: Wake Word
        try:
            wake_word_detection(oww_model)
            play_status_sound("wake")
            console.print("\n[bold yellow][Wake Word Detected!] Listening...[/bold yellow]")
        except Exception as e:
            logger.error(f"Error in pipeline: {e}", exc_info=True)
       
        # Phase 2: Active Listening
        try:
            user_text = speech_to_text(recognizer)

            console.print(f"[bold blue]\[Transcribed]:[/bold blue] '{user_text}'")

            if not user_text:
                console.print("[dim]No speech detected. Going back to sleep.[/dim]")
                play_status_sound("sleep")
                continue

            gemma_reply = generate_response(user_text)

            console.print("[bold magenta]\[Speaking...][/bold magenta]")
            text_to_speech(pipeline, gemma_reply, target_voice)
        except sr.WaitTimeoutError:
            console.print("[dim]Timed out waiting for a command. Going back to sleep.[/dim]")
        except sr.UnknownValueError:
            console.print("[dim]Didn't catch that! Going back to sleep.[/dim]")
        except Exception as e:
            console.print(f"[bold red]\[Error in pipeline]:[/bold red] {e}")

        play_status_sound("sleep")
        console.print("\n[dim]\[Sleeping..] Say Jarvis to wake me up.[/dim]")


if __name__ == "__main__":
    main()

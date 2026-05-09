import logging
import select
import sys
import argparse

import openwakeword
import speech_recognition as sr
from kokoro import KPipeline
from openwakeword.model import Model
from rich.console import Console
from rich.logging import RichHandler

from config.settings import ASSISTANT_SETTINGS, SPEECH_SETTINGS, WAKE_WORD_SETTINGS
from core.llm import generate_response
from engine.stt import build_speech_config, speech_to_text
from engine.tts import text_to_speech
from engine.wake_word import build_wake_config, calibrate_microphone, wake_word_detection
from utils.audio import play_status_sound
from utils.health import run_startup_health_checks
from utils.history import last_heard, record_command

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")
console = Console()


def set_state(state: str, detail: str | None = None) -> None:
    message = f"[bold cyan]State:[/bold cyan] {state}"
    if detail:
        message += f" [dim]{detail}[/dim]"
    console.print(message)


def stdin_pressed() -> bool:
    if not sys.stdin.isatty():
        return False
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return False
    sys.stdin.readline()
    return True


def confirm_tool(tool_name: str, args: dict, permission: str) -> bool:
    if not ASSISTANT_SETTINGS.get("confirm_risky_tools", True):
        return True

    console.print(f"[bold yellow]Confirm {permission} tool:[/bold yellow] {tool_name} {args}")
    console.print("[dim]Type y and press Enter to allow, anything else to cancel.[/dim]")
    answer = input("> ").strip().lower()
    return answer in {"y", "yes"}


def capture_command(
    recognizer: sr.Recognizer,
    speech_config,
    *,
    follow_up: bool = False,
) -> str | None:
    attempts = max(1, speech_config.retry_attempts + 1)
    timeout = speech_config.follow_up_timeout_seconds if follow_up else speech_config.timeout_seconds

    for attempt in range(attempts):
        result = speech_to_text(
            recognizer,
            speech_config,
            timeout_seconds=timeout,
            status_label="Follow-up" if follow_up else "Listening",
        )
        console.print(
            f"[bold blue]\\[Transcribed]:[/bold blue] '{result.text}' "
            f"[dim](audio {result.audio_seconds:.1f}s, rms {result.rms:.3f})[/dim]"
        )

        if result.text:
            record_command(result.text)
            return result.text

        if attempt < attempts - 1:
            console.print("[yellow]I didn't catch that. Listening one more time...[/yellow]")
            play_status_sound("wake")

    return None


def handle_local_command(user_text: str, pipeline, target_voice: str) -> bool:
    normalized = user_text.strip().lower()

    if normalized in {"stop", "cancel", "never mind", "nevermind"}:
        console.print("[dim]Cancelled. Going back to sleep.[/dim]")
        return True

    if "what did you hear" in normalized or "what was the last command" in normalized:
        heard = last_heard()
        reply = f"The last thing I heard was: {heard}" if heard else "I do not have any command history yet."
        console.print(f"[bold cyan]\\[Jarvis]:[/bold cyan] {reply}")
        text_to_speech(pipeline, [reply], target_voice, interrupt_checker=stdin_pressed)
        return True

    return False


def print_health_checks() -> None:
    set_state("Health check")
    for check in run_startup_health_checks():
        style = "green" if check.ok else "yellow"
        label = "OK" if check.ok else "WARN"
        console.print(f"[{style}]{label}[/{style}] {check.name}: {check.detail}")


def main(mode: str = "voice"):
    logger.info("Initializing system...")
    
    if mode == "text":
        console.print("\n[bold green]===============================[/bold green]")
        console.print("[bold green]Text Mode Ready. Type your message below.[/bold green]")
        console.print("[dim]Type 'quit', 'exit', or 'stop' to end.[/dim]")
        console.print("[bold green]===============================[/bold green]")
        
        while True:
            try:
                user_text = input("\nYou: ").strip()
                if not user_text:
                    continue
                if user_text.lower() in {"quit", "exit", "stop"}:
                    console.print("[bold yellow]Goodbye.[/bold yellow]")
                    break
                    
                set_state("Thinking")
                record_command(user_text)
                reply_generator = generate_response(user_text, confirm_tool=confirm_tool, on_state=set_state)
                
                started_reply = False
                for chunk in reply_generator:
                    if not started_reply:
                        console.print("[bold cyan]Jarvis:[/bold cyan] ", end="")
                        started_reply = True
                    console.print(chunk, end=" ", style="cyan", highlight=False)
                if started_reply:
                    console.print()
                
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Goodbye.[/bold yellow]")
                break
            except EOFError:
                console.print("\n[bold yellow]Goodbye.[/bold yellow]")
                break
            except Exception as e:
                set_state("Error")
                console.print(f"[bold red]\\[Error in pipeline]:[/bold red] {e}")
        return

    logger.info("Initializing TTS and engines...")

    wake_config = build_wake_config(WAKE_WORD_SETTINGS)
    speech_config = build_speech_config(SPEECH_SETTINGS, wake_config.microphone_device_index)
    recognizer = sr.Recognizer()

    print_health_checks()

    set_state("Initializing TTS")
    pipeline = KPipeline(lang_code="a")
    target_voice = str(ASSISTANT_SETTINGS.get("tts_voice", "af_heart"))

    set_state("Preparing wake word model")
    openwakeword.utils.download_models()
    oww_model = Model(wakeword_models=list(wake_config.models), inference_framework="onnx")

    set_state("Calibrating microphone")
    try:
        ambient_rms, ambient_dbfs, recommended_threshold = calibrate_microphone(wake_config)
        console.print(
            "[dim]Mic ambient level "
            f"{ambient_dbfs:.0f} dBFS (rms {ambient_rms:.0f}). "
            f"Current wake threshold {wake_config.threshold:.2f}; recommended {recommended_threshold:.2f}.[/dim]"
        )
    except Exception as exc:
        console.print(f"[yellow]Microphone calibration skipped: {exc}[/yellow]")

    console.print("\n[bold green]===============================[/bold green]")
    console.print(
        "[bold green]Pipeline Ready. Say 'Jarvis' or press Enter to talk.[/bold green]"
    )
    console.print("[bold green]===============================[/bold green]")

    follow_up_mode = bool(ASSISTANT_SETTINGS.get("follow_up_mode", True))
    awaiting_follow_up = False

    while True:
        try:
            if awaiting_follow_up:
                set_state("Listening", "follow-up window")
            else:
                set_state("Sleeping", "say Jarvis or press Enter")
                diagnostics = wake_word_detection(oww_model, wake_config)
                play_status_sound("wake")
                set_state(
                    "Heard wake word",
                    f"trigger={diagnostics.trigger}, score={max(list(diagnostics.smoothed_scores.values()) or [0.0]):.2f}",
                )

            user_text = capture_command(recognizer, speech_config, follow_up=awaiting_follow_up)

            if not user_text:
                console.print("[dim]No speech detected. Going back to sleep.[/dim]")
                play_status_sound("sleep")
                awaiting_follow_up = False
                continue

            awaiting_follow_up = False
            if handle_local_command(user_text, pipeline, target_voice):
                play_status_sound("sleep")
                continue

            console.print("[bold magenta]Got it.[/bold magenta]")
            set_state("Thinking")

            reply_generator = generate_response(user_text, confirm_tool=confirm_tool, on_state=set_state)

            set_state("Speaking", "press Enter between chunks to interrupt")
            full_reply = ""

            def intercept_generator(gen):
                nonlocal full_reply
                for chunk in gen:
                    full_reply += chunk + " "
                    yield chunk

            was_interrupted = text_to_speech(
                pipeline,
                intercept_generator(reply_generator),
                target_voice,
                interrupt_checker=stdin_pressed,
            )

            if was_interrupted:
                console.print("[yellow]Speech interrupted.[/yellow]")

            awaiting_follow_up = follow_up_mode and not was_interrupted
            if awaiting_follow_up:
                console.print(
                    f"[dim]Follow-up mode active for {speech_config.follow_up_timeout_seconds:.0f}s.[/dim]"
                )
            else:
                play_status_sound("sleep")
                console.print("\n[dim]\\[Sleeping..] Say Jarvis to wake me up.[/dim]")

        except sr.WaitTimeoutError:
            console.print("[dim]Timed out waiting for a command. Going back to sleep.[/dim]")
            awaiting_follow_up = False
            play_status_sound("sleep")
        except sr.UnknownValueError:
            console.print("[dim]Didn't catch that. Going back to sleep.[/dim]")
            awaiting_follow_up = False
            play_status_sound("sleep")
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Goodbye.[/bold yellow]")
            break
        except Exception as e:
            set_state("Error")
            console.print(f"[bold red]\\[Error in pipeline]:[/bold red] {e}")
            awaiting_follow_up = False
            play_status_sound("sleep")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis AI Assistant")
    parser.add_argument("--mode", type=str, choices=["voice", "text"], default="voice", help="Interaction mode (voice or text)")
    args = parser.parse_args()
    
    main(mode=args.mode)

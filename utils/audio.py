import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def play_status_sound(state: str):
    """
    Play a sound to indicate wake or sleep using native macOS afplay.
    """
    sound_file = ""
    if state == "wake":
        sound_file = "/System/Library/Sounds/Ping.aiff"
    elif state == "sleep":
        sound_file = "/System/Library/Sounds/Pop.aiff"
    else:
        return

    if os.path.exists(sound_file):
        try:
            subprocess.Popen(["afplay", sound_file])
        except Exception as e:
            logger.error(f"Failed to play sound {sound_file}: {e}")
    else:
        logger.warning(f"Sound file not found: {sound_file}")

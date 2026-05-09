import subprocess
from datetime import datetime

def open_app(app_name: str) -> str:
    """Opens a macOS application by name."""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened application: {app_name}"
    except Exception as e:
        return f"Failed to open application {app_name}: {e}"

def get_time() -> str:
    """Returns the current system time."""
    return f"The current time is {datetime.now().strftime('%I:%M %p')}"

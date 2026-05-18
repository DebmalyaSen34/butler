import shutil
import sys
import time


FRAME_DELAY = 0.35
FINAL_HOLD = 0.35
MIN_WIDTH_FOR_ANIMATION = 46

CYAN = "\033[96m"
YELLOW = "\033[93m"
WHITE = "\033[97m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\033[2K"
CURSOR_UP = "\033[1A"


def _visible_len(text: str) -> int:
    length = 0
    in_escape = False
    for char in text:
        if char == "\033":
            in_escape = True
            continue
        if in_escape:
            if char == "m":
                in_escape = False
            continue
        length += 1
    return length


def _center(text: str, width: int) -> str:
    padding = max(0, (width - _visible_len(text)) // 2)
    return f"{' ' * padding}{text}"


def _write_frame(lines: list[str], width: int, *, previous_height: int) -> None:
    if previous_height:
        sys.stdout.write(CURSOR_UP * previous_height)

    rendered = [_center(line, width) for line in lines]
    for line in rendered:
        sys.stdout.write(f"{CLEAR_LINE}{line}\n")
    sys.stdout.flush()


def _compact_intro() -> list[list[str]]:
    nucleus = f"{YELLOW}o{RESET}"
    burst = f"{YELLOW}*{RESET}"
    helium = f"{CYAN}@{RESET}"

    return [
        [f"{DIM}fusion sequence{RESET}", f"{nucleus}                         {nucleus}"],
        [f"{DIM}fusion sequence{RESET}", f"     {nucleus}               {nucleus}"],
        [f"{DIM}binding energy rising{RESET}", f"          {nucleus}     {nucleus}"],
        [f"{WHITE}\\  |  /{RESET}", f"   {nucleus} {nucleus}   ", f"{WHITE}/  |  \\{RESET}"],
        [f"{YELLOW}-- * BOOM * --{RESET}", f" {burst} {burst} {burst} {burst} {burst} "],
        [f"{CYAN}    .-@-.{RESET}", f"{CYAN}  .'  He '.{RESET}", f"{CYAN}  '.___.'{RESET}"],
        [
            f"{CYAN}    .-@-.{RESET}",
            f"{CYAN}  .'  He '.{RESET}",
            f"{CYAN}  '.___.'{RESET}",
            f"{BOLD}{CYAN}HELIUM AGENT{RESET}",
            f"{DIM}{helium} local-first assistant online{RESET}",
        ],
    ]


def render_startup_intro(*, animated: bool = True) -> None:
    width = shutil.get_terminal_size((80, 24)).columns

    if not sys.stdout.isatty() or not animated or width < MIN_WIDTH_FOR_ANIMATION:
        sys.stdout.write(f"{CYAN}{BOLD}HELIUM AGENT{RESET}\n")
        sys.stdout.flush()
        return

    frames = _compact_intro()
    previous_height = 0
    sys.stdout.write(HIDE_CURSOR)

    try:
        for frame in frames:
            _write_frame(frame, width, previous_height=previous_height)
            previous_height = len(frame)
            time.sleep(FRAME_DELAY)
        time.sleep(FINAL_HOLD)
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


def main() -> None:
    render_startup_intro()
    sys.stdout.write(f"{CYAN}helium>{RESET} ")
    sys.stdout.flush()


if __name__ == "__main__":
    main()

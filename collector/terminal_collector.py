"""
Terminal command collector.
Polls the shell history file and logs new commands as events.
"""

import os
import time
import threading
from pathlib import Path

from config.config_loader import CONFIG
from processor.event_processor import process_event

_stop_event = threading.Event()


def _get_history_path() -> Path:
    """Return resolved history path from config, with OS-aware fallback."""
    configured = CONFIG["terminal"].get("history_path", "")
    if configured:
        return Path(os.path.expandvars(os.path.expanduser(configured)))

    # Auto-detect
    shell = CONFIG["terminal"].get("shell", "bash").lower()
    if shell == "powershell":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt"
    elif shell == "zsh":
        return Path.home() / ".zsh_history"
    else:
        return Path.home() / ".bash_history"


def _parse_commands(lines: list[str], shell: str) -> list[str]:
    """Return clean command strings, stripping zsh timestamps or PS metadata."""
    commands = []
    shell = shell.lower()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if shell == "zsh" and line.startswith(": ") and ";" in line:
            # zsh extended_history format: ": <timestamp>:<elapsed>;<command>"
            try:
                line = line.split(";", 1)[1]
            except IndexError:
                pass
        commands.append(line)
    return commands


def watch_terminal(stop_event: threading.Event = None) -> None:
    """
    Infinite loop that polls the shell history file for new commands
    and persists them as 'terminal' events.
    """
    if stop_event is None:
        stop_event = _stop_event

    history_path = _get_history_path()
    shell = CONFIG["terminal"].get("shell", "bash")
    poll_interval = CONFIG["terminal"].get("poll_interval", 5)
    source = shell.lower()

    last_size = 0

    while not stop_event.is_set():
        try:
            if not history_path.exists():
                time.sleep(poll_interval)
                continue

            current_size = history_path.stat().st_size

            if current_size < last_size:
                # File was truncated / rotated — reset
                last_size = 0

            if current_size > last_size:
                with open(history_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_size)
                    new_content = f.read()
                    last_size = f.tell()

                new_lines = new_content.splitlines()
                commands = _parse_commands(new_lines, shell)

                for cmd in commands:
                    process_event(
                        "terminal",
                        source,
                        {"command": cmd, "shell": shell},
                    )

        except (OSError, IOError):
            pass  # History file temporarily unavailable

        time.sleep(poll_interval)

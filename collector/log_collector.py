"""
Log file collector — tails application log files and persists error events.
"""

import os
import re
import time
import threading
from pathlib import Path
from typing import Optional

from config.config_loader import CONFIG
from processor.event_processor import process_event

_stop_event = threading.Event()


def _build_pattern() -> re.Pattern:
    patterns = CONFIG["log_collector"].get(
        "error_patterns", ["ERROR", "Exception", "Traceback", "FATAL", "CRITICAL"]
    )
    combined = "|".join(f"({p})" for p in patterns)
    return re.compile(combined)


def parse_log(file_path: str) -> None:
    """
    One-shot scan of a log file — logs all matching error lines.
    Useful for scanning existing log files on demand.
    """
    pattern = _build_pattern()
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                level = match.group(0)
                process_event(
                    "error",
                    "log",
                    {"file": file_path, "line": line.strip(), "level": level},
                )


def watch_log(file_path: str, stop_event: threading.Event = None) -> None:
    """
    Tail a log file indefinitely, logging new error lines as events.
    Handles log rotation (file shrinks or disappears).
    """
    if stop_event is None:
        stop_event = _stop_event

    pattern = _build_pattern()
    poll_interval = CONFIG["log_collector"].get("poll_interval", 5)
    path = Path(file_path)

    last_inode: Optional[int] = None
    last_pos: int = 0

    while not stop_event.is_set():
        try:
            if not path.exists():
                last_inode = None
                last_pos = 0
                time.sleep(poll_interval)
                continue

            current_inode = path.stat().st_ino
            current_size = path.stat().st_size

            # Detect log rotation
            if last_inode is not None and current_inode != last_inode:
                last_pos = 0

            last_inode = current_inode

            # Detect truncation
            if current_size < last_pos:
                last_pos = 0

            if current_size > last_pos:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_pos)
                    for line in f:
                        match = pattern.search(line)
                        if match:
                            level = match.group(0)
                            process_event(
                                "error",
                                "log",
                                {
                                    "file": str(file_path),
                                    "line": line.strip(),
                                    "level": level,
                                },
                            )
                    last_pos = f.tell()

        except (OSError, IOError):
            pass

        time.sleep(poll_interval)

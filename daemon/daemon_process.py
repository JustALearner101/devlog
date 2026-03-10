"""
Foreground runner for the devlog daemon.
This module is invoked as a subprocess by `devlog daemon`.
It runs all collectors and blocks indefinitely until killed.

Usage (internal — do not call directly):
    python -m daemon.daemon_process
"""

import signal
import sys
import os
import threading
import time


# Ensure project root is on path when invoked as subprocess
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config.config_loader import CONFIG
from collector.terminal_collector import watch_terminal
from collector.log_collector import watch_log
from db.database import init_db

_stop_event = threading.Event()
_threads: list[threading.Thread] = []

PID_FILE = os.path.join(_project_root, "devlog_daemon.pid")


def _write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def _remove_pid():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def _handle_signal(signum, frame):
    _stop_event.set()


def run():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        signal.signal(signal.SIGINT, _handle_signal)
    except (OSError, ValueError):
        pass

    _write_pid()

    try:
        init_db()

        # Terminal collector thread
        t_terminal = threading.Thread(
            target=watch_terminal,
            args=(_stop_event,),
            name="terminal-collector",
            daemon=True,
        )
        _threads.append(t_terminal)
        t_terminal.start()

        # One thread per log file configured
        watch_paths = CONFIG["log_collector"].get("watch_paths", [])
        for log_path in watch_paths:
            t_log = threading.Thread(
                target=watch_log,
                args=(log_path, _stop_event),
                name=f"log-collector-{log_path}",
                daemon=True,
            )
            _threads.append(t_log)
            t_log.start()

        # Keep main thread alive, checking stop_event
        while not _stop_event.is_set():
            time.sleep(1)

        # Wait for threads to finish
        for t in _threads:
            t.join(timeout=10)

    finally:
        _remove_pid()


if __name__ == "__main__":
    run()


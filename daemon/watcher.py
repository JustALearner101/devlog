"""
Daemon launcher — spawns the devlog daemon as a detached background process.
"""

import os
import sys
import subprocess
import signal
from pathlib import Path

_project_root = Path(__file__).parent.parent
PID_FILE = _project_root / "devlog_daemon.pid"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _pid_running(pid: int) -> bool:
    """Return True if a process with this PID is currently running."""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def launch_background() -> int:
    """
    Spawn the daemon as a detached background process.
    Returns the PID of the new process.
    Raises RuntimeError if a daemon is already running.
    """
    existing_pid = _read_pid()
    if existing_pid and _pid_running(existing_pid):
        raise RuntimeError(f"Daemon is already running (PID {existing_pid})")

    # Remove stale PID file
    PID_FILE.unlink(missing_ok=True)

    python = sys.executable
    script = str(_project_root / "daemon" / "daemon_process.py")

    if sys.platform == "win32":
        # Windows: use DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP so the
        # child survives after the parent terminal closes
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(
            [python, script],
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(_project_root),
        )
    else:
        # Unix: double-fork via nohup equivalent
        proc = subprocess.Popen(
            [python, script],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            cwd=str(_project_root),
        )

    return proc.pid


def stop_daemon() -> int | None:
    """
    Send SIGTERM (Windows: taskkill) to the running daemon.
    Returns the PID that was stopped, or None if no daemon was running.
    """
    pid = _read_pid()
    if pid is None or not _pid_running(pid):
        PID_FILE.unlink(missing_ok=True)
        return None

    if sys.platform == "win32":
        subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(pid, signal.SIGTERM)

    PID_FILE.unlink(missing_ok=True)
    return pid


def status() -> dict:
    """
    Return a dict describing the daemon's current state.
    Keys: running (bool), pid (int | None)
    """
    pid = _read_pid()
    running = bool(pid and _pid_running(pid))
    return {"running": running, "pid": pid if running else None}


# ---------------------------------------------------------------------------
# Legacy foreground helpers (kept for tests / direct use)
# ---------------------------------------------------------------------------

def start() -> None:
    """Foreground start — blocks until Ctrl+C. Used internally by daemon_process."""
    import threading
    import time
    from config.config_loader import CONFIG
    from collector.terminal_collector import watch_terminal
    from collector.log_collector import watch_log

    stop_event = threading.Event()
    threads: list[threading.Thread] = []

    t = threading.Thread(target=watch_terminal, args=(stop_event,), daemon=True)
    threads.append(t)
    t.start()

    for log_path in CONFIG["log_collector"].get("watch_paths", []):
        tl = threading.Thread(target=watch_log, args=(log_path, stop_event), daemon=True)
        threads.append(tl)
        tl.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        for th in threads:
            th.join(timeout=10)


def stop() -> None:
    stop_daemon()

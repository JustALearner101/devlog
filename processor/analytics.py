"""
Analytics engine — queries the events DB and returns structured insight dicts.
"""

import json
from collections import Counter
from datetime import datetime, date, timedelta

from sqlalchemy import func

from db.database import get_session
from db.models import Event
from config.config_loader import CONFIG

_TOP_N = CONFIG["report"].get("top_n", 5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _day_range(for_date: date) -> tuple[datetime, datetime]:
    """Return (start_dt, end_dt) covering the full day for SQLAlchemy queries."""
    start = datetime(for_date.year, for_date.month, for_date.day, 0, 0, 0)
    end = datetime(for_date.year, for_date.month, for_date.day, 23, 59, 59)
    return start, end


def _week_range(for_date: date) -> tuple[datetime, datetime]:
    """Return (start_dt, end_dt) for the ISO week containing for_date."""
    start_of_week = for_date - timedelta(days=for_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start = datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0)
    end = datetime(end_of_week.year, end_of_week.month, end_of_week.day, 23, 59, 59)
    return start, end


# ---------------------------------------------------------------------------
# Daily analytics
# ---------------------------------------------------------------------------

def commits_today(for_date: date = None) -> int:
    """Count commit events for a given day (defaults to today)."""
    d = for_date or date.today()
    start, end = _day_range(d)
    with get_session() as session:
        return (
            session.query(func.count(Event.id))
            .filter(Event.type == "commit", Event.timestamp >= start, Event.timestamp <= end)
            .scalar()
        )


def commands_today(for_date: date = None) -> int:
    """Count terminal events for a given day."""
    d = for_date or date.today()
    start, end = _day_range(d)
    with get_session() as session:
        return (
            session.query(func.count(Event.id))
            .filter(Event.type == "terminal", Event.timestamp >= start, Event.timestamp <= end)
            .scalar()
        )


def errors_today(for_date: date = None) -> int:
    """Count error events for a given day."""
    d = for_date or date.today()
    start, end = _day_range(d)
    with get_session() as session:
        return (
            session.query(func.count(Event.id))
            .filter(Event.type == "error", Event.timestamp >= start, Event.timestamp <= end)
            .scalar()
        )


def top_files_today(for_date: date = None, n: int = None) -> list[tuple[str, int]]:
    """
    Return the top N most-modified files for a given day.
    Extracted from commit metadata['files_changed'] lists.
    """
    n = n or _TOP_N
    d = for_date or date.today()
    start, end = _day_range(d)

    counter: Counter = Counter()
    with get_session() as session:
        events = (
            session.query(Event.meta)
            .filter(Event.type == "commit", Event.timestamp >= start, Event.timestamp <= end)
            .all()
        )

    for (raw,) in events:
        try:
            meta = json.loads(raw or "{}")
            for f in meta.get("files_changed", []):
                counter[f] += 1
        except (json.JSONDecodeError, TypeError):
            pass

    return counter.most_common(n)


def common_errors_today(for_date: date = None, n: int = None) -> list[tuple[str, int]]:
    """Return the top N most common error snippets for a given day."""
    n = n or _TOP_N
    d = for_date or date.today()
    start, end = _day_range(d)

    counter: Counter = Counter()
    with get_session() as session:
        events = (
            session.query(Event.meta)
            .filter(Event.type == "error", Event.timestamp >= start, Event.timestamp <= end)
            .all()
        )

    for (raw,) in events:
        try:
            meta = json.loads(raw or "{}")
            line = meta.get("line", raw or "")
            # Use first 80 chars as the error key to keep output readable
            counter[line[:80]] += 1
        except (json.JSONDecodeError, TypeError):
            counter[str(raw)[:80]] += 1

    return counter.most_common(n)


def get_daily_summary(for_date: date = None) -> dict:
    """Return a dict with all metrics for the daily report."""
    d = for_date or date.today()
    return {
        "date": d.isoformat(),
        "commits": commits_today(d),
        "commands": commands_today(d),
        "errors": errors_today(d),
        "top_files": top_files_today(d),
        "common_errors": common_errors_today(d),
    }


# ---------------------------------------------------------------------------
# Weekly analytics
# ---------------------------------------------------------------------------

def get_weekly_summary(for_date: date = None) -> dict:
    """Return a dict with all metrics for the weekly report."""
    d = for_date or date.today()
    start, end = _week_range(d)

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_commit_counts: Counter = Counter()
    module_counter: Counter = Counter()
    total_commits = 0
    total_commands = 0
    total_errors = 0

    with get_session() as session:
        # Commits
        commit_events = (
            session.query(Event.timestamp, Event.meta)
            .filter(Event.type == "commit", Event.timestamp >= start, Event.timestamp <= end)
            .all()
        )
        for ts, raw in commit_events:
            total_commits += 1
            day_commit_counts[ts.weekday()] += 1
            try:
                meta = json.loads(raw or "{}")
                for f in meta.get("files_changed", []):
                    # Use top-level directory as the "module"
                    parts = f.replace("\\", "/").split("/")
                    module = parts[0] if len(parts) > 1 else f
                    module_counter[module] += 1
            except (json.JSONDecodeError, TypeError):
                pass

        # Terminal commands
        total_commands = (
            session.query(func.count(Event.id))
            .filter(Event.type == "terminal", Event.timestamp >= start, Event.timestamp <= end)
            .scalar()
        )

        # Errors
        total_errors = (
            session.query(func.count(Event.id))
            .filter(Event.type == "error", Event.timestamp >= start, Event.timestamp <= end)
            .scalar()
        )

    most_active_day = (
        day_names[day_commit_counts.most_common(1)[0][0]]
        if day_commit_counts
        else "N/A"
    )
    most_worked_module = (
        module_counter.most_common(1)[0][0] if module_counter else "N/A"
    )

    # Estimate coding sessions: each day with at least one event = 1 session
    active_days = len(day_commit_counts)

    return {
        "week_start": start.date().isoformat(),
        "week_end": end.date().isoformat(),
        "total_commits": total_commits,
        "total_commands": total_commands,
        "total_errors": total_errors,
        "total_coding_sessions": active_days,
        "most_active_day": most_active_day,
        "most_worked_module": most_worked_module,
    }


# ---------------------------------------------------------------------------
# Command analytics
# ---------------------------------------------------------------------------

def top_commands(for_date: date = None, n: int = None) -> list[tuple[str, int]]:
    """Return the top N most-used terminal commands for a given day."""
    n = n or _TOP_N
    d = for_date or date.today()
    start, end = _day_range(d)

    counter: Counter = Counter()
    with get_session() as session:
        events = (
            session.query(Event.meta)
            .filter(Event.type == "terminal", Event.timestamp >= start, Event.timestamp <= end)
            .all()
        )

    for (raw,) in events:
        try:
            meta = json.loads(raw or "{}")
            cmd = meta.get("command", "").strip().split()[0]  # first token = program name
            if cmd:
                counter[cmd] += 1
        except (json.JSONDecodeError, TypeError, IndexError):
            pass

    return counter.most_common(n)

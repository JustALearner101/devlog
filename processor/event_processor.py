"""
Central write path for all events.
All collectors call process_event() instead of writing directly to the DB.
"""

import json
from datetime import datetime, timezone
from db.database import get_session
from db.models import Event


def process_event(event_type: str, source: str, metadata: dict, timestamp: datetime = None) -> Event:
    """
    Validate, normalise, and persist a single event.

    :param event_type: 'commit' | 'terminal' | 'error'
    :param source:     e.g. 'git', 'bash', 'powershell', 'log'
    :param metadata:   dict of event-specific data
    :param timestamp:  optional UTC datetime; defaults to utcnow
    :return:           the persisted Event instance
    """
    if not event_type:
        raise ValueError("event_type is required")
    if not source:
        raise ValueError("source is required")

    ts = timestamp or datetime.now(timezone.utc).replace(tzinfo=None)
    metadata_json = json.dumps(metadata or {})

    event = Event(
        type=event_type,
        source=source,
        timestamp=ts,
        meta=metadata_json,
    )

    with get_session() as session:
        session.add(event)

    return event


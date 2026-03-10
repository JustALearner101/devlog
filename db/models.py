from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    meta = Column("metadata", Text)  # JSON string — stored as 'metadata' in DB

    __table_args__ = (
        Index("ix_events_type_timestamp", "type", "timestamp"),
    )

    def get_metadata(self) -> dict:
        """Parse and return meta as a dict."""
        if self.meta:
            try:
                return json.loads(self.meta)
            except (json.JSONDecodeError, TypeError):
                return {"raw": self.meta}
        return {}

    def __repr__(self):
        return f"<Event id={self.id} type={self.type} source={self.source} ts={self.timestamp}>"

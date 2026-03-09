from .. import db
from ..models import EventType


DEFAULT_EVENT_TYPES = [
    "Commander Party",
    "Modern RCQ",
    "Standard RCQ",
    "Sealed RCQ",
    "$1k",
    "Store Championship",
    "Prerelease",
    "Release",
    "Skirmish",
]


def seed_default_event_types():
    """Ensure default event types exist (add any missing)."""
    for name in DEFAULT_EVENT_TYPES:
        if EventType.query.filter_by(name=name).first() is None:
            db.session.add(EventType(name=name))
    db.session.commit()

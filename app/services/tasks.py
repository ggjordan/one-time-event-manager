from __future__ import annotations

from datetime import datetime, timedelta

from .. import db
from ..models import Event, EventTask, TaskTemplate


DEFAULT_TEMPLATES = [
    # Online setup – all should be due before the 1‑month social posts
    {
        "name": "Online: Event page on site",
        "group": "online_setup",
        "lead_days_before_event": 35,
        "order_index": 10,
    },
    {
        "name": "Online: Ticket / registration setup",
        "group": "online_setup",
        "lead_days_before_event": 34,
        "order_index": 20,
    },
    {
        "name": "Online: Front page banner",
        "group": "online_setup",
        "lead_days_before_event": 33,
        "order_index": 30,
    },
    # Social – 1 month out
    {
        "name": "Social: 1 month out – Discord post",
        "group": "social_1_month",
        "lead_days_before_event": 30,
        "order_index": 40,
    },
    {
        "name": "Social: 1 month out – Facebook post",
        "group": "social_1_month",
        "lead_days_before_event": 30,
        "order_index": 50,
    },
    {
        "name": "Assets: 1 month social graphics",
        "group": "assets",
        "lead_days_before_event": 32,
        "order_index": 60,
    },
    # Social – 2 weeks out
    {
        "name": "Social: 2 weeks out – Discord post",
        "group": "social_2_weeks",
        "lead_days_before_event": 14,
        "order_index": 70,
    },
    {
        "name": "Social: 2 weeks out – Facebook post",
        "group": "social_2_weeks",
        "lead_days_before_event": 14,
        "order_index": 80,
    },
    {
        "name": "Assets: 2 weeks social graphics",
        "group": "assets",
        "lead_days_before_event": 16,
        "order_index": 90,
    },
    # Social – 1 week out
    {
        "name": "Social: 1 week out – Discord post",
        "group": "social_1_week",
        "lead_days_before_event": 7,
        "order_index": 100,
    },
    {
        "name": "Social: 1 week out – Facebook post",
        "group": "social_1_week",
        "lead_days_before_event": 7,
        "order_index": 110,
    },
    {
        "name": "Assets: 1 week social graphics",
        "group": "assets",
        "lead_days_before_event": 9,
        "order_index": 120,
    },
    # Social – night before
    {
        "name": "Social: Night before – Discord post",
        "group": "social_night_before",
        "lead_days_before_event": 1,
        "order_index": 130,
    },
    {
        "name": "Social: Night before – Facebook post",
        "group": "social_night_before",
        "lead_days_before_event": 1,
        "order_index": 140,
    },
    # Event prep / running / post-event
    {
        "name": "Event prep: Set aside space",
        "group": "event_prep",
        "lead_days_before_event": 0,
        "order_index": 150,
    },
    {
        "name": "Run event",
        "group": "event_run",
        "lead_days_before_event": 0,
        "order_index": 160,
    },
    {
        "name": "Post-event: Get pictures",
        "group": "post_event",
        "lead_days_before_event": -1,
        "order_index": 170,
    },
    {
        "name": "Post-event: Record attendance",
        "group": "post_event",
        "lead_days_before_event": -1,
        "order_index": 180,
    },
    {
        "name": "Post-event: Archive event listing",
        "group": "post_event",
        "lead_days_before_event": -2,
        "order_index": 190,
    },
]


def seed_default_task_templates() -> None:
    """Create default task templates if none exist yet."""

    if TaskTemplate.query.count() > 0:
        return

    for data in DEFAULT_TEMPLATES:
        tmpl = TaskTemplate(
            name=data["name"],
            group=data["group"],
            lead_days_before_event=data["lead_days_before_event"],
            order_index=data["order_index"],
        )
        db.session.add(tmpl)

    db.session.commit()


def generate_tasks_for_event(event: Event) -> None:
    """Generate EventTask rows for an event from active templates."""

    now = datetime.utcnow()
    event_dt = event.event_datetime

    templates = (
        TaskTemplate.query.filter_by(is_active=True)
        .order_by(TaskTemplate.order_index.asc())
        .all()
    )

    for tmpl in templates:
        # Ideal due date is event date/time minus lead_days_before_event
        ideal_due = event_dt - timedelta(days=tmpl.lead_days_before_event)

        # If ideal due is already in the past, shift to "now" to allow on-time
        # completion for late-created events.
        actual_due = ideal_due if ideal_due >= now else now

        task = EventTask(
            event=event,
            template=tmpl,
            name=tmpl.name,
            group=tmpl.group,
            assignee=event.owner,
            ideal_due_at=ideal_due,
            actual_due_at=actual_due,
        )
        db.session.add(task)


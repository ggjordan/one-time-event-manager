from datetime import datetime

from flask import Blueprint, render_template, request
from sqlalchemy.orm import joinedload

from .. import db
from ..models import Event, EventTask, User

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _is_task_on_time(task):
    if task.status != "complete" or not task.completed_at or not task.actual_due_at:
        return False
    return task.completed_at <= task.actual_due_at


def _event_fully_prepared(event):
    """True if every task due before the event was completed on time."""
    event_dt = event.event_datetime
    # Event.tasks is lazy='dynamic' so use .all() to get a list
    for task in event.tasks.all():
        if task.actual_due_at and task.actual_due_at < event_dt:
            if task.status != "complete":
                return False
            if not _is_task_on_time(task):
                return False
    return True


@reports_bp.route("/")
def index():
    return render_template("reports/index.html")


@reports_bp.route("/by-user")
def by_user():
    now = datetime.utcnow()
    users = User.query.order_by(User.name.asc()).all()
    rows = []
    for user in users:
        tasks = EventTask.query.filter_by(assignee_id=user.id).all()
        completed = [t for t in tasks if t.status == "complete"]
        on_time = [t for t in completed if _is_task_on_time(t)]
        overdue_undone = [t for t in tasks if t.status != "complete" and t.actual_due_at and t.actual_due_at < now]
        total = len(tasks)
        completed_count = len(completed)
        on_time_count = len(on_time)
        overdue_undone_count = len(overdue_undone)
        pct_on_time = round(100 * on_time_count / completed_count, 1) if completed_count else None
        pct_overdue_undone = round(100 * overdue_undone_count / total, 1) if total else None
        rows.append({
            "user": user,
            "total_tasks": total,
            "completed": completed_count,
            "on_time": on_time_count,
            "pct_on_time": pct_on_time,
            "overdue_undone": overdue_undone_count,
            "pct_overdue_undone": pct_overdue_undone,
        })
    return render_template("reports/by_user.html", rows=rows)


@reports_bp.route("/events-prepared")
def events_prepared():
    # Don't use joinedload(Event.tasks) - Event.tasks is lazy='dynamic'
    events = (
        Event.query.options(joinedload(Event.game), joinedload(Event.owner))
        .order_by(Event.event_datetime.desc())
        .all()
    )
    rows = []
    for event in events:
        prepared = _event_fully_prepared(event)
        rows.append({
            "event": event,
            "fully_prepared": prepared,
        })
    return render_template("reports/events_prepared.html", rows=rows)


@reports_bp.route("/attendance")
def attendance():
    """Correlation: events with attendees, compare avg when fully prepared vs not."""
    # Don't use joinedload(Event.tasks) - Event.tasks is lazy='dynamic'
    events = (
        Event.query.options(joinedload(Event.game))
        .filter(Event.attendees.isnot(None))
        .order_by(Event.event_datetime.desc())
        .all()
    )
    prepared_attendees = [e.attendees for e in events if _event_fully_prepared(e) and e.attendees is not None]
    not_prepared_attendees = [e.attendees for e in events if not _event_fully_prepared(e) and e.attendees is not None]

    avg_prepared = round(sum(prepared_attendees) / len(prepared_attendees), 1) if prepared_attendees else None
    avg_not_prepared = round(sum(not_prepared_attendees) / len(not_prepared_attendees), 1) if not_prepared_attendees else None

    event_rows = [
        {"event": e, "fully_prepared": _event_fully_prepared(e), "attendees": e.attendees}
        for e in events
    ]

    return render_template(
        "reports/attendance.html",
        events=event_rows,
        count_prepared=len(prepared_attendees),
        count_not_prepared=len(not_prepared_attendees),
        avg_prepared=avg_prepared,
        avg_not_prepared=avg_not_prepared,
    )

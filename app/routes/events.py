from datetime import datetime, timedelta, time as time_cls
import os
import uuid

from flask import Blueprint, current_app, redirect, render_template, request, url_for, flash
from sqlalchemy import or_

from .. import db
from ..models import Event, EventType, Game, User, EventTask
from ..services.tasks import generate_tasks_for_event
from ..services.task_types import (
    TASK_TYPE_OPTIONS,
    TASK_TYPE_TO_GROUP,
    get_task_type,
    get_task_type_label,
    GROUP_TO_TYPE,
)
from ..utils.url_validation import is_allowed_drive_link

events_bp = Blueprint("events", __name__, url_prefix="/events")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_TASK_STATUSES = {"complete", "not_applicable", "missed_deadline"}


def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def _task_timing_class(task):
    """Return 'on_time', 'late_2', 'late_3', or None for row styling."""
    if task.status != "complete" or not task.completed_at or not task.actual_due_at:
        return None
    delta = task.completed_at - task.actual_due_at
    days_late = delta.total_seconds() / 86400
    if days_late <= 0:
        return "on_time"
    if days_late <= 2:
        return "late_2"
    return "late_3"


def _is_attendance_task(task):
    """True if completing this task should capture event attendees."""
    return task and "record attendance" in (task.name or "").lower()


def _event_task_sort_key(task, sort_by):
    """Sort key for a single event's tasks (no event/game variety)."""
    if sort_by == "due_date":
        return (task.actual_due_at is None, task.actual_due_at or "")
    if sort_by == "days_until_due":
        if not task.actual_due_at:
            return (1, None)
        now = datetime.utcnow()
        due = task.actual_due_at.replace(tzinfo=None) if task.actual_due_at.tzinfo else task.actual_due_at
        delta = (due - now).total_seconds() / 86400
        return (0, delta)
    if sort_by in ("task", "name"):
        return (task.name or "")
    if sort_by == "status":
        return (task.status == "complete", task.completed_at or "")
    if sort_by == "assignee":
        return (task.assignee.name if task.assignee else "")
    return (task.actual_due_at is None, task.actual_due_at or "")


EVENT_STATUS_OPTIONS = [
    ("all", "All"),
    ("undone", "Incomplete (to-do)"),
    ("done", "Complete only"),
    ("not_applicable", "Not applicable"),
    ("missed_deadline", "Missed deadline"),
]
EVENT_SORT_OPTIONS = [
    ("due_date", "Due date"),
    ("task", "Task name"),
    ("status", "Status"),
    ("assignee", "Assignee"),
]


@events_bp.route("/")
def list_events():
    search = request.args.get("search", "").strip()
    date_from_s = request.args.get("date_from", "").strip()
    date_to_s = request.args.get("date_to", "").strip()
    q = Event.query
    if search:
        term = f"%{search}%"
        q = (
            q.join(User, Event.owner_id == User.id)
            .join(Game, Event.game_id == Game.id)
        )
        q = q.filter(
            or_(
                Event.title.ilike(term),
                User.name.ilike(term),
                User.email.ilike(term),
                Game.name.ilike(term),
                Event.event_type.ilike(term),
            )
        )
    if date_from_s:
        try:
            df = datetime.strptime(date_from_s, "%Y-%m-%d")
            q = q.filter(Event.event_datetime >= df)
        except ValueError:
            pass
    if date_to_s:
        try:
            dt = datetime.strptime(date_to_s, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            q = q.filter(Event.event_datetime <= dt)
        except ValueError:
            pass
    events = q.order_by(Event.event_datetime.asc()).all()
    return render_template(
        "events/list.html",
        events=events,
        search=search,
        date_from=date_from_s,
        date_to=date_to_s,
    )


@events_bp.route("/<int:event_id>")
def event_detail(event_id: int):
    event = Event.query.get_or_404(event_id)
    tasks = (
        EventTask.query.filter_by(event_id=event.id)
        .options(
            db.joinedload(EventTask.assignee),
            db.joinedload(EventTask.template),
        )
        .all()
    )

    search = request.args.get("search", "").strip()
    assignee_id = request.args.get("assignee_id", type=int)
    status_filter = request.args.get("status", "all")
    task_type_filter = request.args.get("task_type", "").strip()
    sort_by = request.args.get("sort_by", "due_date")
    sort_dir = request.args.get("sort_dir", "asc")

    if search:
        term = search.lower()
        tasks = [t for t in tasks if term in (t.name or "").lower()]
    if assignee_id is not None:
        tasks = [t for t in tasks if t.assignee_id == assignee_id]
    if status_filter == "done":
        tasks = [t for t in tasks if t.status == "complete"]
    elif status_filter == "undone":
        tasks = [t for t in tasks if t.status == "incomplete"]
    elif status_filter == "not_applicable":
        tasks = [t for t in tasks if t.status == "not_applicable"]
    elif status_filter == "missed_deadline":
        tasks = [t for t in tasks if t.status == "missed_deadline"]
    if task_type_filter and task_type_filter in dict(TASK_TYPE_OPTIONS):
        tasks = [t for t in tasks if get_task_type(t.group) == task_type_filter]

    reverse = sort_dir == "desc"
    tasks = sorted(tasks, key=lambda t: _event_task_sort_key(t, sort_by), reverse=reverse)

    users = User.query.order_by(User.name.asc()).all()
    assignee_links = [(u.id, u.name) for u in users]
    task_timings = {t.id: _task_timing_class(t) for t in tasks}
    attendance_task_ids = {t.id for t in tasks if _is_attendance_task(t)}

    return render_template(
        "events/detail.html",
        event=event,
        tasks=tasks,
        users=users,
        assignee_links=assignee_links,
        task_timings=task_timings,
        attendance_task_ids=attendance_task_ids,
        task_type_options=TASK_TYPE_OPTIONS,
        task_type_filter=task_type_filter,
        status_filter=status_filter,
        status_filter_options=EVENT_STATUS_OPTIONS,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=EVENT_SORT_OPTIONS,
        search=search,
        assignee_id=assignee_id,
    )


def _event_detail_redirect(event_id, **extra):
    """Redirect to event detail, preserving current filter query params."""
    params = {k: v for k, v in request.args.items() if v}
    params.update(extra)
    return redirect(url_for("events.event_detail", event_id=event_id, **params))


@events_bp.route("/<int:event_id>/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(event_id: int, task_id: int):
    """Set task status: complete, not_applicable, or missed_deadline. For complete, accepts drive_link (required) and notes."""
    event = Event.query.get_or_404(event_id)
    task = EventTask.query.filter_by(id=task_id, event_id=event_id).first_or_404()

    status = (request.form.get("status") or "complete").strip().lower()
    if status not in ALLOWED_TASK_STATUSES:
        status = "complete"

    if _is_attendance_task(task) and status == "complete":
        attendees_val = request.form.get("attendees", "").strip()
        if not attendees_val:
            flash("Enter the number of attendees to mark this task complete.", "error")
            return _event_detail_redirect(event_id)
        try:
            event.attendees = int(attendees_val)
        except ValueError:
            flash("Attendees must be a number.", "error")
            return _event_detail_redirect(event_id)
        if event.attendees < 0:
            flash("Attendees cannot be negative.", "error")
            return _event_detail_redirect(event_id)

    if status == "complete":
        drive_link = request.form.get("drive_link", "").strip()
        requires_drive = task.template and getattr(task.template, "requires_drive_link", False)
        if requires_drive and not drive_link:
            flash("Please enter a link to the image (Google Drive, Dropbox, or OneDrive).", "error")
            return _event_detail_redirect(event_id)
        if drive_link and not is_allowed_drive_link(drive_link):
            flash("Link must be a valid https URL from Google Drive, Dropbox, or OneDrive.", "error")
            return _event_detail_redirect(event_id)
        task.drive_link = drive_link if drive_link else None
        task.screenshot_path = None
        notes_val = request.form.get("notes", "").strip()
        task.notes = notes_val or None
    else:
        task.drive_link = None
        notes_val = request.form.get("notes", "").strip()
        task.notes = notes_val or None

    task.status = status
    task.completed_at = datetime.utcnow()

    db.session.commit()
    flash(f"Task marked as {status.replace('_', ' ')}.", "success")
    return _event_detail_redirect(event_id)


@events_bp.route("/<int:event_id>/tasks/<int:task_id>/assign", methods=["POST"])
def assign_task(event_id: int, task_id: int):
    task = EventTask.query.filter_by(id=task_id, event_id=event_id).first_or_404()
    assignee_id = request.form.get("assignee_id")
    if assignee_id is not None and assignee_id != "":
        task.assignee_id = int(assignee_id)
    else:
        task.assignee_id = None
    db.session.commit()
    flash("Task assignee updated.", "success")
    return _event_detail_redirect(event_id)


    return redirect(url_for("events.event_detail", event_id=event_id))


@events_bp.route("/<int:event_id>/tasks/add", methods=["GET", "POST"])
def add_custom_task(event_id: int):
    event = Event.query.get_or_404(event_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        task_type = request.form.get("task_type", "").strip()
        due_type = request.form.get("due_type", "date").strip()
        due_date_s = request.form.get("due_date", "").strip()
        due_weekday = request.form.get("due_weekday", type=int)
        needs_notes = request.form.get("needs_notes") == "1"
        notes = request.form.get("notes", "").strip() or None
        assignee_id = request.form.get("assignee_id", type=int)
        if not name:
            flash("Task name is required.", "error")
            return redirect(url_for("events.add_custom_task", event_id=event_id))
        if due_type == "weekday" and due_weekday is not None:
            d = event.event_datetime.date()
            days_back = (d.weekday() - due_weekday + 7) % 7
            if days_back == 0:
                days_back = 7
            due_date = datetime.combine(d - timedelta(days=days_back), event.event_datetime.time())
        elif due_date_s:
            try:
                due_date = datetime.strptime(due_date_s, "%Y-%m-%d")
                due_date = due_date.replace(hour=17, minute=0, second=0, microsecond=0)
            except ValueError:
                flash("Invalid due date.", "error")
                return redirect(url_for("events.add_custom_task", event_id=event_id))
        else:
            flash("Due date or day of week is required.", "error")
            return redirect(url_for("events.add_custom_task", event_id=event_id))
        group = TASK_TYPE_TO_GROUP.get(task_type, "event_prep")
        task = EventTask(
            event_id=event_id,
            template_id=None,
            name=name,
            group=group,
            assignee_id=assignee_id,
            ideal_due_at=due_date,
            actual_due_at=due_date,
            status="incomplete",
            notes=notes if needs_notes else None,
        )
        db.session.add(task)
        db.session.commit()
        flash("Custom task added.", "success")
        return redirect(url_for("events.event_detail", event_id=event_id))
    users = User.query.order_by(User.name.asc()).all()
    WEEKDAY_OPTIONS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")]
    return render_template(
        "events/add_task.html",
        event=event,
        task_type_options=TASK_TYPE_OPTIONS,
        users=users,
        weekday_options=WEEKDAY_OPTIONS,
    )


@events_bp.route("/<int:event_id>/tasks/<int:task_id>/edit-due", methods=["POST"])
def edit_task_due(event_id: int, task_id: int):
    task = EventTask.query.filter_by(id=task_id, event_id=event_id).first_or_404()
    due_date_s = request.form.get("due_date", "").strip()
    if not due_date_s:
        flash("Due date is required.", "error")
        return redirect(url_for("events.event_detail", event_id=event_id))
    try:
        due_date = datetime.strptime(due_date_s, "%Y-%m-%d")
        due_date = due_date.replace(hour=17, minute=0, second=0, microsecond=0)
    except ValueError:
        flash("Invalid due date.", "error")
        return redirect(url_for("events.event_detail", event_id=event_id))
    task.actual_due_at = due_date
    task.ideal_due_at = due_date
    db.session.commit()
    flash("Due date updated.", "success")
    return redirect(url_for("events.event_detail", event_id=event_id))


@events_bp.route("/<int:event_id>/attendees", methods=["POST"])
def update_attendees(event_id: int):
    event = Event.query.get_or_404(event_id)
    val = request.form.get("attendees", "").strip()
    if val == "":
        event.attendees = None
    else:
        try:
            event.attendees = int(val)
        except ValueError:
            flash("Attendees must be a number.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))
    db.session.commit()
    flash("Attendees updated.", "success")
    return redirect(url_for("events.event_detail", event_id=event_id))


@events_bp.route("/<int:event_id>/regenerate-tasks", methods=["POST"])
def regenerate_tasks(event_id: int):
    """Re-create all tasks for this event from the template. Replaces existing tasks."""
    event = Event.query.get_or_404(event_id)
    EventTask.query.filter_by(event_id=event_id).delete()
    db.session.flush()
    generate_tasks_for_event(event)
    db.session.commit()
    flash("Tasks re-created from template. All tasks for this event were replaced.", "success")
    return redirect(url_for("events.event_detail", event_id=event_id))


@events_bp.route("/new", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        game_id = request.form.get("game_id", type=int)
        owner_id = request.form.get("owner_id", type=int)
        allowed_range = request.form.get("allowed_date_range", "").strip()
        notes = request.form.get("scheduling_notes", "").strip()
        event_type = request.form.get("event_type", "").strip()

        if not (title and date_str and owner_id):
            flash("Title, date, and owner are required.", "error")
            return redirect(url_for("events.create_event"))

        if not game_id:
            flash("Please select a game.", "error")
            return redirect(url_for("events.create_event"))
        game = Game.query.get(game_id)
        if not game:
            flash("Invalid game selected.", "error")
            return redirect(url_for("events.create_event"))

        owner = User.query.get(owner_id)
        if not owner:
            flash("Invalid owner selected.", "error")
            return redirect(url_for("events.create_event"))

        try:
            event_date = datetime.fromisoformat(date_str)
        except ValueError:
            try:
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
                event_date = parsed
            except ValueError:
                flash("Invalid date format.", "error")
                return redirect(url_for("events.create_event"))

        if time_str:
            try:
                t = datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                flash("Invalid time format.", "error")
                return redirect(url_for("events.create_event"))
            event_dt = datetime.combine(event_date.date(), t)
        else:
            event_dt = datetime.combine(event_date.date(), time_cls(18, 0))

        event = Event(
            title=title,
            owner=owner,
            game=game,
            event_type=event_type or None,
            event_datetime=event_dt,
            allowed_date_range=allowed_range or None,
            scheduling_notes=notes or None,
        )

        db.session.add(event)
        db.session.flush()
        generate_tasks_for_event(event)
        db.session.commit()

        flash("Event created.", "success")
        return redirect(url_for("events.list_events"))

    games = Game.query.order_by(Game.name.asc()).all()
    users = User.query.order_by(User.name.asc()).all()
    event_type_options = EventType.query.order_by(EventType.name.asc()).all()
    return render_template("events/new.html", games=games, users=users, event_type_options=event_type_options)


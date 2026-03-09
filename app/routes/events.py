from datetime import datetime, timedelta, time as time_cls
import os
import uuid

from flask import Blueprint, current_app, redirect, render_template, request, url_for, flash

from .. import db
from ..models import Event, EventType, Game, User, EventTask
from ..services.tasks import generate_tasks_for_event

events_bp = Blueprint("events", __name__, url_prefix="/events")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


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


@events_bp.route("/")
def list_events():
    events = Event.query.order_by(Event.event_datetime.asc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/<int:event_id>")
def event_detail(event_id: int):
    event = Event.query.get_or_404(event_id)
    tasks = (
        EventTask.query.filter_by(event_id=event.id)
        .order_by(EventTask.actual_due_at.asc())
        .all()
    )
    users = User.query.order_by(User.name.asc()).all()
    task_timings = {t.id: _task_timing_class(t) for t in tasks}
    attendance_task_ids = {t.id for t in tasks if _is_attendance_task(t)}
    return render_template(
        "events/detail.html",
        event=event,
        tasks=tasks,
        users=users,
        task_timings=task_timings,
        attendance_task_ids=attendance_task_ids,
    )


@events_bp.route("/<int:event_id>/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(event_id: int, task_id: int):
    event = Event.query.get_or_404(event_id)
    task = EventTask.query.filter_by(id=task_id, event_id=event_id).first_or_404()

    if _is_attendance_task(task):
        attendees_val = request.form.get("attendees", "").strip()
        if not attendees_val:
            flash("Enter the number of attendees to mark this task complete.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))
        try:
            event.attendees = int(attendees_val)
        except ValueError:
            flash("Attendees must be a number.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))
        if event.attendees < 0:
            flash("Attendees cannot be negative.", "error")
            return redirect(url_for("events.event_detail", event_id=event_id))

    task.status = "complete"
    task.completed_at = datetime.utcnow()

    file = request.files.get("screenshot")
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[-1].lower()
        safe_name = f"task_{task_id}_{uuid.uuid4().hex[:8]}.{ext}"
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        file.save(os.path.join(upload_dir, safe_name))
        task.screenshot_path = safe_name

    db.session.commit()
    flash("Task marked complete.", "success")
    return redirect(url_for("events.event_detail", event_id=event_id))


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


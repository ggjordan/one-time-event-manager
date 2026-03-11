from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, request, url_for, flash
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from .. import db
from ..models import Event, EventTask, User
from ..utils.url_validation import is_allowed_drive_link
from ..services.task_types import (
    TASK_TYPE_OPTIONS,
    get_task_type,
    get_task_type_label,
    GROUP_TO_TYPE,
)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

GROUP_BY_OPTIONS = [
    ("assignee", "Assignee"),
    ("task_type", "Task type"),
    ("group", "Template group"),
    ("game", "Game"),
]
SORT_COLUMNS = [
    ("task", "Task"),
    ("event", "Event"),
    ("game", "Game"),
    ("days_until_due", "Days until due"),
    ("due_date", "Due date"),
    ("status", "Status"),
    ("assignee", "Assignee"),
]
STATUS_FILTER_OPTIONS = [
    ("all", "All"),
    ("undone", "Incomplete (to-do)"),
    ("done", "Complete only"),
    ("not_applicable", "Not applicable"),
    ("missed_deadline", "Missed deadline"),
]
DUE_WITHIN_OPTIONS = [
    ("", "Any due date"),
    ("1", "Due within 1 day"),
    ("3", "Due within 3 days"),
    ("7", "Due this week"),
]


def _group_key_task(task, group_by):
    if group_by == "assignee":
        if task.assignee_id is None:
            return ("__unassigned__", "Unassigned")
        return (task.assignee_id, task.assignee.name if task.assignee else "Unknown")
    if group_by == "task_type":
        tt = get_task_type(task.group)
        return (tt, get_task_type_label(tt))
    if group_by == "group":
        return (task.group or "__none__", task.group or "Other")
    if group_by == "game":
        game_name = task.event.game.name if task.event and task.event.game else ""
        return (game_name or "__none__", game_name or "Other")
    return (None, "Other")


def _sort_key_task(task, sort_by):
    if sort_by == "due_date":
        return (task.actual_due_at is None, task.actual_due_at or "")
    if sort_by == "days_until_due":
        if not task.actual_due_at:
            return (1, None)  # no due date last when asc
        now = datetime.utcnow()
        if task.actual_due_at.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        delta = (task.actual_due_at.replace(tzinfo=None) if task.actual_due_at.tzinfo else task.actual_due_at) - now
        days = delta.total_seconds() / 86400
        return (0, days)
    if sort_by == "name" or sort_by == "task":
        return (task.name or "")
    if sort_by == "event":
        return (task.event.title if task.event else "")
    if sort_by == "game":
        return (task.event.game.name if task.event and task.event.game else "")
    if sort_by == "status":
        return (task.status == "complete", task.completed_at or "")
    if sort_by == "assignee":
        return (task.assignee.name if task.assignee else "")
    return (task.actual_due_at is None, task.actual_due_at or "")


def _build_task_list(
    assignee_id=None,
    status_filter="all",
    search="",
    due_within="",
    due_date_from=None,
    due_date_to=None,
    task_type_filter="",
):
    q = (
        EventTask.query.options(
            joinedload(EventTask.event).joinedload(Event.game),
            joinedload(EventTask.assignee),
        )
    )
    if assignee_id is not None:
        q = q.filter(EventTask.assignee_id == assignee_id)
    if status_filter == "done":
        q = q.filter(EventTask.status == "complete")
    elif status_filter == "undone":
        q = q.filter(EventTask.status == "incomplete")
    elif status_filter == "not_applicable":
        q = q.filter(EventTask.status == "not_applicable")
    elif status_filter == "missed_deadline":
        q = q.filter(EventTask.status == "missed_deadline")

    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.join(Event).filter(
            or_(
                EventTask.name.ilike(term),
                Event.title.ilike(term),
            )
        )
    if due_date_from:
        q = q.filter(EventTask.actual_due_at >= due_date_from)
    if due_date_to:
        q = q.filter(EventTask.actual_due_at <= due_date_to)
    if due_within == "1":
        now = datetime.utcnow()
        end = now + timedelta(days=1)
        q = q.filter(EventTask.actual_due_at >= now, EventTask.actual_due_at <= end)
    elif due_within == "3":
        now = datetime.utcnow()
        end = now + timedelta(days=3)
        q = q.filter(EventTask.actual_due_at >= now, EventTask.actual_due_at <= end)
    elif due_within == "7":
        now = datetime.utcnow()
        end = now + timedelta(days=7)
        q = q.filter(EventTask.actual_due_at >= now, EventTask.actual_due_at <= end)

    if task_type_filter and task_type_filter in dict(TASK_TYPE_OPTIONS):
        groups_for_type = [g for g, t in GROUP_TO_TYPE.items() if t == task_type_filter]
        if groups_for_type:
            q = q.filter(EventTask.group.in_(groups_for_type))
        else:
            q = q.filter(EventTask.group == task_type_filter)

    return q.all()


def _sort_tasks(tasks, sort_by, sort_dir):
    reverse = sort_dir == "desc"
    return sorted(tasks, key=lambda t: _sort_key_task(t, sort_by), reverse=reverse)


def _days_until_due(task):
    if not task.actual_due_at:
        return None
    now = datetime.utcnow()
    due = task.actual_due_at.replace(tzinfo=None) if task.actual_due_at.tzinfo else task.actual_due_at
    delta = due - now
    return int(round(delta.total_seconds() / 86400))


def _build_task_list_args():
    return {
        "group_by": request.args.get("group_by", "assignee"),
        "sort_by": request.args.get("sort_by", "due_date"),
        "sort_dir": request.args.get("sort_dir", "asc"),
        "status_filter": request.args.get("status", "all"),
        "assignee_id": request.args.get("assignee_id", type=int),
        "search": request.args.get("search", "").strip(),
        "due_within": request.args.get("due_within", ""),
        "task_type_filter": request.args.get("task_type", ""),
    }


def _parse_due_range():
    due_date_from = None
    due_date_to = None
    from_str = request.args.get("due_date_from", "").strip()
    to_str = request.args.get("due_date_to", "").strip()
    if from_str:
        try:
            due_date_from = datetime.strptime(from_str, "%Y-%m-%d")
        except ValueError:
            pass
    if to_str:
        try:
            due_date_to = datetime.strptime(to_str, "%Y-%m-%d")
            due_date_to = due_date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            pass
    return due_date_from, due_date_to


@tasks_bp.route("/")
def list_tasks():
    args = _build_task_list_args()
    due_date_from, due_date_to = _parse_due_range()

    tasks = _build_task_list(
        assignee_id=args["assignee_id"],
        status_filter=args["status_filter"],
        search=args["search"],
        due_within=args["due_within"],
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        task_type_filter=args["task_type_filter"],
    )

    groups = {}
    for task in tasks:
        key, label = _group_key_task(task, args["group_by"])
        if key not in groups:
            groups[key] = {"label": label, "tasks": []}
        groups[key]["tasks"].append(task)

    for key in groups:
        groups[key]["tasks"] = _sort_tasks(
            groups[key]["tasks"], args["sort_by"], args["sort_dir"]
        )

    group_list = sorted(
        groups.items(),
        key=lambda x: (x[0] == "__unassigned__", str(x[1]["label"])),
    )

    assignee_links = [
        (u.id, u.name)
        for u in User.query.join(EventTask, User.id == EventTask.assignee_id)
        .distinct()
        .order_by(User.name.asc())
        .all()
    ]

    return render_template(
        "tasks/list.html",
        group_list=group_list,
        group_by=args["group_by"],
        sort_by=args["sort_by"],
        sort_dir=args["sort_dir"],
        status_filter=args["status_filter"],
        assignee_id=args["assignee_id"],
        assignee_links=assignee_links,
        group_by_options=GROUP_BY_OPTIONS,
        sort_columns=SORT_COLUMNS,
        status_filter_options=STATUS_FILTER_OPTIONS,
        due_within_options=DUE_WITHIN_OPTIONS,
        task_type_options=TASK_TYPE_OPTIONS,
        search=args["search"],
        due_within=args["due_within"],
        due_date_from=request.args.get("due_date_from", ""),
        due_date_to=request.args.get("due_date_to", ""),
        task_type_filter=args["task_type_filter"],
        days_until_due_fn=_days_until_due,
        get_task_type=get_task_type,
    )


@tasks_bp.route("/assignee/<int:user_id>")
def tasks_by_assignee(user_id):
    user = User.query.get_or_404(user_id)
    args = _build_task_list_args()
    args["assignee_id"] = user_id
    due_date_from, due_date_to = _parse_due_range()

    tasks = _build_task_list(
        assignee_id=user_id,
        status_filter=args["status_filter"],
        search=args["search"],
        due_within=args["due_within"],
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        task_type_filter=args["task_type_filter"],
    )

    groups = {}
    for task in tasks:
        key, label = _group_key_task(task, args["group_by"])
        if key not in groups:
            groups[key] = {"label": label, "tasks": []}
        groups[key]["tasks"].append(task)

    for key in groups:
        groups[key]["tasks"] = _sort_tasks(
            groups[key]["tasks"], args["sort_by"], args["sort_dir"]
        )

    group_list = sorted(
        groups.items(),
        key=lambda x: (x[0] == "__unassigned__", str(x[1]["label"])),
    )

    assignee_links = [
        (u.id, u.name)
        for u in User.query.join(EventTask, User.id == EventTask.assignee_id)
        .distinct()
        .order_by(User.name.asc())
        .all()
    ]

    return render_template(
        "tasks/list.html",
        group_list=group_list,
        group_by=args["group_by"],
        sort_by=args["sort_by"],
        sort_dir=args["sort_dir"],
        status_filter=args["status_filter"],
        assignee_id=user_id,
        assignee_name=user.name,
        assignee_links=[],
        group_by_options=GROUP_BY_OPTIONS,
        sort_columns=SORT_COLUMNS,
        status_filter_options=STATUS_FILTER_OPTIONS,
        due_within_options=DUE_WITHIN_OPTIONS,
        task_type_options=TASK_TYPE_OPTIONS,
        search=args["search"],
        due_within=args["due_within"],
        due_date_from=request.args.get("due_date_from", ""),
        due_date_to=request.args.get("due_date_to", ""),
        task_type_filter=args["task_type_filter"],
        days_until_due_fn=_days_until_due,
        get_task_type=get_task_type,
    )


def _is_attendance_task(task):
    return task and "record attendance" in (task.name or "").lower()


def _list_tasks_redirect_params():
    return {
        "search": request.form.get("list_search", "").strip(),
        "assignee_id": request.form.get("list_assignee_id", type=int) or "",
        "status": request.form.get("list_status", "all"),
        "due_within": request.form.get("list_due_within", ""),
        "due_date_from": request.form.get("list_due_date_from", ""),
        "due_date_to": request.form.get("list_due_date_to", ""),
        "task_type": request.form.get("list_task_type", ""),
        "group_by": request.form.get("list_group_by", "assignee"),
        "sort_by": request.form.get("list_sort_by", "due_date"),
        "sort_dir": request.form.get("list_sort_dir", "asc"),
    }


@tasks_bp.route("/<int:task_id>/set-status", methods=["POST"])
def set_task_status(task_id: int):
    task = EventTask.query.options(joinedload(EventTask.event)).get_or_404(task_id)
    status = (request.form.get("status") or "complete").strip().lower()
    if status not in ("complete", "not_applicable", "missed_deadline"):
        status = "complete"

    if _is_attendance_task(task) and status == "complete":
        attendees_val = request.form.get("attendees", "").strip()
        if not attendees_val:
            flash("Enter the number of attendees to mark this task complete.", "error")
            params = {k: v for k, v in _list_tasks_redirect_params().items() if v not in (None, "")}
            return redirect(url_for("tasks.list_tasks", **params))
        try:
            task.event.attendees = int(attendees_val)
        except ValueError:
            flash("Attendees must be a number.", "error")
            params = {k: v for k, v in _list_tasks_redirect_params().items() if v not in (None, "")}
            return redirect(url_for("tasks.list_tasks", **params))

    if status == "complete":
        drive_link = request.form.get("drive_link", "").strip()
        requires_drive = task.template and getattr(task.template, "requires_drive_link", False)
        if requires_drive and not drive_link:
            flash("Please enter a link when marking Complete.", "error")
            params = {k: v for k, v in _list_tasks_redirect_params().items() if v not in (None, "")}
            return redirect(url_for("tasks.list_tasks", **params))
        if drive_link and not is_allowed_drive_link(drive_link):
            flash("Link must be a valid https URL from Google Drive, Dropbox, or OneDrive.", "error")
            params = {k: v for k, v in _list_tasks_redirect_params().items() if v not in (None, "")}
            return redirect(url_for("tasks.list_tasks", **params))
        task.drive_link = drive_link if drive_link else None
        task.screenshot_path = None
    else:
        task.drive_link = None

    notes_val = request.form.get("notes", "").strip()
    task.notes = notes_val or None
    task.status = status
    task.completed_at = datetime.utcnow()
    db.session.commit()
    flash("Task status updated.", "success")
    params = {k: v for k, v in _list_tasks_redirect_params().items() if v not in (None, "")}
    return redirect(url_for("tasks.list_tasks", **params))

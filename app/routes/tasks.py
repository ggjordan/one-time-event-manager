from flask import Blueprint, render_template, request, url_for
from sqlalchemy.orm import joinedload

from ..models import Event, EventTask, User

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

GROUP_BY_OPTIONS = [
    ("assignee", "Assignee"),
    ("group", "Task type"),
    ("game", "Game"),
]
SORT_COLUMNS = [
    ("task", "Task"),
    ("event", "Event"),
    ("game", "Game"),
    ("due_date", "Due date"),
    ("status", "Status"),
    ("assignee", "Assignee"),
]
STATUS_FILTER_OPTIONS = [
    ("all", "All"),
    ("done", "Done only"),
    ("undone", "Undone only"),
]


def _group_key_task(task, group_by):
    if group_by == "assignee":
        if task.assignee_id is None:
            return ("__unassigned__", "Unassigned")
        return (task.assignee_id, task.assignee.name if task.assignee else "Unknown")
    if group_by == "group":
        return (task.group or "__none__", task.group or "Other")
    if group_by == "game":
        game_name = task.event.game.name if task.event and task.event.game else ""
        return (game_name or "__none__", game_name or "Other")
    return (None, "Other")


def _sort_key_task(task, sort_by):
    if sort_by == "due_date":
        return (task.actual_due_at is None, task.actual_due_at or "")
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


def _build_task_list(assignee_id=None, status_filter="all"):
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
        q = q.filter(EventTask.status != "complete")
    return q.all()


def _sort_tasks(tasks, sort_by, sort_dir):
    reverse = sort_dir == "desc"
    return sorted(tasks, key=lambda t: _sort_key_task(t, sort_by), reverse=reverse)


@tasks_bp.route("/")
def list_tasks():
    group_by = request.args.get("group_by", "assignee")
    sort_by = request.args.get("sort_by", "due_date")
    sort_dir = request.args.get("sort_dir", "asc")
    status_filter = request.args.get("status", "all")
    assignee_id = request.args.get("assignee_id", type=int)

    tasks = _build_task_list(assignee_id=assignee_id, status_filter=status_filter)

    groups = {}
    for task in tasks:
        key, label = _group_key_task(task, group_by)
        if key not in groups:
            groups[key] = {"label": label, "tasks": []}
        groups[key]["tasks"].append(task)

    for key in groups:
        groups[key]["tasks"] = _sort_tasks(groups[key]["tasks"], sort_by, sort_dir)

    group_list = sorted(groups.items(), key=lambda x: (x[0] == "__unassigned__", str(x[1]["label"])))

    assignee_links = (
        [(u.id, u.name) for u in User.query.join(EventTask, User.id == EventTask.assignee_id).distinct().order_by(User.name.asc()).all()]
        if not assignee_id else []
    )

    return render_template(
        "tasks/list.html",
        group_list=group_list,
        group_by=group_by,
        sort_by=sort_by,
        sort_dir=sort_dir,
        status_filter=status_filter,
        assignee_id=assignee_id,
        assignee_links=assignee_links,
        group_by_options=GROUP_BY_OPTIONS,
        sort_columns=SORT_COLUMNS,
        status_filter_options=STATUS_FILTER_OPTIONS,
    )


@tasks_bp.route("/assignee/<int:user_id>")
def tasks_by_assignee(user_id):
    user = User.query.get_or_404(user_id)
    group_by = request.args.get("group_by", "group")
    sort_by = request.args.get("sort_by", "due_date")
    sort_dir = request.args.get("sort_dir", "asc")
    status_filter = request.args.get("status", "all")

    tasks = _build_task_list(assignee_id=user_id, status_filter=status_filter)

    groups = {}
    for task in tasks:
        key, label = _group_key_task(task, group_by)
        if key not in groups:
            groups[key] = {"label": label, "tasks": []}
        groups[key]["tasks"].append(task)

    for key in groups:
        groups[key]["tasks"] = _sort_tasks(groups[key]["tasks"], sort_by, sort_dir)

    group_list = sorted(groups.items(), key=lambda x: (x[0] == "__unassigned__", str(x[1]["label"])))

    return render_template(
        "tasks/list.html",
        group_list=group_list,
        group_by=group_by,
        sort_by=sort_by,
        sort_dir=sort_dir,
        status_filter=status_filter,
        assignee_id=user_id,
        assignee_name=user.name,
        assignee_links=[],  # On per-person page, no assignee quick links
        group_by_options=GROUP_BY_OPTIONS,
        sort_columns=SORT_COLUMNS,
        status_filter_options=STATUS_FILTER_OPTIONS,
    )

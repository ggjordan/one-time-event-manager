from flask import Blueprint, redirect, render_template, request, url_for, flash

from .. import db
from ..models import TaskTemplate, Game
from ..services.task_types import TASK_TYPE_OPTIONS, TASK_TYPE_TO_GROUP, get_task_type, get_task_type_label

task_templates_bp = Blueprint("task_templates", __name__, url_prefix="/task-templates")


def _group_options():
    return list(TASK_TYPE_OPTIONS)


@task_templates_bp.route("/")
def list_templates():
    templates = (
        TaskTemplate.query.order_by(
            TaskTemplate.lead_days_before_event.desc(),
            TaskTemplate.name.asc(),
        ).all()
    )
    return render_template(
        "task_templates/list.html",
        templates=templates,
        task_type_options=TASK_TYPE_OPTIONS,
        get_task_type_label=get_task_type_label,
        get_task_type=get_task_type,
    )


@task_templates_bp.route("/add", methods=["GET", "POST"])
def add_template():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        group = request.form.get("group", "").strip()
        due_type = request.form.get("due_type", "days").strip()
        lead_days = request.form.get("lead_days_before_event", type=int)
        due_weekday = request.form.get("due_weekday", type=int)
        requires_notes = request.form.get("requires_notes") == "1"
        requires_drive_link = request.form.get("requires_drive_link") == "1"
        game_ids = request.form.getlist("game_ids", type=int)
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("task_templates.add_template"))
        if not group:
            flash("Task type (group) is required.", "error")
            return redirect(url_for("task_templates.add_template"))
        internal_group = TASK_TYPE_TO_GROUP.get(group, group)
        if lead_days is None:
            lead_days = 0
        t = TaskTemplate(
            name=name,
            group=internal_group,
            lead_days_before_event=lead_days,
            due_weekday=due_weekday if due_type == "weekday" and due_weekday is not None else None,
            order_index=0,
            requires_notes=requires_notes,
            requires_drive_link=requires_drive_link,
            is_active=True,
        )
        db.session.add(t)
        db.session.flush()
        for gid in game_ids:
            g = Game.query.get(gid)
            if g:
                t.games.append(g)
        db.session.commit()
        flash("Task template added.", "success")
        return redirect(url_for("task_templates.list_templates"))
    games = Game.query.order_by(Game.name.asc()).all()
    return render_template(
        "task_templates/add.html",
        task_type_options=TASK_TYPE_OPTIONS,
        group_options=_group_options(),
        games=games,
        weekday_options=[(i, d) for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])],
    )


@task_templates_bp.route("/<int:template_id>/edit", methods=["GET", "POST"])
def edit_template(template_id: int):
    t = TaskTemplate.query.get_or_404(template_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        group = request.form.get("group", "").strip()
        due_type = request.form.get("due_type", "days").strip()
        lead_days = request.form.get("lead_days_before_event", type=int)
        due_weekday = request.form.get("due_weekday", type=int)
        requires_notes = request.form.get("requires_notes") == "1"
        requires_drive_link = request.form.get("requires_drive_link") == "1"
        game_ids = request.form.getlist("game_ids", type=int)
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("task_templates.edit_template", template_id=template_id))
        if not group:
            flash("Task type (group) is required.", "error")
            return redirect(url_for("task_templates.edit_template", template_id=template_id))
        internal_group = TASK_TYPE_TO_GROUP.get(group, group)
        t.name = name
        t.group = internal_group
        t.lead_days_before_event = lead_days if lead_days is not None else 0
        t.due_weekday = due_weekday if due_type == "weekday" and due_weekday is not None else None
        t.requires_notes = requires_notes
        t.requires_drive_link = requires_drive_link
        t.games = [Game.query.get(gid) for gid in game_ids]
        t.games = [g for g in t.games if g is not None]
        db.session.commit()
        flash("Task template updated.", "success")
        return redirect(url_for("task_templates.list_templates"))
    games = Game.query.order_by(Game.name.asc()).all()
    return render_template(
        "task_templates/edit.html",
        template=t,
        task_type_options=TASK_TYPE_OPTIONS,
        get_task_type_label=get_task_type_label,
        group_options=_group_options(),
        current_task_type=get_task_type(t.group),
        games=games,
        weekday_options=[(i, d) for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])],
    )


@task_templates_bp.route("/<int:template_id>/deactivate", methods=["POST"])
def deactivate_template(template_id: int):
    t = TaskTemplate.query.get_or_404(template_id)
    t.is_active = False
    db.session.commit()
    flash("Task template deactivated. It will no longer be added to new events.", "success")
    return redirect(url_for("task_templates.list_templates"))


@task_templates_bp.route("/<int:template_id>/activate", methods=["POST"])
def activate_template(template_id: int):
    t = TaskTemplate.query.get_or_404(template_id)
    t.is_active = True
    db.session.commit()
    flash("Task template activated.", "success")
    return redirect(url_for("task_templates.list_templates"))

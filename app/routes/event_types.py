from flask import Blueprint, redirect, render_template, request, url_for, flash

from .. import db
from ..models import Event, EventType

event_types_bp = Blueprint("event_types", __name__, url_prefix="/event-types")


@event_types_bp.route("/")
def list_event_types():
    types = EventType.query.order_by(EventType.name.asc()).all()
    return render_template("event_types/list.html", event_types=types)


@event_types_bp.route("/add", methods=["GET", "POST"])
def add_event_type():
    next_url = request.args.get("next", url_for("events.create_event"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Event type name is required.", "error")
            return redirect(url_for("event_types.add_event_type", next=next_url))
        existing = EventType.query.filter_by(name=name).first()
        if existing:
            flash(f"An event type named \"{name}\" already exists.", "error")
            return redirect(url_for("event_types.add_event_type", next=next_url))
        db.session.add(EventType(name=name))
        db.session.commit()
        flash(f"Added event type: {name}.", "success")
        return redirect(next_url)
    return render_template("event_types/add.html", next_url=next_url)


@event_types_bp.route("/merge", methods=["GET", "POST"])
def merge_event_types():
    types = EventType.query.order_by(EventType.name.asc()).all()
    if request.method == "POST":
        from_id = request.form.get("from_id", type=int)
        to_id = request.form.get("to_id", type=int)
        if not from_id or not to_id or from_id == to_id:
            flash("Select two different event types to merge.", "error")
            return redirect(url_for("event_types.merge_event_types"))
        from_type = EventType.query.get(from_id)
        to_type = EventType.query.get(to_id)
        if not from_type or not to_type:
            flash("Invalid event type selected.", "error")
            return redirect(url_for("event_types.merge_event_types"))
        Event.query.filter_by(event_type=from_type.name).update({"event_type": to_type.name})
        merged_name = from_type.name
        db.session.delete(from_type)
        db.session.commit()
        flash(f"Merged \"{merged_name}\" into \"{to_type.name}\".", "success")
        return redirect(url_for("event_types.list_event_types"))
    return render_template("event_types/merge.html", event_types=types)

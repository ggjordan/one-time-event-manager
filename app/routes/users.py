from flask import Blueprint, redirect, render_template, request, url_for, flash
from sqlalchemy import or_

from .. import db
from ..models import User, Event, EventTask, Game

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
def list_users():
    search = request.args.get("search", "").strip()
    q = User.query
    if search:
        term = f"%{search}%"
        q = q.filter(or_(User.name.ilike(term), User.email.ilike(term)))
    users = q.order_by(User.name.asc()).all()
    return render_template("users/list.html", users=users, search=search)


@users_bp.route("/add", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not (name and email):
            flash("Name and email are required.", "error")
            return redirect(url_for("users.add_user"))
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash(f"A user with email {email} already exists.", "error")
            return redirect(url_for("users.add_user"))
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()
        flash(f"Added {name}.", "success")
        return redirect(url_for("users.list_users"))
    return render_template("users/add.html")


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not (name and email):
            flash("Name and email are required.", "error")
            return redirect(url_for("users.edit_user", user_id=user_id))
        other = User.query.filter_by(email=email).first()
        if other and other.id != user_id:
            flash(f"A user with email {email} already exists.", "error")
            return redirect(url_for("users.edit_user", user_id=user_id))
        user.name = name
        user.email = email
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("users.list_users"))
    return render_template("users/edit.html", user=user)


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id: int):
    """Permanently delete a user. Deletes events they own (and those tasks), unassigns their tasks, clears game lead."""
    user = User.query.get_or_404(user_id)
    name = user.name
    # Delete events owned by this user (cascade deletes their tasks)
    for event in list(user.events_owned):
        db.session.delete(event)
    # Unassign any tasks still assigned to them (e.g. on other users' events)
    EventTask.query.filter_by(assignee_id=user_id).update({"assignee_id": None})
    # Clear game lead if they were lead
    Game.query.filter_by(lead_user_id=user_id).update({"lead_user_id": None})
    db.session.delete(user)
    db.session.commit()
    flash(f"User “{name}” has been permanently deleted.", "success")
    return redirect(url_for("users.list_users"))


@users_bp.route("/merge", methods=["GET", "POST"])
def merge_users():
    users = User.query.order_by(User.name.asc()).all()
    if request.method == "POST":
        from_id = request.form.get("from_id", type=int)
        to_id = request.form.get("to_id", type=int)
        if not from_id or not to_id or from_id == to_id:
            flash("Select two different users to merge.", "error")
            return redirect(url_for("users.merge_users"))
        from_user = User.query.get(from_id)
        to_user = User.query.get(to_id)
        if not from_user or not to_user:
            flash("Invalid user selected.", "error")
            return redirect(url_for("users.merge_users"))
        Event.query.filter_by(owner_id=from_id).update({"owner_id": to_id})
        EventTask.query.filter_by(assignee_id=from_id).update({"assignee_id": to_id})
        Game.query.filter_by(lead_user_id=from_id).update({"lead_user_id": to_id})
        merged_name = from_user.name
        db.session.delete(from_user)
        db.session.commit()
        flash(f"Merged {merged_name} into {to_user.name}.", "success")
        return redirect(url_for("users.list_users"))
    return render_template("users/merge.html", users=users)

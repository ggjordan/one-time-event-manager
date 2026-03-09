from flask import Blueprint, redirect, render_template, request, url_for, flash

from .. import db
from ..models import User, Event, EventTask, Game

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
def list_users():
    users = User.query.order_by(User.name.asc()).all()
    return render_template("users/list.html", users=users)


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

from flask import Blueprint, redirect, render_template, request, url_for, flash

from .. import db
from ..models import Event, Game

games_bp = Blueprint("games", __name__, url_prefix="/games")


@games_bp.route("/")
def list_games():
    games = Game.query.order_by(Game.name.asc()).all()
    return render_template("games/list.html", games=games)


@games_bp.route("/add", methods=["GET", "POST"])
def add_game():
    next_url = request.args.get("next", url_for("events.create_event"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("games.add_game", next=next_url))
        existing = Game.query.filter_by(name=name).first()
        if existing:
            flash(f"A game named \"{name}\" already exists.", "error")
            return redirect(url_for("games.add_game", next=next_url))
        db.session.add(Game(name=name))
        db.session.commit()
        flash(f"Added game: {name}.", "success")
        return redirect(next_url)
    return render_template("games/add.html", next_url=next_url)


@games_bp.route("/merge", methods=["GET", "POST"])
def merge_games():
    games = Game.query.order_by(Game.name.asc()).all()
    if request.method == "POST":
        from_id = request.form.get("from_id", type=int)
        to_id = request.form.get("to_id", type=int)
        if not from_id or not to_id or from_id == to_id:
            flash("Select two different games to merge.", "error")
            return redirect(url_for("games.merge_games"))
        from_game = Game.query.get(from_id)
        to_game = Game.query.get(to_id)
        if not from_game or not to_game:
            flash("Invalid game selected.", "error")
            return redirect(url_for("games.merge_games"))
        Event.query.filter_by(game_id=from_id).update({"game_id": to_id})
        merged_name = from_game.name
        db.session.delete(from_game)
        db.session.commit()
        flash(f"Merged \"{merged_name}\" into \"{to_game.name}\".", "success")
        return redirect(url_for("games.list_games"))
    return render_template("games/merge.html", games=games)

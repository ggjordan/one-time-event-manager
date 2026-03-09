from .. import db
from ..models import Game


DEFAULT_GAMES = [
    "Magic",
    "Pokemon",
    "Star Wars",
    "Flesh and Blood",
    "Lorcana",
    "One Piece",
    "Gundam",
    "Riftbound",
    "Sorcery",
    "Board Games",
]


def seed_default_games():
    """Ensure default games exist (add any missing)."""
    for name in DEFAULT_GAMES:
        if Game.query.filter_by(name=name).first() is None:
            db.session.add(Game(name=name))
    db.session.commit()

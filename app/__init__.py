from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_dir = os.path.join(base_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    default_db_path = os.path.join(instance_dir, "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{default_db_path}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    upload_dir = os.path.join(instance_dir, "uploads", "screenshots")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so they are registered with SQLAlchemy before migrations
    from . import models  # noqa: F401
    from .services.tasks import seed_default_task_templates
    from .services.games import seed_default_games
    from .services.event_types import seed_default_event_types

    from .routes.main import main_bp
    from .routes.events import events_bp
    from .routes.tasks import tasks_bp
    from .routes.users import users_bp
    from .routes.reports import reports_bp
    from .routes.games import games_bp
    from .routes.event_types import event_types_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(event_types_bp)

    # Seed default task templates, games, and event types (skip if tables not yet migrated)
    with app.app_context():
        try:
            seed_default_task_templates()
            seed_default_games()
            seed_default_event_types()
        except Exception as e:
            from sqlalchemy.exc import OperationalError
            if isinstance(e, OperationalError) and "no such table" in str(e).lower():
                pass  # Tables not created yet; run flask db upgrade first
            else:
                raise

    return app


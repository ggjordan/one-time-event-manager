from datetime import datetime

from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    picture_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    events_owned = db.relationship("Event", back_populates="owner", lazy="dynamic")
    tasks_assigned = db.relationship("EventTask", back_populates="assignee", lazy="dynamic")


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    lead_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    lead_user = db.relationship("User", backref="games_led")
    events = db.relationship("Event", back_populates="game", lazy="dynamic")


# Association: which games a task template applies to (empty = all games)
task_template_game = db.Table(
    "task_template_game",
    db.Column("task_template_id", db.Integer, db.ForeignKey("task_template.id"), primary_key=True),
    db.Column("game_id", db.Integer, db.ForeignKey("game.id"), primary_key=True),
)


class EventType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"), nullable=False)

    event_type = db.Column(db.String(128))
    event_datetime = db.Column(db.DateTime, nullable=False)
    allowed_date_range = db.Column(db.String(255))
    scheduling_notes = db.Column(db.Text)
    date_finalized = db.Column(db.DateTime)

    attendees = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    owner = db.relationship("User", back_populates="events_owned")
    game = db.relationship("Game", back_populates="events")
    tasks = db.relationship(
        "EventTask", back_populates="event", cascade="all, delete-orphan", lazy="dynamic"
    )


class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    group = db.Column(db.String(64), nullable=False)
    lead_days_before_event = db.Column(db.Integer, nullable=False)
    due_weekday = db.Column(db.Integer, nullable=True)  # 0=Monday, 6=Sunday; if set, due on that weekday before event
    order_index = db.Column(db.Integer, nullable=False, default=0)
    requires_notes = db.Column(db.Boolean, default=False, nullable=False)
    requires_drive_link = db.Column(db.Boolean, default=False, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tasks = db.relationship("EventTask", back_populates="template", lazy="dynamic")
    games = db.relationship(
        "Game",
        secondary=task_template_game,
        backref=db.backref("task_templates", lazy="dynamic"),
        lazy="dynamic",
    )


class EventTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("task_template.id"))

    name = db.Column(db.String(255), nullable=False)
    group = db.Column(db.String(64))

    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    ideal_due_at = db.Column(db.DateTime)
    actual_due_at = db.Column(db.DateTime)

    status = db.Column(db.String(32), default="incomplete", nullable=False)
    completed_at = db.Column(db.DateTime)

    screenshot_path = db.Column(db.String(512))  # legacy
    drive_link = db.Column(db.String(512))  # Google Drive / link to image
    notes = db.Column(db.Text)
    requires_notes = db.Column(db.Boolean, default=False, nullable=False)  # for custom tasks; template tasks use template.requires_notes

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event = db.relationship("Event", back_populates="tasks")
    template = db.relationship("TaskTemplate", back_populates="tasks")
    assignee = db.relationship("User", back_populates="tasks_assigned")


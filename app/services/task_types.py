"""Task type groups for filtering and display.

User-facing types: Online Store Tasks, Asset Creation, Social Media Posting, Event Running.
Internal template groups map into these.
"""

# Display order and label for the 4 task types
TASK_TYPE_OPTIONS = [
    ("online_store", "Online Store Tasks"),
    ("asset_creation", "Asset Creation"),
    ("social_media", "Social Media Posting"),
    ("event_running", "Event Running"),
]

# Map task_type key -> single group for new templates/custom tasks
TASK_TYPE_TO_GROUP = {
    "online_store": "online_setup",
    "asset_creation": "assets",
    "social_media": "social_1_week",
    "event_running": "event_prep",
}

# Map internal group (from TaskTemplate.group / EventTask.group) -> task_type key
GROUP_TO_TYPE = {
    "online_setup": "online_store",
    "assets": "asset_creation",
    "social_1_month": "social_media",
    "social_2_weeks": "social_media",
    "social_1_week": "social_media",
    "social_night_before": "social_media",
    "event_prep": "event_running",
    "event_run": "event_running",
    "post_event": "event_running",
}


def get_task_type(group: str | None) -> str:
    """Return task_type key for a given group. Unknown groups map to event_running."""
    if not group:
        return "event_running"
    return GROUP_TO_TYPE.get(group, "event_running")


def get_task_type_label(task_type_key: str) -> str:
    for key, label in TASK_TYPE_OPTIONS:
        if key == task_type_key:
            return label
    return task_type_key

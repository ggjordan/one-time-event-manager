"""
Import events from the Google Sheet "Test Copy One Time Events Checklist".
Run from project root: python -m scripts.import_sheet_events [path/to/sheet.csv]

If you pass a CSV path (export from the sheet), task columns are read: any cell with
initials (e.g. RG, Zach) or a date is treated as "complete on time" for that task.

Sheet columns: A=Title, B=Assigned Event, C=Date, D=Date Range/Game, E=Game. F onward = task columns.
"""
from datetime import datetime
import csv
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Column index (after 0=Title,1=Assigned,2=Date,3=DateRange,4=Game) -> task template name. None = skip.
SHEET_TASK_COLUMN_TEMPLATES = [
    None,
    "Online: Ticket / registration setup",
    None,
    "Online: Event page on site",
    "Online: Front page banner",
    "Social: 1 month out – Discord post",
    "Social: 1 month out – Facebook post",
    None,
    "Social: 2 weeks out – Discord post",
    "Social: 2 weeks out – Facebook post",
    None,
    "Social: 1 week out – Discord post",
    "Social: 1 week out – Facebook post",
    None,
    "Event prep: Set aside space",
    "Run event",
    "Post-event: Get pictures",
    "Post-event: Record attendance",
    "Post-event: Archive event listing",
]

# Rows from the sheet: (title, assigned_event, date_str, date_range_or_game, game_or_planning)
# Optional 6th element: list of task cell values (length len(SHEET_TASK_COLUMN_TEMPLATES)) for completion.
SHEET_ROWS = [
    ("Compendium of Rathe Silver Age Introduction", "Jordan", "02/17", "FaB", "Reed"),
    ("Lorcana Iconic 1k", "Zach", "2/21", "Lorcana", "Zach"),
    ("TMNT Prerelease - Friday 3 pm", "Reed / Brock", "02/27", "MtG", "Jordan"),
    ("TMNT Prerelease - Friday 7 pm", "Reed / Brock", "02/27", "MtG", "Jordan"),
    ("TMNT Prerelease - Saturday 7 pm 2 Headed Giant", "Reed / Brock", "02/28", "MtG", "Jordan"),
    ("TMNT Prerelease - Saturday 3 pm", "Reed / Brock", "02/28", "MtG", "Jordan"),
    ("TMNT Prerelease - Saturday 11 am", "Reed / Brock", "02/28", "MtG", "Jordan"),
    ("TMNT Prerelease - Sunday 3 pm", "Reed / Brock", "03/01", "MtG", "Jordan"),
    ("TMNT Prerelease - Sunday 11 am", "Reed / Brock", "03/01", "MtG", "Jordan"),
    ("Heroines Battle (Heroines Leader Limited)", "Brock", "3/2", "One Piece", "Brock"),
    ("TMNT RCQ", "Reed / Brock", "03/07", "MtG", "Reed"),
    ("A Lawless Time Saturday Prerelease", "Abi", "03/07", "SWU", "Reed"),
    ("A Lawless Time Twin Suns Prerelease", "Abi", "03/09", "SWU", "Reed"),
    ("History of Draft: Battle for Zendikar + Oath of the Gatewatch", "Joseph", "3/14", "MtG", "Joseph"),
    ("FaB Pro Quest Las Vegas", "Jordan", "03/14", "FaB", "Jordan"),
    ("March Summoner's Skirmish", "Joseph", "03/14", "Riftbound", "Joseph"),
    ("Heroines Battle (Heroines Leader Limited)", "Brock", "3/16", "One Piece", "Brock"),
    ("One Piece Treasure Cup", "Brock", "3/17", "One Piece", "Brock"),
    ("History of Draft: Conspiracy", "Joseph", "03/21", "MtG", "Joseph"),
    ("Alpine Gaming Con", "Lindy/Joseph", "03/21", "Other", "Zach"),
    ("History of Draft: Kaladesh", "Joseph", "03/28", "MtG", "Joseph"),
    ("Warhound (GT)?", "Reed", "03/29", "03/28-03/29", "Warhammer"),
    ("Gundam ST09 Release Event", "Arrow", "03/29", "Gundam", "Arrow"),
    ("OP-15 Release Event", "Brock", "3/29", "One Piece", "Brock"),
    ("OP-15 Release Event", "Brock", "3/30", "One Piece", "Brock"),
    ("Paintstravaganza: Fantasy", "Reed", "03/31", "02/01-03/31", "Other"),
    ("History of Draft: Kaladesh + Aether Revolt", "Joseph", "04/04", "MtG", "Joseph"),
    ("April Summoner's Skirmish", "Joseph", "04/04", "Riftbound", "Joseph"),
    ("TMNT Commander Party", "Baker (02/24)", "04/04", "MtG", "Reed (02/24)"),
    ("Gundam Newtype Challenge 2026 Mission 2", "Arrow", "04/11", "Gundam", "Zach"),
    ("Gundam Starter Deck Battle [ST01-06]", "Arrow", "04/19", "Gundam", "Reed"),
    ("Unleashed Pre Release Saturday x2", "Joseph", "05/01", "Riftbound", "Joseph"),
    ("Unleashed Pre Release Sunday x2", "Joseph", "05/02", "Riftbound", "Joseph"),
    ("Riftbound May Skirmish", "Joseph", "05/30", "Riftbound", "Joseph"),
    ("OP-16 Release Event", "Brock", "6/7", "One Piece", "Brock"),
    ("OP-16 Release Event", "Brock", "6/8", "One Piece", "Brock"),
    ("Gundam ST10/EB01 Battle Royale Release Event", "Arrow", "06/28", "Gundam", "Reed"),
    ("Riftbound July Skirmish", "Joseph", "07/11", "Riftbound", "Joseph"),
    ("Gundam GD05/SC01 Release Event 1", "Arrow", "07/26", "Gundam", "Reed"),
    ("Gundam GD05/SC01 Release Event 2", "Arrow", "07/28", "Gundam", "Reed"),
    ("Winterspell Set Champs", "Zach", "02/20 Due Date", "April 4-5, April 11-12, April 18-19, April 25-26", "Lorcana"),
    ("Gundam GD04 Release Event", "Arrow", "4/26", "Gundam", ""),
    ("Gundam Store Champs season 1", "Arrow", "TBD", "05/??", "Gundam"),
    ("Magic Presents: It's Turtle Time (Special Draft)", "Reed", "03/17-04-16", "MtG", ""),
    ("Strixhaven Prerelease", "Reed", "04/17-04/19?", "MtG", "Jordan"),
]

GAME_MAP = {
    "fab": "Flesh and Blood",
    "mtg": "Magic",
    "lorcana": "Lorcana",
    "one piece": "One Piece",
    "gundam": "Gundam",
    "riftbound": "Riftbound",
    "swu": "Star Wars",
    "warhammer": "Warhammer",
    "other": "Other",
}
EXTRA_GAMES = ["Warhammer", "Other"]


def _normalize_game_cell(cell):
    if not cell or not str(cell).strip():
        return None
    s = str(cell).strip().lower()
    if re.match(r"^\d{1,2}/\d{1,2}", s) or "due date" in s or "tbd" in s or "??" in s or "april" in s or "may" in s:
        return None
    return s


def _resolve_game(date_range_or_game, game_or_planning):
    d = _normalize_game_cell(date_range_or_game)
    e = _normalize_game_cell(game_or_planning)
    for raw, canonical in GAME_MAP.items():
        if d and raw in d:
            return canonical
        if e and raw in e:
            return canonical
    if d and len(d) <= 20 and not re.match(r"^\d", d):
        return "Other"
    if e and len(e) <= 20 and not re.match(r"^\d", e) and e not in (
        "reed", "zach", "jordan", "brock", "abi", "joseph", "arrow", "baker", "lindy", "rg", "kl", "n/a"
    ):
        return "Other"
    return "Other"


def _parse_date(date_str, default_year=2025):
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip().lower()
    if "tbd" in s or "??" in s:
        return None
    # Allow "02/20 Due Date" by taking first MM/DD
    m = re.search(r"(\d{1,2})/(\d{1,2})", s)
    if not m:
        return None
    try:
        month, day = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return datetime(default_year, month, day, 18, 0, 0)
    except (ValueError, TypeError):
        pass
    return None


def _owner_to_user_name(assigned_event):
    if not assigned_event or not str(assigned_event).strip():
        return None
    s = str(assigned_event).strip()
    for sep in (" / ", "/", " ("):
        if sep in s:
            s = s.split(sep)[0].strip()
            break
    return s or None


def _cell_looks_complete(cell, default_year=2025):
    """If cell has initials (2-5 letters) or a date, return True (on time) or datetime. Else None."""
    if not cell or not str(cell).strip():
        return None
    s = str(cell).strip()
    if s.upper() in ("N/A", "NA", ""):
        return None
    # Initials: mostly letters, length 2-5
    if re.match(r"^[A-Za-z]{2,5}$", s):
        return True
    # Date M/D or MM/DD
    m = re.search(r"(\d{1,2})/(\d{1,2})", s)
    if m:
        try:
            month, day = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(default_year, month, day, 18, 0, 0)
        except (ValueError, TypeError):
            pass
    # Name (e.g. "Jordan", "Reed") - treat as complete on time
    if re.match(r"^[A-Za-z\s]{2,20}$", s):
        return True
    return None


def _build_task_completion_map(task_cells, default_year=2025):
    """Build dict template_name -> True | datetime from list of cell values (starting at column 5)."""
    out = {}
    for i, template_name in enumerate(SHEET_TASK_COLUMN_TEMPLATES):
        if not template_name:
            continue
        if i >= len(task_cells):
            break
        val = _cell_looks_complete(task_cells[i], default_year)
        if val is not None:
            out[template_name] = val
    return out


def _read_csv_rows(path):
    """Read CSV and yield (title, assigned_event, date_str, col_d, col_e, task_cells_list)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return
    for row in rows[1:]:  # skip header
        if len(row) < 5:
            continue
        title, assigned, date_str = row[0].strip(), row[1].strip(), row[2].strip()
        col_d, col_e = row[3].strip() if len(row) > 3 else "", row[4].strip() if len(row) > 4 else ""
        task_cells = []
        for i in range(len(SHEET_TASK_COLUMN_TEMPLATES)):
            idx = 5 + i
            task_cells.append(row[idx].strip() if len(row) > idx else "")
        yield title, assigned, date_str, col_d, col_e, task_cells


def run():
    from app import create_app, db
    from app.models import Event, Game, User
    from app.services.tasks import generate_tasks_for_event

    app = create_app()
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    use_csv = csv_path and os.path.isfile(csv_path)

    with app.app_context():
        for name in EXTRA_GAMES:
            if Game.query.filter_by(name=name).first() is None:
                db.session.add(Game(name=name))
        db.session.commit()

        def get_game(name):
            return Game.query.filter_by(name=name).first() if name else None

        def get_owner_user(assigned_event):
            name = _owner_to_user_name(assigned_event)
            if not name:
                return None
            u = User.query.filter(
                db.func.lower(User.name).startswith(name.lower())
                | (db.func.lower(User.name) == name.lower())
            ).first()
            if u:
                return u
            return User.query.filter(db.func.lower(User.name).contains(name.lower())).first()

        created = []
        skipped_no_game = []
        no_owner_match = []
        skipped_no_date = []

        if use_csv:
            rows = list(_read_csv_rows(csv_path))
        else:
            rows = [(r[0], r[1], r[2], r[3], r[4], []) for r in SHEET_ROWS]

        for row in rows:
            if use_csv:
                title, assigned_event, date_str, col_d, col_e, task_cells = row
            else:
                title, assigned_event, date_str, col_d, col_e = row[0], row[1], row[2], row[3], row[4]
                task_cells = []

            if not title or not str(title).strip():
                continue
            title = str(title).strip()[:255]
            game_name = _resolve_game(col_d, col_e)
            game = get_game(game_name)
            if not game:
                skipped_no_game.append((title, game_name))
                continue
            owner = get_owner_user(assigned_event)
            if not owner:
                no_owner_match.append((title, assigned_event))
                continue
            dt = _parse_date(date_str)
            if not dt:
                skipped_no_date.append((title, date_str))
                continue
            if Event.query.filter_by(title=title, event_datetime=dt).first():
                continue
            task_completion_map = _build_task_completion_map(task_cells, default_year=dt.year) if task_cells else None
            event = Event(
                title=title,
                owner_id=owner.id,
                game_id=game.id,
                event_datetime=dt,
            )
            db.session.add(event)
            db.session.flush()
            generate_tasks_for_event(event, task_completion_map=task_completion_map)
            created.append((title, dt.strftime("%Y-%m-%d"), owner.name, game.name))

        db.session.commit()

        if use_csv:
            print("Read", len(rows), "rows from CSV.")
        print("Imported", len(created), "events.")
        for t, d, o, g in created:
            print("  ", d, t[:50], "|", o, "|", g)
        if no_owner_match:
            print("\nNo matching user (owner) for these events (not imported):")
            for t, a in no_owner_match:
                print("  ", t[:50], "| Assigned in sheet:", a)
        if skipped_no_date:
            print("\nSkipped (no parseable date):")
            for t, d in skipped_no_date:
                print("  ", t[:50], "| Date:", d)
        if skipped_no_game:
            print("\nSkipped (game not found):")
            for t, g in skipped_no_game:
                print("  ", t[:50], "| Game:", g)
        return created, no_owner_match, skipped_no_date, skipped_no_game


if __name__ == "__main__":
    run()

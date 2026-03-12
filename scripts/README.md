# Import events from Google Sheet

The spreadsheet [Test Copy One Time Events Checklist](https://docs.google.com/spreadsheets/d/1ehidN2O65MJKFHwp-BKu-buFzoPhBGSDhjFH8bTyV8U/edit?gid=0#gid=0) is used as the source.

## Run the import

From the project root:

```bash
python3 -m scripts.import_sheet_events
```

Optional: pass a **CSV export** of the sheet to mark tasks complete when the sheet has initials or a date in the task column:

```bash
python3 -m scripts.import_sheet_events path/to/sheet.csv
```

- **Task due dates** use the correct date (past or future) from each template’s “days before event”; they are no longer set to today.
- When using a CSV: any task column cell with **initials** (e.g. RG, Zach) or a **date** (M/D or MM/DD) is treated as “complete on time” for that task.

(or `python -m scripts.import_sheet_events` if `python` points to Python 3.)

- Creates **Events** with title, date, owner, and game.
- Generates **tasks** for each event from your task templates (same as “Create Event” in the app).
- Adds games **Warhammer** and **Other** if they don’t exist.
- Skips rows with no parseable date (e.g. `TBD`, `05/??`).
- Skips rows whose **Assigned Event** (owner) doesn’t match any **Team** user.

## If events are missing (no matching user)

The script matches the sheet’s “Assigned Event” column to **Team** members by name (case‑insensitive, first word of “Reed / Brock” → Reed).

If you see “No matching user (owner) for these events”, add the missing people under **Team** (same names as in the sheet, e.g. Reed, Brock, Joseph, Abi, Arrow, Baker, Lindy), then run the import again. Already-imported events are skipped (same title + date), so re-running is safe.

## What didn’t match (summary)

- **Owner (Assigned Event):** Only users that exist in **Team** are used. Add Reed, Brock, Joseph, Abi, Arrow, Baker, Lindy (or the exact names you use) so those events import.
- **Date:** Rows with `TBD` or `05/??` are skipped (no date). “02/20 Due Date” is parsed as 2025-02-20.
- **Game:** FaB → Flesh and Blood, MtG → Magic, SWU → Star Wars. Unknown values fall back to **Other** (created if missing).

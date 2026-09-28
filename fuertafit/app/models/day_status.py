"""Estados especiales de un día: 'skipped' (saltado), 'moved' (su rutina se movió), 'away' (vacaciones/fuera)."""
from datetime import date, timedelta

from app.models.db import connect


def days_between(start, end):
    d, last = date.fromisoformat(start), date.fromisoformat(end)
    while d <= last:
        yield d.isoformat()
        d += timedelta(1)


def get_status(start, end):
    with connect() as conn:
        rows = conn.execute("SELECT day, status, note FROM day_status WHERE day BETWEEN ? AND ?",
                            (start, end)).fetchall()
    return {day: {"status": st, "note": note} for day, st, note in rows}


def set_status(start, end, status, note=None):
    with connect() as conn:
        conn.executemany("INSERT OR REPLACE INTO day_status (day, status, note) VALUES (?, ?, ?)",
                         [(d, status, note) for d in days_between(start, end)])


def clear_status(start, end):
    with connect() as conn:
        conn.execute("DELETE FROM day_status WHERE day BETWEEN ? AND ?", (start, end))


def clear_away(start, end):
    with connect() as conn:
        conn.execute("DELETE FROM day_status WHERE status = 'away' AND day BETWEEN ? AND ?", (start, end))


def away_days(since):
    """[(día, motivo)] marcados como fuera desde `since`, en orden."""
    with connect() as conn:
        return conn.execute("SELECT day, note FROM day_status WHERE status = 'away' AND day >= ? ORDER BY day",
                            (since,)).fetchall()

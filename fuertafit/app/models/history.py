"""Rutinas marcadas como hechas."""
from datetime import date, timedelta

from app.models.db import connect


def recent_history(days):
    since = (date.today() - timedelta(days=days)).isoformat()
    with connect() as conn:
        return conn.execute(
            "SELECT post_id, done_on FROM history WHERE done_on >= ? ORDER BY done_on DESC", (since,)
        ).fetchall()


def history_between(start, end):
    with connect() as conn:
        return conn.execute(
            "SELECT post_id, done_on FROM history WHERE done_on BETWEEN ? AND ? ORDER BY done_on DESC",
            (start, end),
        ).fetchall()


def mark_done(post_ids, day=None):
    day = day or date.today().isoformat()
    with connect() as conn:
        # Una misma rutina solo cuenta una vez por día.
        conn.executemany(
            "INSERT INTO history (post_id, done_on) VALUES (?, ?) ON CONFLICT DO NOTHING",
            [(int(pid), day) for pid in post_ids],
        )


def unmark_done(post_ids, day=None):
    day = day or date.today().isoformat()
    with connect() as conn:
        conn.executemany("DELETE FROM history WHERE post_id = ? AND done_on = ?",
                         [(int(pid), day) for pid in post_ids])

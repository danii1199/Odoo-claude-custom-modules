"""Rutinas planificadas por día (calendario)."""
from app.models import catalog
from app.models.db import connect


def get_plans(start, end):
    """{día: {"note": str, "source": str, "postIds": [...]}} entre dos fechas (incluidas)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT day, post_id, note, source FROM plan WHERE day BETWEEN ? AND ? ORDER BY day, position",
            (start, end),
        ).fetchall()
    plans = {}
    for day, pid, note, source in rows:
        p = plans.setdefault(day, {"note": note, "source": source, "postIds": []})
        p["postIds"].append(pid)
    return plans


def save_plan(day, post_ids, note=None, source="manual"):
    ids = [int(pid) for pid in post_ids if int(pid) in catalog.BY_ID]
    with connect() as conn:
        conn.execute("DELETE FROM plan WHERE day = ?", (day,))
        conn.executemany(
            "INSERT INTO plan (day, position, post_id, note, source) VALUES (?, ?, ?, ?, ?)",
            [(day, i, pid, note, source) for i, pid in enumerate(ids)],
        )
    return ids


def delete_plan(day):
    delete_range(day, day)


def delete_range(start, end):
    with connect() as conn:
        conn.execute("DELETE FROM plan WHERE day BETWEEN ? AND ?", (start, end))

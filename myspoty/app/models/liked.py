"""Copia local de "Tus me gusta" (la sincronización horaria la reescribe entera)."""
from app.context import uid
from app.models.db import connect
from app.models.library import track_row_to_dict, upsert_track


def replace_all(items):
    """items: [(track, added_at)] con todas tus canciones guardadas."""
    with connect() as conn:
        for track, _ in items:
            upsert_track(conn, track)
        conn.execute("DELETE FROM liked WHERE user_id = ?", (uid(),))
        conn.executemany("INSERT INTO liked (user_id, track_id, added_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                         [(uid(), t["id"], added) for t, added in items])


def tracks(since=None):
    """Tus me gusta (más recientes primero), opcionalmente solo los guardados desde `since` (ISO)."""
    sql = ("SELECT t.id, t.uri, t.name, t.artists, t.album, t.image, t.duration_ms, l.added_at FROM liked l"
           " JOIN tracks t ON t.id = l.track_id WHERE l.user_id = ?")
    args = (uid(),)
    if since:
        sql += " AND l.added_at >= ?"
        args = (uid(), since)
    with connect() as conn:
        rows = conn.execute(sql + " ORDER BY l.added_at DESC", args).fetchall()
    return [{**track_row_to_dict(r[:7]), "addedAt": r[7]} for r in rows]


def ids():
    with connect() as conn:
        return {r[0] for r in conn.execute("SELECT track_id FROM liked WHERE user_id = ?", (uid(),))}


def count():
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM liked WHERE user_id = ?", (uid(),)).fetchone()[0]


def newest_id():
    with connect() as conn:
        row = conn.execute("SELECT track_id FROM liked WHERE user_id = ? ORDER BY added_at DESC LIMIT 1", (uid(),)).fetchone()
    return row[0] if row else None

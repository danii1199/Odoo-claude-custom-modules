"""Playlists inteligentes: nombre + reglas (JSON) + id de la playlist de Spotify donde se sincronizan."""
import json
from datetime import datetime

from app.context import uid
from app.models.db import connect


def _row(r):
    return {"id": r[0], "name": r[1], "rules": json.loads(r[2]), "spotifyId": r[3], "syncedAt": r[4]}


def list_all():
    with connect() as conn:
        return [_row(r) for r in conn.execute(
            "SELECT id, name, rules, spotify_id, synced_at FROM smart WHERE user_id = ? ORDER BY lower(name)", (uid(),))]


def get(smart_id):
    with connect() as conn:
        r = conn.execute("SELECT id, name, rules, spotify_id, synced_at FROM smart WHERE id = ? AND user_id = ?",
                         (smart_id, uid())).fetchone()
    return _row(r) if r else None


def save(name, rules, smart_id=None):
    with connect() as conn:
        if smart_id:
            conn.execute("UPDATE smart SET name = ?, rules = ? WHERE id = ? AND user_id = ?", (name, json.dumps(rules), smart_id, uid()))
            return smart_id
        return conn.execute("INSERT INTO smart (user_id, name, rules) VALUES (?, ?, ?) RETURNING id",
                            (uid(), name, json.dumps(rules))).fetchone()[0]


def mark_synced(smart_id, spotify_id):
    with connect() as conn:
        conn.execute("UPDATE smart SET spotify_id = ?, synced_at = ? WHERE id = ? AND user_id = ?",
                     (spotify_id, datetime.now().isoformat(timespec="minutes"), smart_id, uid()))


def delete(smart_id):
    with connect() as conn:
        conn.execute("DELETE FROM smart WHERE id = ? AND user_id = ?", (smart_id, uid()))

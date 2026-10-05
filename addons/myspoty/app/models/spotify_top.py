"""Copia local de tus tops oficiales de Spotify y estado de la última sincronización."""
import json

from app.context import uid
from app.models.db import connect

RANGES = ("short_term", "medium_term", "long_term")  # ~4 semanas, ~6 meses, ~1 año


def save_top(range_, kind, items):
    with connect() as conn:
        conn.execute("INSERT INTO spotify_top (user_id, range, kind, data) VALUES (?, ?, ?, ?)"
                     " ON CONFLICT (user_id, range, kind) DO UPDATE SET data = EXCLUDED.data",
                     (uid(), range_, kind, json.dumps(items, ensure_ascii=False)))


def get_top(range_, kind):
    with connect() as conn:
        row = conn.execute("SELECT data FROM spotify_top WHERE user_id = ? AND range = ? AND kind = ?", (uid(), range_, kind)).fetchone()
    return json.loads(row[0]) if row else []


def set_state(**values):
    with connect() as conn:
        conn.executemany("INSERT INTO sync_state (user_id, key, value) VALUES (?, ?, ?)"
                         " ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value",
                         [(uid(), k, json.dumps(v)) for k, v in values.items()])


def get_state(key, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE user_id = ? AND key = ?", (uid(), key)).fetchone()
    return json.loads(row[0]) if row else default

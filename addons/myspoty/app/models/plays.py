"""Historial real de escucha (sincronizado desde Spotify) y estadísticas sobre él."""
import json
from datetime import datetime, timedelta

from app.context import uid
from app.models.db import connect
from app.models.library import track_row_to_dict, upsert_track


def record_many(items):
    """Guarda escuchas [(track, played_at)] ignorando las que ya estaban. Devuelve cuántas son nuevas."""
    count = lambda conn: conn.execute("SELECT COUNT(*) FROM plays WHERE user_id = ?", (uid(),)).fetchone()[0]
    with connect() as conn:
        before = count(conn)
        for track, played_at in items:
            upsert_track(conn, track)
            conn.execute("INSERT INTO plays (user_id, track_id, played_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                         (uid(), track["id"], played_at))
        return count(conn) - before


def first_play():
    with connect() as conn:
        return conn.execute("SELECT MIN(played_at) FROM plays WHERE user_id = ?", (uid(),)).fetchone()[0]


def stats(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with connect() as conn:
        total, ms = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(t.duration_ms), 0) FROM plays p JOIN tracks t ON t.id = p.track_id"
            " WHERE p.user_id = ? AND p.played_at >= ?", (uid(), since)).fetchone()
        top = conn.execute(
            "SELECT t.id, t.uri, t.name, t.artists, t.album, t.image, t.duration_ms, COUNT(*) AS n"
            " FROM plays p JOIN tracks t ON t.id = p.track_id WHERE p.user_id = ? AND p.played_at >= ?"
            " GROUP BY t.id ORDER BY n DESC, MAX(p.played_at) DESC LIMIT 25", (uid(), since)).fetchall()
        by_hour = conn.execute(
            "SELECT CAST(substr(played_at, 12, 2) AS INTEGER) AS h, COUNT(*) FROM plays"
            " WHERE user_id = ? AND played_at >= ? GROUP BY h", (uid(), since)).fetchall()
        rows = conn.execute(
            "SELECT t.artists, COALESCE(t.duration_ms, 0) FROM plays p JOIN tracks t ON t.id = p.track_id"
            " WHERE p.user_id = ? AND p.played_at >= ?", (uid(), since)).fetchall()
    # Por artista: escuchas y minutos. Una canción con varios artistas cuenta entera para cada uno.
    artists = {}
    for names, ms_track in rows:
        for name in json.loads(names):
            a = artists.setdefault(name, [0, 0])
            a[0] += 1
            a[1] += ms_track
    hours = [0] * 24
    for h, n in by_hour:
        hours[h] = n
    return {
        "days": days,
        "plays": total,
        "minutes": round(ms / 60000),
        "topTracks": [{**track_row_to_dict(r[:7]), "plays": r[7], "minutes": round(r[7] * (r[6] or 0) / 60000)}
                      for r in top],
        "topArtists": [{"name": a, "plays": n, "minutes": round(ms_a / 60000)}
                       for a, (n, ms_a) in sorted(artists.items(), key=lambda kv: -kv[1][1])[:12]],
        "byHour": hours,
    }

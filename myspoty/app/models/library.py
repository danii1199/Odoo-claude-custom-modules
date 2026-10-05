"""Tus datos sobre las canciones: copia mínima de cada una, etiquetas, valoración y notas."""
import json
from datetime import datetime

from app.context import uid
from app.models.db import connect

TRACK_FIELDS = ("id", "uri", "name", "artists", "album", "image", "duration_ms")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def track_row_to_dict(row):
    d = dict(zip(TRACK_FIELDS, row))
    d["artists"] = json.loads(d["artists"])
    return d


def upsert_track(conn, track):
    """Guarda/actualiza la copia de una canción. `track`: {id, uri, name, artists[], album, image, duration_ms}."""
    conn.execute(
        "INSERT INTO tracks (id, uri, name, artists, album, image, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (id) DO UPDATE SET uri = EXCLUDED.uri, name = EXCLUDED.name, artists = EXCLUDED.artists,"
        " album = EXCLUDED.album, image = EXCLUDED.image, duration_ms = EXCLUDED.duration_ms",
        (track["id"], track["uri"], track["name"], json.dumps(track.get("artists") or []),
         track.get("album"), track.get("image"), track.get("duration_ms")),
    )


# ---------- etiquetas ----------

def list_tags():
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.id, t.name, t.color, COUNT(tt.track_id) FROM tags t "
            "LEFT JOIN track_tags tt ON tt.tag_id = t.id WHERE t.user_id = ? GROUP BY t.id ORDER BY lower(t.name)", (uid(),)
        ).fetchall()
    return [{"id": i, "name": n, "color": c, "count": k} for i, n, c, k in rows]


def create_tag(name, color):
    with connect() as conn:
        return conn.execute("INSERT INTO tags (user_id, name, color) VALUES (?, ?, ?) RETURNING id", (uid(), name, color)).fetchone()[0]


def update_tag(tag_id, name, color):
    with connect() as conn:
        conn.execute("UPDATE tags SET name = ?, color = ? WHERE id = ? AND user_id = ?", (name, color, tag_id, uid()))


def delete_tag(tag_id):
    with connect() as conn:
        if conn.execute("DELETE FROM tags WHERE id = ? AND user_id = ? RETURNING id", (tag_id, uid())).fetchone():
            conn.execute("DELETE FROM track_tags WHERE tag_id = ?", (tag_id,))


# ---------- datos por canción ----------

def meta_for(track_ids):
    """{track_id: {"tags": [ids], "rating": n, "note": str}} para las canciones pedidas."""
    out = {tid: {"tags": [], "rating": 0, "note": "", "plays": 0} for tid in track_ids}
    if not track_ids:
        return out
    marks = ",".join("?" * len(track_ids))
    with connect() as conn:
        for tid, tag in conn.execute(f"SELECT tt.track_id, tt.tag_id FROM track_tags tt JOIN tags g ON g.id = tt.tag_id"
                                     f" WHERE g.user_id = ? AND tt.track_id IN ({marks})", [uid(), *track_ids]):
            out[tid]["tags"].append(tag)
        for tid, rating, note in conn.execute(
                f"SELECT track_id, rating, note FROM track_meta WHERE user_id = ? AND track_id IN ({marks})", [uid(), *track_ids]):
            out[tid].update(rating=rating, note=note)
        for tid, n in conn.execute(f"SELECT track_id, COUNT(*) FROM plays WHERE user_id = ? AND track_id IN ({marks})"
                                   f" GROUP BY track_id", [uid(), *track_ids]):
            out[tid]["plays"] = n
    return out


def save_meta(track, tag_ids, rating, note):
    """Sustituye etiquetas, valoración y nota de una canción (y guarda su copia)."""
    with connect() as conn:
        upsert_track(conn, track)
        mine = {r[0] for r in conn.execute("SELECT id FROM tags WHERE user_id = ?", (uid(),))}
        current = {r[0] for r in conn.execute("SELECT tag_id FROM track_tags WHERE track_id = ?", (track["id"],))} & mine
        wanted = set(tag_ids) & mine  # solo tus etiquetas
        conn.executemany("DELETE FROM track_tags WHERE track_id = ? AND tag_id = ?",
                         [(track["id"], t) for t in current - wanted])
        conn.executemany("INSERT INTO track_tags (track_id, tag_id, added_at) VALUES (?, ?, ?)",
                         [(track["id"], t, _now()) for t in wanted - current])
        conn.execute("INSERT INTO track_meta (user_id, track_id, rating, note) VALUES (?, ?, ?, ?)"
                     " ON CONFLICT (user_id, track_id) DO UPDATE SET rating = EXCLUDED.rating, note = EXCLUDED.note",
                     (uid(), track["id"], max(0, min(5, int(rating or 0))), note or ""))


def find_tracks(tags_all=(), tags_any=(), tags_none=(), min_rating=0):
    """Canciones tuyas que cumplen las reglas, con tu valoración y la fecha de tu última etiqueta."""
    mine = "(SELECT tt.track_id, tt.tag_id, tt.added_at FROM track_tags tt JOIN tags g ON g.id = tt.tag_id WHERE g.user_id = ?)"
    user = uid()
    sql = (f"SELECT t.id, t.uri, t.name, t.artists, t.album, t.image, t.duration_ms, COALESCE(m.rating, 0),"
           f" (SELECT MAX(added_at) FROM {mine} x WHERE x.track_id = t.id) FROM tracks t"
           f" LEFT JOIN track_meta m ON m.track_id = t.id AND m.user_id = ? WHERE COALESCE(m.rating, 0) >= ?")
    args = [user, user, int(min_rating or 0)]
    for tag in tags_all:
        sql += f" AND EXISTS (SELECT 1 FROM {mine} x WHERE x.track_id = t.id AND x.tag_id = ?)"
        args += [user, tag]
    if tags_any:
        sql += f" AND EXISTS (SELECT 1 FROM {mine} x WHERE x.track_id = t.id AND x.tag_id IN ({','.join('?' * len(tags_any))}))"
        args += [user, *tags_any]
    if tags_none:
        sql += f" AND NOT EXISTS (SELECT 1 FROM {mine} x WHERE x.track_id = t.id AND x.tag_id IN ({','.join('?' * len(tags_none))}))"
        args += [user, *tags_none]
    if not (tags_all or tags_any or min_rating):
        # Sin reglas positivas no devolvemos todo, solo lo que has etiquetado o valorado.
        sql += f" AND (EXISTS (SELECT 1 FROM {mine} x WHERE x.track_id = t.id) OR COALESCE(m.rating, 0) > 0)"
        args += [user]
    with connect() as conn:
        rows = conn.execute(sql, args).fetchall()
    out = []
    for row in rows:
        d = track_row_to_dict(row[:7])
        d.update(rating=row[7], taggedAt=row[8])
        out.append(d)
    return out

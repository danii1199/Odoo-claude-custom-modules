"""Fuentes de canciones para las playlists inteligentes, a partir de tus datos de Spotify.

Spotify ya no da recomendaciones ni "artistas relacionados" a apps nuevas, así que las fuentes se construyen con
lo que sí da: tus tops, tus me gusta (copia local, ver models/liked), tu historial y la búsqueda (máx. 10 por página).
Cada fuente devuelve canciones en el formato propio: {id, uri, name, artists, album, image, duration_ms, why}.
"""
import random
import re
import time
from datetime import datetime, timedelta

from app.models import library, liked, spotify_top
from app.context import uid
from app.models.db import connect
from app.services.spotify import SpotifyError, api

SOURCES = {
    "top": "Tus más escuchadas",
    "artists": "Más de tus artistas favoritos",
    "collab": "Artistas cercanos",
    "genre": "Por género",
    "liked_recent": "Me gusta recientes",
    "forgotten": "Joyas olvidadas",
    "history": "Tus más repetidas",
    "tags": "Tus etiquetas",
}

_cache = {}  # clave -> (momento, datos): búsquedas 1 h, discografías 24 h (cambian poco)
CACHE_TTL = 3600
DISCO_TTL = 24 * 3600


def _image(images):
    if not images:
        return None
    ordered = sorted(images, key=lambda i: i.get("width") or 0)
    return next((i["url"] for i in ordered if (i.get("width") or 0) >= 300), ordered[-1]["url"])


def _track(t, why):
    return {"id": t["id"], "uri": t["uri"], "name": t["name"], "artists": [a["name"] for a in t.get("artists") or []],
            "album": (t.get("album") or {}).get("name"), "image": _image((t.get("album") or {}).get("images")),
            "duration_ms": t.get("duration_ms"), "why": why}


def _cached(key, fn, ttl=CACHE_TTL):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    value = fn()
    _cache[key] = (time.time(), value)
    return value


def search_tracks(query, pages=3):
    """Búsqueda de canciones con caché (Spotify devuelve 10 como mucho por página)."""
    def load():
        out = []
        for p in range(pages):
            res = api("GET", "/search", {"q": query, "type": "track", "limit": 10, "offset": p * 10}).get("tracks") or {}
            items = [t for t in res.get("items") or [] if t and t.get("id")]
            out += items
            if len(items) < 10 or not res.get("next"):
                break
        return out
    return _cached(("search", query, pages), load)


def _known_ids():
    """Canciones que ya conoces: tus tops (todos los periodos) y tus me gusta."""
    ids = set(liked.ids())
    for r in spotify_top.RANGES:
        ids |= {t["id"] for t in spotify_top.get_top(r, "tracks")}
    return ids


def _by_artist(name, why, only_new, known, per_artist):
    """Canciones de un artista (por búsqueda), solo las que son suyas de verdad."""
    esc = name.replace('"', "")
    found = [t for t in search_tracks(f'artist:"{esc}"') if any(a["name"].lower() == name.lower() for a in t["artists"])]
    if only_new:
        found = [t for t in found if t["id"] not in known]
    random.shuffle(found)
    return [_track(t, why) for t in found[:per_artist]]


# ---------- fuentes ----------

def src_top(r):
    return [{**t, "why": SOURCES["top"]} for t in spotify_top.get_top(r["range"], "tracks")]


def _discography(artist_id, albums=4):
    """Canciones de sus últimos álbumes y sencillos (un álbum por llamada: Spotify no deja pedir varios a la vez)."""
    def load():
        try:
            items = api("GET", f"/artists/{artist_id}/albums", {"include_groups": "album,single", "limit": 10}).get("items") or []
        except SpotifyError as e:
            if e.status != 429:
                raise
            return []  # Spotify la tiene bloqueada: se sigue solo con la búsqueda
        tracks = []
        for al in items[:albums]:
            full = api("GET", f"/albums/{al['id']}")
            for t in (full.get("tracks") or {}).get("items") or []:
                if t.get("id"):
                    tracks.append({**t, "album": {"name": full["name"], "images": full.get("images")}})
        return tracks
    return _cached(("disco", artist_id, albums), load, DISCO_TTL)


def src_artists(r):
    known = _known_ids()
    out = []
    for a in spotify_top.get_top(r["range"], "artists")[:r["artists"]]:
        found = {t["id"]: t for t in _discography(a["id"])}
        name = a["name"].replace('"', "")
        for t in search_tracks(f'artist:"{name}"'):
            if any(x["name"].lower() == a["name"].lower() for x in t["artists"]):
                found.setdefault(t["id"], t)
        pick = [t for t in found.values() if not (r["onlyNew"] and t["id"] in known)]
        random.shuffle(pick)
        out += [_track(t, f"Más de {a['name']}") for t in pick[:8]]
    return out


def src_collab(r):
    """"Relacionados" caseros: quien colabora con tus artistas favoritos en tus canciones y aún no está en tu top."""
    top_names = {a["name"].lower() for rng in spotify_top.RANGES for a in spotify_top.get_top(rng, "artists")}
    pool = [t for rng in spotify_top.RANGES for t in spotify_top.get_top(rng, "tracks")] + liked.tracks()
    count = {}
    for t in pool:
        names = t["artists"]
        if any(n.lower() in top_names for n in names):
            for n in names:
                if n.lower() not in top_names:
                    count[n] = count.get(n, 0) + 1
    known = _known_ids()
    out = []
    for name, _ in sorted(count.items(), key=lambda kv: -kv[1])[:r["artists"]]:
        out += _by_artist(name, f"Cerca de tus favoritos: {name}", r["onlyNew"], known, per_artist=5)
    return out


def src_genre(r):
    genres = [g.strip() for g in re.split(r"[,;]", r["genres"]) if g.strip()]
    known = _known_ids() if r["onlyNew"] else set()
    out = []
    for g in genres[:5]:
        esc = g.replace('"', "")
        found = [t for t in search_tracks(f'genre:"{esc}"', pages=5) if t["id"] not in known]
        out += [_track(t, f"Género: {g}") for t in found]
    return out


def src_liked_recent(r):
    since = (datetime.now() - timedelta(days=r["days"])).isoformat(timespec="seconds")
    return [{**t, "why": SOURCES["liked_recent"]} for t in liked.tracks(since)]


def src_forgotten(r):
    tops = {t["id"] for rng in spotify_top.RANGES for t in spotify_top.get_top(rng, "tracks")}
    with connect() as conn:
        heard = {row[0] for row in conn.execute("SELECT DISTINCT track_id FROM plays WHERE user_id = ?", (uid(),))}
    return [{**t, "why": SOURCES["forgotten"]} for t in liked.tracks() if t["id"] not in tops and t["id"] not in heard]


def src_history(r):
    since = (datetime.now() - timedelta(days=r["days"])).isoformat(timespec="seconds")
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.id, t.uri, t.name, t.artists, t.album, t.image, t.duration_ms, COUNT(*) AS n FROM plays p"
            " JOIN tracks t ON t.id = p.track_id WHERE p.user_id = ? AND p.played_at >= ? GROUP BY t.id ORDER BY n DESC",
            (uid(), since)).fetchall()
    return [{**library.track_row_to_dict(row[:7]), "why": f"{SOURCES['history']} ({row[7]}×)"} for row in rows]


def src_tags(r):
    tracks = library.find_tracks(r["tagsAll"], r["tagsAny"], r["tagsNone"], r["minRating"])
    return [{**t, "why": SOURCES["tags"]} for t in tracks]


FUNCS = {"top": src_top, "artists": src_artists, "collab": src_collab, "genre": src_genre,
         "liked_recent": src_liked_recent, "forgotten": src_forgotten, "history": src_history, "tags": src_tags}


def build(rules):
    """Junta las fuentes elegidas alternándolas (una de cada por turno), sin repetir canciones."""
    lists = []
    for name in rules["sources"]:
        items = FUNCS[name](rules)
        if rules["order"] in ("mix", "random") and name not in ("top", "history"):
            random.shuffle(items)  # las listas ordenadas (tops, repetidas) conservan su orden en la mezcla
        lists.append(items)
    out, seen = [], set()
    for k in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if k < len(l) and l[k]["id"] not in seen:
                seen.add(l[k]["id"])
                out.append(l[k])
    if rules["order"] == "random":
        random.shuffle(out)
    elif rules["order"] == "name":
        out.sort(key=lambda t: t["name"].lower())
    return out[:rules["limit"]]

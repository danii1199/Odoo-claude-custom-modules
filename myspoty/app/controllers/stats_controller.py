"""Estadísticas: tops oficiales de Spotify e historial real sincronizado cada hora."""
from app.models import plays, spotify_top
from app.router import HttpError, route
from app.services import sync
from app.services.spotify import SpotifyError


@route("GET", "/api/stats")
def history(req):
    return {**plays.stats(max(1, min(365, req.get_int("days", 30)))),
            "since": plays.first_play(), "lastSync": spotify_top.get_state("last_sync")}


@route("GET", "/api/stats/top")
def top(req):
    range_ = req.get("range", "short_term")
    if range_ not in spotify_top.RANGES:
        raise HttpError(400, "Periodo no válido")
    artists = spotify_top.get_top(range_, "artists")
    genres = {}
    for pos, a in enumerate(artists):  # un género pesa más cuanto más arriba está el artista
        for g in a["genres"]:
            genres[g] = genres.get(g, 0) + (len(artists) - pos)
    return {"tracks": spotify_top.get_top(range_, "tracks"), "artists": artists,
            "genres": [g for g, _ in sorted(genres.items(), key=lambda kv: -kv[1])[:14]],
            "lastSync": spotify_top.get_state("last_sync")}


@route("POST", "/api/stats/sync")
def sync_now(req):
    try:
        res = sync.sync()
    except SpotifyError as e:
        raise HttpError(e.status if e.status >= 400 else 502, str(e))
    if res is None:
        raise HttpError(401, "No has iniciado sesión en Spotify.")
    return res

"""Letra de la canción que suena (para la pantalla completa)."""
import urllib.error

from app.router import HttpError, route
from app.services import lyrics


@route("GET", "/api/lyrics")
def get(req):
    track_id, name, artist = req.get("id"), req.get("name"), req.get("artist")
    if not (track_id and name and artist):
        raise HttpError(400, "Faltan datos de la canción")
    try:
        return lyrics.get(track_id, name, artist, req.get("album"), req.get_int("duration_ms"))
    except (urllib.error.URLError, TimeoutError, OSError):
        raise HttpError(503, "No se ha podido consultar LRCLIB ahora mismo")

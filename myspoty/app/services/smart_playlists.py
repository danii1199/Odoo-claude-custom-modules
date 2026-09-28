"""Playlists inteligentes: fuentes (tops, tus artistas, género, me gusta, historial, etiquetas) -> playlist real en tu Spotify."""
from app.models import auth, smart
from app.services import smart_sources
from app.services.spotify import SpotifyError, api, logged_in

FALLBACK = (400, 403, 404, 405)


def _first(*calls):
    """Spotify está migrando su API (2025): primero la dirección nueva y, si la rechaza, la antigua."""
    last = None
    for method, path, body in calls:
        try:
            return api(method, path, body=body)
        except SpotifyError as e:
            if e.status not in FALLBACK:
                raise
            last = e
    raise last

ORDERS = ("mix", "random", "name")
RANGES = ("short_term", "medium_term", "long_term")


def normalize_rules(rules):
    """Reglas con valores por defecto y límites. Las playlists antiguas (solo etiquetas) siguen funcionando."""
    rules = rules or {}
    ints = lambda k: [int(x) for x in rules.get(k) or []]
    num = lambda k, default, lo, hi: max(lo, min(hi, int(rules.get(k) or default)))
    sources = [s for s in rules.get("sources") or ["tags"] if s in smart_sources.FUNCS] or ["top"]
    return {"sources": sources,
            "range": rules.get("range") if rules.get("range") in RANGES else "short_term",
            "artists": num("artists", 8, 1, 20), "days": num("days", 30, 1, 365),
            "genres": str(rules.get("genres") or "")[:200], "onlyNew": rules.get("onlyNew", True) is not False,
            "tagsAll": ints("tagsAll"), "tagsAny": ints("tagsAny"), "tagsNone": ints("tagsNone"),
            "minRating": num("minRating", 0, 0, 5), "limit": num("limit", 50, 1, 500),
            "order": rules.get("order") if rules.get("order") in ORDERS else "mix",
            "daily": bool(rules.get("daily"))}


def preview(rules):
    return smart_sources.build(normalize_rules(rules))


def sync(smart_id):
    """Crea (la primera vez) o reescribe la playlist de Spotify con las canciones que cumplen las reglas."""
    item = smart.get(smart_id)
    if not item:
        raise SpotifyError(404, "Esa playlist inteligente no existe.")
    if not logged_in():
        raise SpotifyError(401, "Inicia sesión en Spotify para sincronizar.")
    uris = [t["uri"] for t in preview(item["rules"])]
    if not uris:
        raise SpotifyError(400, "Con estas reglas no sale ninguna canción.")
    playlist_id = item["spotifyId"]
    if playlist_id:
        try:
            api("GET", f"/playlists/{playlist_id}", {"fields": "id"})
        except SpotifyError as e:
            if e.status != 404:
                raise
            playlist_id = None  # la borraste en Spotify: se crea otra
    if not playlist_id:
        user = auth.get_user() or {}
        body = {"name": f"⚡ {item['name']}", "public": False,
                "description": "Playlist inteligente de myspoty: se actualiza con tus etiquetas y valoraciones."}
        created = _first(("POST", "/me/playlists", body), ("POST", f"/users/{user['id']}/playlists", body))
        playlist_id = created["id"]
    # PUT sustituye el contenido (máx. 100 por llamada); el resto se añade por tandas.
    _first(("PUT", f"/playlists/{playlist_id}/items", {"uris": uris[:100]}),
           ("PUT", f"/playlists/{playlist_id}/tracks", {"uris": uris[:100]}))
    for i in range(100, len(uris), 100):
        _first(("POST", f"/playlists/{playlist_id}/items", {"uris": uris[i:i + 100]}),
               ("POST", f"/playlists/{playlist_id}/tracks", {"uris": uris[i:i + 100]}))
    smart.mark_synced(smart_id, playlist_id)
    return {"spotifyId": playlist_id, "tracks": len(uris)}


def sync_daily():
    """Las marcadas «actualizar cada día» y ya creadas en Spotify se rehacen si hace más de 24 h."""
    from datetime import datetime, timedelta
    limit = (datetime.now() - timedelta(hours=24)).isoformat(timespec="minutes")
    done = []
    for item in smart.list_all():
        if item["rules"].get("daily") and item["spotifyId"] and (item["syncedAt"] or "") < limit:
            sync(item["id"])
            done.append(item["name"])
    return done

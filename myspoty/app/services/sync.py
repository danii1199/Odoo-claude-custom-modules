"""Sincronización con Spotify (cada hora y al iniciar sesión): historial real reciente y tops oficiales.

Spotify solo da las últimas 50 escuchas, así que guardarlas cada hora (sin duplicar) va acumulando el
historial completo, también lo que escuchas en el móvil u otros dispositivos.
"""
import threading
from datetime import datetime

from app.models import liked, plays, spotify_top
from app.context import current
from app.services.spotify import SpotifyError, api, logged_in

_lock = threading.Lock()


def _image(images, size=300):
    """La imagen más pequeña que llegue a `size` px (o la más grande que haya)."""
    if not images:
        return None
    ordered = sorted(images, key=lambda i: i.get("width") or 0)
    return next((i["url"] for i in ordered if (i.get("width") or 0) >= size), ordered[-1]["url"])


def _track(t):
    return {"id": t["id"], "uri": t["uri"], "name": t["name"], "artists": [a["name"] for a in t.get("artists") or []],
            "album": (t.get("album") or {}).get("name"), "image": _image((t.get("album") or {}).get("images")),
            "duration_ms": t.get("duration_ms")}


def _artist(a):
    return {"id": a["id"], "uri": a["uri"], "name": a["name"], "image": _image(a.get("images")),
            "genres": a.get("genres") or [], "followers": (a.get("followers") or {}).get("total")}


def _local(iso_utc):
    """'2026-09-28T13:40:12.345Z' -> hora local del servidor (Madrid en Docker), sin zona."""
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return dt.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


def sync():
    if not logged_in():
        return None
    with _lock:  # que la hora en punto y un "sincronizar ahora" no se pisen
        recent = api("GET", "/me/player/recently-played", {"limit": 50})
        items = [(_track(it["track"]), _local(it["played_at"])) for it in recent.get("items") or []
                 if it.get("track") and it["track"].get("id")]
        new = plays.record_many(items)
        for range_ in spotify_top.RANGES:
            tracks = api("GET", "/me/top/tracks", {"limit": 50, "time_range": range_})
            artists = api("GET", "/me/top/artists", {"limit": 50, "time_range": range_})
            spotify_top.save_top(range_, "tracks", [_track(t) for t in tracks.get("items") or [] if t.get("id")])
            spotify_top.save_top(range_, "artists", [_artist(a) for a in artists.get("items") or []])
        # Tus me gusta (para las playlists inteligentes): solo se releen enteros si han cambiado.
        first = api("GET", "/me/tracks", {"limit": 50, "offset": 0})
        newest = next((i["track"]["id"] for i in first.get("items") or [] if i.get("track", {}).get("id")), None)
        if first.get("total") != liked.count() or newest != liked.newest_id():
            saved, page, offset = [], first, 0
            while True:
                saved += [(_track(i["track"]), _local(i["added_at"])) for i in page.get("items") or [] if i.get("track", {}).get("id")]
                if not page.get("next") or len(saved) >= 10000:
                    break
                offset += 50
                page = api("GET", "/me/tracks", {"limit": 50, "offset": offset})
            liked.replace_all(saved)
        result = {"at": datetime.now().isoformat(timespec="minutes"), "newPlays": new, "liked": liked.count()}
        spotify_top.set_state(last_sync=result)
        return result


def safe_sync(origin):
    try:
        res = sync()
        if res:
            print(f"[sync:{origin}:{current()}] {res['newPlays']} escuchas nuevas, {res['liked']} me gusta, tops actualizados", flush=True)
            from app.services import smart_playlists  # aquí para no crear una importación circular
            renewed = smart_playlists.sync_daily()
            # Deja en caché la discografía de tus artistas top: la vista previa de "Más de tus artistas" sale al momento.
            from app.services import smart_sources
            for a in spotify_top.get_top("short_term", "artists")[:5]:
                smart_sources._discography(a["id"])
            if renewed:
                print(f"[sync:{origin}] inteligentes renovadas: {', '.join(renewed)}", flush=True)
    except SpotifyError as e:
        print(f"[sync:{origin}] Spotify: {e}", flush=True)
    except Exception as e:  # que un fallo puntual no mate el hilo
        print(f"[sync:{origin}] Error: {e}", flush=True)

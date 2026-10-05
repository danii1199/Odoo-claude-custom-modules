"""Playlists inteligentes: crear, previsualizar y sincronizar con Spotify."""
from app.models import smart
from app.router import HttpError, route
from app.services import smart_playlists
from app.services.spotify import SpotifyError


@route("GET", "/api/smart")
def list_smart(req):
    return smart.list_all()


@route("POST", "/api/smart")
def save_smart(req):
    name = (req.body.get("name") or "").strip()[:60]
    if not name:
        raise HttpError(400, "Ponle un nombre")
    rules = smart_playlists.normalize_rules(req.body.get("rules"))
    return {"id": smart.save(name, rules, req.body.get("id"))}


@route("POST", "/api/smart/delete")
def delete_smart(req):
    smart.delete(int(req.body["id"]))
    return {"ok": True}


@route("POST", "/api/smart/preview")
def preview(req):
    try:
        return smart_playlists.preview(req.body.get("rules"))
    except SpotifyError as e:
        raise HttpError(e.status if e.status >= 400 else 502, str(e))


@route("POST", "/api/smart/sync")
def sync(req):
    try:
        return smart_playlists.sync(int(req.body["id"]))
    except SpotifyError as e:
        raise HttpError(e.status if e.status >= 400 else 502, str(e))

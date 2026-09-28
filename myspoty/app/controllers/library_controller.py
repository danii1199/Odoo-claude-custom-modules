"""Tus datos sobre las canciones: etiquetas, valoraciones y notas."""
import re

from app.models import library
from app.models.db import IntegrityError
from app.router import HttpError, route

COLOR_RX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _track(body):
    t = body.get("track") or {}
    if not isinstance(t.get("id"), str) or not isinstance(t.get("uri"), str) or not t.get("name"):
        raise HttpError(400, "Canción no válida")
    return t


@route("GET", "/api/tags")
def tags(req):
    return library.list_tags()


@route("POST", "/api/tags")
def save_tag(req):
    name = (req.body.get("name") or "").strip()[:40]
    color = req.body.get("color") or "#c6ff3d"
    if not name or not COLOR_RX.match(color):
        raise HttpError(400, "Nombre o color no válido")
    try:
        if req.body.get("id"):
            library.update_tag(int(req.body["id"]), name, color)
            return {"id": int(req.body["id"])}
        return {"id": library.create_tag(name, color)}
    except IntegrityError:
        raise HttpError(409, "Ya tienes una etiqueta con ese nombre")


@route("POST", "/api/tags/delete")
def delete_tag(req):
    library.delete_tag(int(req.body["id"]))
    return {"ok": True}


@route("GET", "/api/tracks/meta")
def meta(req):
    return library.meta_for(req.get_list("ids")[:100])


@route("POST", "/api/tracks/meta")
def save_meta(req):
    b = req.body
    library.save_meta(_track(b), [int(t) for t in b.get("tags") or []], b.get("rating", 0), (b.get("note") or "")[:500])
    return {"ok": True}


@route("GET", "/api/tracks/tagged")
def tagged(req):
    return library.find_tracks(tags_all=[int(t) for t in req.get_list("tags")], min_rating=req.get_int("minRating", 0))

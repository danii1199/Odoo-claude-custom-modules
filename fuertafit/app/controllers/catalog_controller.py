"""Catálogo: metadatos, buscador e importación de rutinas nuevas."""
from app.models import catalog
from app.router import HttpError, route
from app.services import coach
from app.views.serializers import routine


@route("GET", "/api/meta")
def meta(req):
    return {**catalog.meta(), "bot": coach.available(), "model": coach.MODEL}


@route("GET", "/api/routines")
def routines(req):
    res = catalog.search(q=req.get("q"), types=req.get_list("types"), groups=req.get_list("groups"),
                         intensities=req.get_list("intensities"), materials=req.get_list("materials"),
                         min_minutes=req.get_int("min"), max_minutes=req.get_int("max"),
                         offset=req.get_int("offset", 0), limit=req.get_int("limit", 30))
    return {"total": res["total"], "items": [routine(it) for it in res["items"]]}


@route("GET", "/api/catalog/ids")
def ids(req):
    return catalog.catalog_ids()


@route("POST", "/api/catalog/import")
def import_items(req):
    items = req.body.get("items")
    if not isinstance(items, list):
        raise HttpError(400, "Formato no válido")
    res = catalog.import_items(items)
    print(f"[catálogo] +{res['added']} nuevas, {res['updated']} actualizadas", flush=True)
    return res

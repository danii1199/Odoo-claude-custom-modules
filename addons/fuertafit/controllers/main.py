"""Controlador: la web (/fuerta, página del sitio web de Odoo) y su API JSON (/fuerta/api/*). Todo requiere sesión
de Odoo y trabaja con los datos del usuario que ha entrado (el catálogo es común)."""
import json
import logging
from pathlib import Path

from odoo import http
from odoo.http import request

from ..services import calendar, catalog, coach, planner
from ..services.dates import today
from ..services.generator import generate
from . import serializers

_logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).resolve().parent.parent / "static" / "web"
# Odoo cachea los estáticos una semana: la versión (fecha del archivo más nuevo) fuerza a recargarlos tras cambiarlos.
VERSION = str(int(max(p.stat().st_mtime for p in WEB_DIR.rglob("*") if p.is_file())))


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Req:
    """Parámetros de la URL y cuerpo JSON de la petición."""

    def __init__(self, query, body):
        self.query, self.body = query, body

    def get(self, key, default=None):
        return self.query.get(key) or default

    def get_list(self, key):
        """Parámetro separado por comas ("a,b") como lista; None si viene vacío."""
        return [x for x in (self.query.get(key) or "").split(",") if x] or None

    def get_int(self, key, default=None):
        value = self.query.get(key)
        return int(value) if value else default


GROUP = "fuertafit.group_fuerta_user"


def _allowed():
    """Solo quien está en «Mi rutina Fuerta / Usuario» (security/groups.xml) usa la web y la API."""
    return request.env.user.has_group(GROUP)


def _forbidden():
    return request.make_response("No tienes acceso a Mi rutina Fuerta.", status=403,
                                 headers=[("Content-Type", "text/plain; charset=utf-8")])


def _page(name):
    """Página HTML suelta de static/web (sin el layout del sitio web): solo /fuerta/sync, la ventanita del marcador."""
    html = (WEB_DIR / name).read_text(encoding="utf-8").replace("__V__", VERSION)
    return request.make_response(html, [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-cache")])


def _api(handler):
    """Ejecuta `handler(env, req)` y responde en JSON. Los POST solo con Content-Type JSON: un formulario de otra
    web no puede mandarlo sin permiso del navegador (protección CSRF, ya que estas rutas no llevan token)."""
    hr = request.httprequest
    try:
        if not _allowed():
            raise HttpError(403, "No tienes acceso a Mi rutina Fuerta")
        body = {}
        if hr.method == "POST":
            if hr.mimetype != "application/json":
                raise HttpError(415, "Se esperaba JSON")
            try:
                body = json.loads(hr.get_data() or b"{}")
            except ValueError:
                raise HttpError(400, "JSON no válido")
            if not isinstance(body, dict):
                raise HttpError(400, "Formato no válido")
        return request.make_json_response(handler(request.env, Req(request.params, body)))
    except HttpError as e:
        request.env.cr.rollback()  # la respuesta normal confirmaría la transacción
        return request.make_json_response({"error": str(e)}, status=e.status)
    except (KeyError, ValueError, TypeError) as e:  # faltan campos o fechas mal formadas
        request.env.cr.rollback()
        return request.make_json_response({"error": f"Petición no válida: {e}"}, status=400)


def get(path):
    return http.route(path, type="http", auth="user", methods=["GET"])


def post(path):
    return http.route(path, type="http", auth="user", methods=["POST"], csrf=False)


class FuertaWeb(http.Controller):
    # ---------- páginas ----------
    @http.route("/fuerta", type="http", auth="user", methods=["GET"], website=True)
    def index(self, **kw):
        if not _allowed():
            return _forbidden()
        return request.render("fuertafit.app_page", {"v": VERSION})

    @get("/fuerta/sync")
    def sync(self, **kw):
        if not _allowed():
            return _forbidden()
        return _page("sync.html")

    # ---------- catálogo ----------
    @get("/fuerta/api/meta")
    def meta(self, **kw):
        return _api(lambda env, req: {**catalog.meta(catalog.get(env)), "bot": coach.available(),
                                      "model": coach.MODEL, "user": env.user.name, "today": today(env).isoformat()})

    @get("/fuerta/api/routines")
    def routines(self, **kw):
        def handler(env, req):
            res = catalog.search(catalog.get(env), q=req.get("q"), types=req.get_list("types"),
                                 groups=req.get_list("groups"), intensities=req.get_list("intensities"),
                                 materials=req.get_list("materials"), min_minutes=req.get_int("min"),
                                 max_minutes=req.get_int("max"), offset=req.get_int("offset", 0),
                                 limit=req.get_int("limit", 30))
            return {"total": res["total"], "items": [serializers.routine(it) for it in res["items"]]}
        return _api(handler)

    @get("/fuerta/api/catalog/ids")
    def catalog_ids(self, **kw):
        return _api(lambda env, req: env["fuerta.routine"].catalog_ids())

    @post("/fuerta/api/catalog/import")
    def catalog_import(self, **kw):
        def handler(env, req):
            items = req.body.get("items")
            if not isinstance(items, list):
                raise HttpError(400, "Formato no válido")
            res = env["fuerta.routine"].import_items(items)
            _logger.info("[catálogo] %s: +%s nuevas, %s actualizadas", env.user.login, res["added"], res["updated"])
            return res
        return _api(handler)

    # ---------- calendario y generación ----------
    @get("/fuerta/api/plans")
    def plans(self, **kw):
        def handler(env, req):
            start, end = req.get("from"), req.get("to")
            return serializers.calendar(catalog.get(env).by_id, env["fuerta.plan"].get_plans(start, end),
                                        env["fuerta.day.status"].get_status(start, end),
                                        env["fuerta.history"].between(start, end))
        return _api(handler)

    @post("/fuerta/api/generate")
    def generate(self, **kw):
        return _api(lambda env, req: generate(env, req.body))

    @post("/fuerta/api/plan")
    def plan_save(self, **kw):
        def handler(env, req):
            b = req.body
            ids = env["fuerta.plan"].save_plan(b["day"], b.get("postIds", []), b.get("note"), b.get("source", "manual"))
            return {"ok": True, "postIds": ids}
        return _api(handler)

    @post("/fuerta/api/plan/remove")
    def plan_remove(self, **kw):
        return _api(lambda env, req: env["fuerta.plan"].delete_plan(req.body["day"]) or {"ok": True})

    @post("/fuerta/api/plan/week")
    def plan_week(self, **kw):
        return _api(lambda env, req: planner.plan_week(env, req.body.get("start"), bool(req.body.get("overwrite"))))

    @post("/fuerta/api/plan/auto")
    def plan_auto(self, **kw):
        def handler(env, req):
            minutes = int(req.body["minutes"]) if req.body.get("minutes") else None
            return {"postIds": planner.plan_day(env, req.body["day"], minutes)}
        return _api(handler)

    # ---------- días especiales ----------
    @post("/fuerta/api/day/move")
    def day_move(self, **kw):
        def handler(env, req):
            try:
                return {"result": calendar.move_plan(env, req.body["from"], req.body["to"])}
            except ValueError as e:
                raise HttpError(400, str(e))
        return _api(handler)

    @post("/fuerta/api/day/skip")
    def day_skip(self, **kw):
        return _api(lambda env, req: calendar.skip_day(env, req.body["day"], req.body.get("note")) or {"ok": True})

    @post("/fuerta/api/day/clear")
    def day_clear(self, **kw):
        def handler(env, req):
            start = req.body["start"]
            env["fuerta.day.status"].clear_status(start, req.body.get("end") or start)
            return {"ok": True}
        return _api(handler)

    @get("/fuerta/api/away")
    def away_list(self, **kw):
        return _api(lambda env, req: calendar.away_ranges(env, req.get("since") or today(env).isoformat()))

    @post("/fuerta/api/away")
    def away_add(self, **kw):
        def handler(env, req):
            b = req.body
            calendar.set_away(env, b["start"], b["end"], b.get("note"), b.get("removePlans", True))
            return {"ok": True}
        return _api(handler)

    @post("/fuerta/api/away/update")
    def away_update(self, **kw):
        def handler(env, req):
            b = req.body
            calendar.update_away(env, b["oldStart"], b["oldEnd"], b["start"], b["end"], b.get("note"),
                                 b.get("removePlans", True))
            return {"ok": True}
        return _api(handler)

    # ---------- historial ----------
    @get("/fuerta/api/history")
    def history(self, **kw):
        def handler(env, req):
            by_id = catalog.get(env).by_id
            return [serializers.history_entry(by_id, pid, day) for pid, day in env["fuerta.history"].recent(60)]
        return _api(handler)

    @post("/fuerta/api/history")
    def history_mark(self, **kw):
        return _api(lambda env, req: env["fuerta.history"].mark_done(req.body.get("postIds", []),
                                                                     req.body.get("doneOn")) or {"ok": True})

    @post("/fuerta/api/history/remove")
    def history_unmark(self, **kw):
        return _api(lambda env, req: env["fuerta.history"].unmark_done(req.body.get("postIds", []),
                                                                       req.body.get("doneOn")) or {"ok": True})

    # ---------- ajustes y entrenador ----------
    @get("/fuerta/api/settings")
    def settings_get(self, **kw):
        return _api(lambda env, req: env["fuerta.settings"].get_settings())

    @post("/fuerta/api/settings")
    def settings_save(self, **kw):
        return _api(lambda env, req: env["fuerta.settings"].save_settings(req.body))

    @post("/fuerta/api/bot/chat")
    def bot_chat(self, **kw):
        return _api(lambda env, req: coach.chat(env, req.body.get("history", []), req.body.get("message", "")))

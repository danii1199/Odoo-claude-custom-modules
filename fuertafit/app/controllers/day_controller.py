"""Días especiales: mover, saltar, deshacer y vacaciones/ausencias."""
from datetime import date

from app.models import day_status
from app.router import HttpError, route
from app.services import calendar


@route("POST", "/api/day/move")
def move(req):
    try:
        return {"result": calendar.move_plan(req.body["from"], req.body["to"])}
    except ValueError as e:
        raise HttpError(400, str(e))


@route("POST", "/api/day/skip")
def skip(req):
    calendar.skip_day(req.body["day"], req.body.get("note"))
    return {"ok": True}


@route("POST", "/api/day/clear")
def clear(req):
    day_status.clear_status(req.body["start"], req.body.get("end") or req.body["start"])
    return {"ok": True}


@route("GET", "/api/away")
def away_list(req):
    return calendar.away_ranges(req.get("since") or date.today().isoformat())


@route("POST", "/api/away")
def away_add(req):
    b = req.body
    calendar.set_away(b["start"], b["end"], b.get("note"), b.get("removePlans", True))
    return {"ok": True}


@route("POST", "/api/away/update")
def away_update(req):
    b = req.body
    calendar.update_away(b["oldStart"], b["oldEnd"], b["start"], b["end"], b.get("note"), b.get("removePlans", True))
    return {"ok": True}

"""Calendario y generación: ver días, generar rutinas y guardar/borrar planes."""
from app.models import day_status, history, plans
from app.router import route
from app.services import planner
from app.services.generator import generate
from app.views import serializers


@route("GET", "/api/plans")
def calendar(req):
    start, end = req.get("from"), req.get("to")
    return serializers.calendar(plans.get_plans(start, end), day_status.get_status(start, end),
                                history.history_between(start, end))


@route("POST", "/api/generate")
def generate_routine(req):
    return generate(req.body)


@route("POST", "/api/plan")
def save(req):
    b = req.body
    ids = plans.save_plan(b["day"], b.get("postIds", []), b.get("note"), b.get("source", "manual"))
    return {"ok": True, "postIds": ids}


@route("POST", "/api/plan/remove")
def remove(req):
    plans.delete_plan(req.body["day"])
    return {"ok": True}


@route("POST", "/api/plan/week")
def fill_week(req):
    return planner.plan_week(req.body.get("start"), bool(req.body.get("overwrite")))


@route("POST", "/api/plan/auto")
def fill_day(req):
    minutes = int(req.body["minutes"]) if req.body.get("minutes") else None
    return {"postIds": planner.plan_day(req.body["day"], minutes)}

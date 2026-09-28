"""Rutinas hechas: listar, marcar y desmarcar."""
from app.models import history
from app.router import route
from app.views.serializers import history_entry


@route("GET", "/api/history")
def recent(req):
    return [history_entry(pid, day) for pid, day in history.recent_history(60)]


@route("POST", "/api/history")
def mark(req):
    history.mark_done(req.body.get("postIds", []), req.body.get("doneOn"))
    return {"ok": True}


@route("POST", "/api/history/remove")
def unmark(req):
    history.unmark_done(req.body.get("postIds", []), req.body.get("doneOn"))
    return {"ok": True}

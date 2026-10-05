"""Ajustes: duración por defecto, semana tipo, material, etc."""
from app.models import settings
from app.router import route


@route("GET", "/api/settings")
def get(req):
    return settings.get_settings()


@route("POST", "/api/settings")
def save(req):
    return settings.save_settings(req.body)

"""Entrenador con IA (latente: sin ANTHROPIC_API_KEY responde que no está activo)."""
from app.router import route
from app.services import coach


@route("POST", "/api/bot/chat")
def chat(req):
    return coach.chat(req.body.get("history", []), req.body.get("message", ""))

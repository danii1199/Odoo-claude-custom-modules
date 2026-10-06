"""Cuentas: login con Spotify, sesión por cookie, conectar otros dispositivos y token para el reproductor."""
import threading

from app.config import REDIRECT_URIS
from app.context import as_user
from app.models import auth
from app.router import HttpError, Redirect, route
from app.server_cookie import COOKIE, MAX_AGE
from app.services import spotify, sync


def _start_session(req, user_id):
    sid = auth.create_session(user_id, req.headers.get("User-Agent"))
    req.set_cookie(COOKIE, sid, MAX_AGE)


@route("GET", "/login", public=True)
def login(req):
    if not spotify.configured():
        raise HttpError(500, "Falta SPOTIFY_CLIENT_ID en el archivo .env")
    return Redirect(spotify.login_url(req.origin))


@route("GET", "/callback", public=True)
def callback(req):
    if req.get("error"):  # cancelaste el permiso en Spotify
        return Redirect("/?login=cancelado")
    try:
        user_id = spotify.finish_login(req.get("code"), req.get("state"))
    except spotify.SpotifyError as e:
        raise HttpError(e.status if e.status >= 400 else 400, str(e))
    _start_session(req, user_id)

    def first_sync():  # para tener estadísticas y me gusta desde el primer momento
        with as_user(user_id):
            sync.safe_sync("login")
    threading.Thread(target=first_sync, daemon=True).start()
    return Redirect("/")


@route("GET", "/api/status", public=True)
def status(req):
    return {"configured": spotify.configured(), "loggedIn": bool(req.user) and spotify.logged_in(),
            "user": auth.get_user() if req.user else None,
            "redirectUri": spotify.redirect_for(req.origin), "redirectUris": REDIRECT_URIS}


@route("GET", "/api/token")
def token(req):
    """Token de acceso para el Web Playback SDK y las llamadas del navegador a la Web API."""
    try:
        tok = spotify.access_token()
    except spotify.SpotifyError as e:
        raise HttpError(e.status, str(e))
    if not tok:
        raise HttpError(401, "No has iniciado sesión en Spotify.")
    return {"accessToken": tok, "expiresAt": auth.get_tokens()["expires_at"]}


@route("POST", "/api/logout", public=True)
def logout(req):
    """Cierra la sesión de este navegador (los datos y los demás dispositivos no se tocan)."""
    sid = req.cookies.get(COOKIE)
    if sid:
        auth.delete_session(sid)
    req.set_cookie(COOKIE, "", 0)
    return {"ok": True}


@route("POST", "/api/device/code")
def device_code(req):
    """Código de 6 letras (10 min, un solo uso) para entrar desde otro dispositivo sin pasar por Spotify."""
    return {"code": auth.new_device_code(), "minutes": 10}


@route("POST", "/api/device/login", public=True)
def device_login(req):
    user_id = auth.use_device_code(req.body.get("code"))
    if not user_id:
        raise HttpError(400, "Código incorrecto o caducado. Pide otro en el dispositivo donde ya has entrado.")
    _start_session(req, user_id)
    return {"ok": True}


@route("GET", "/api/sessions")
def sessions(req):
    return auth.sessions_of_user()

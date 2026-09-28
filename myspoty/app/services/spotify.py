"""Cliente de Spotify: inicio de sesión OAuth con PKCE, renovación del token y llamadas a la Web API.

Con PKCE no hace falta el client secret: solo el Client ID de tu app del panel de desarrolladores.
Tu contraseña nunca pasa por aquí; inicias sesión en la página oficial de Spotify.
"""
import base64
import hashlib
import re
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from urllib.parse import urlparse

from app.config import CLIENT_ID, REDIRECT_URIS, SCOPES
from app.context import as_user, current
from app.models import auth

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"

_pending = {}  # state -> (code_verifier, redirect_uri) de los logins en curso
_blocked = {}  # tipo de petición ("GET /artists/{id}/albums") -> momento hasta el que Spotify la ha bloqueado


class SpotifyError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def configured():
    return bool(CLIENT_ID)


def logged_in():
    """¿El usuario de esta petición tiene permiso de Spotify guardado?"""
    return bool(current()) and bool(auth.get_tokens())


def redirect_for(origin):
    """La dirección de vuelta registrada que corresponde a la dirección por la que se ha entrado."""
    return next((u for u in REDIRECT_URIS if urlparse(u).netloc == urlparse(origin).netloc), REDIRECT_URIS[0])


# ---------- inicio de sesión ----------

def login_url(origin):
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    redirect = redirect_for(origin)
    _pending[state] = (verifier, redirect)
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": redirect, "scope": SCOPES,
        "state": state, "code_challenge_method": "S256", "code_challenge": challenge,
    })


def finish_login(code, state):
    """Canjea el código, identifica al usuario de Spotify y guarda su permiso. Devuelve su id."""
    verifier, redirect = _pending.pop(state, (None, None))
    if not verifier:
        raise SpotifyError(400, "El inicio de sesión ha caducado. Vuelve a intentarlo.")
    tok = _token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect,
                          "client_id": CLIENT_ID, "code_verifier": verifier})
    req = urllib.request.Request(API_URL + "/me", headers={"Authorization": f"Bearer {tok['access_token']}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            me = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:  # app en modo desarrollo y esta cuenta no está dada de alta en el panel
            raise SpotifyError(403, "Esta cuenta de Spotify no tiene acceso a myspoty todavía: el dueño tiene que "
                                    "añadir su email en el panel de desarrolladores de Spotify (User Management).")
        raise SpotifyError(e.code, "Spotify no ha dejado leer tu perfil.")
    with as_user(me["id"]):
        auth.upsert_user({"id": me["id"], "name": me.get("display_name") or me["id"],
                          "image": (me.get("images") or [{}])[0].get("url"), "product": me.get("product")})
        _store(tok)
    return me["id"]


def _token_request(data):
    req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SpotifyError(e.code, f"Spotify rechazó el token: {e.read().decode()[:200]}")


def _store(tok):
    old = auth.get_tokens() or {}
    # Al renovar, Spotify puede no mandar un refresh token nuevo: se mantiene el anterior.
    auth.save_tokens(tok["access_token"], tok.get("refresh_token") or old.get("refresh_token"),
                     time.time() + tok.get("expires_in", 3600))


def access_token():
    """Token válido del usuario actual (lo renueva si le queda menos de un minuto). None si no hay sesión."""
    if not current():
        return None
    tok = auth.get_tokens()
    if not tok:
        return None
    if tok["expires_at"] - 60 < time.time():
        _store(_token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                               "client_id": CLIENT_ID}))
        tok = auth.get_tokens()
    return tok["access_token"]


# ---------- Web API ----------

def _kind(method, path):
    """"GET /artists/0gwN…/albums" -> "GET /artists/{id}/albums" (los bloqueos de Spotify son por tipo de petición)."""
    return method + " " + re.sub(r"/[A-Za-z0-9]{22}(?=/|$)", "/{id}", path)


def api(method, path, params=None, body=None, _retry=True):
    until = _blocked.get(_kind(method, path), 0)
    if until > time.time():  # bloqueada: ni se intenta, para no alargar el castigo
        raise SpotifyError(429, f"Spotify tiene esta consulta bloqueada durante {round((until - time.time()) / 3600, 1)} h más.")
    token = access_token()
    if not token:
        raise SpotifyError(401, "No has iniciado sesión en Spotify.")
    url = API_URL + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if e.code == 401 and _retry:  # token revocado o caducado antes de tiempo: renovar y reintentar una vez
            auth.expire_token()
            return api(method, path, params, body, _retry=False)
        if e.code == 429:  # demasiadas peticiones: si pide esperar poco, se espera y se reintenta una vez
            wait = int(e.headers.get("Retry-After") or 5)
            if _retry and wait <= 10:
                time.sleep(wait)
                return api(method, path, params, body, _retry=False)
            if wait > 60:
                _blocked[_kind(method, path)] = time.time() + wait
                print(f"[spotify] {_kind(method, path)} bloqueada {round(wait / 3600, 1)} h por exceso de peticiones", flush=True)
            raise SpotifyError(429, f"Spotify pide esperar ({round(wait / 60)} min) por exceso de peticiones.")
        detail = e.read().decode()[:300]
        try:
            detail = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        raise SpotifyError(e.code, f"Spotify: {detail}")

"""Servidor HTTP: sirve el reproductor (views/static) y despacha las rutas registradas por los controladores."""
import html
import json
import traceback
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import app.controllers  # noqa: F401  (registra las rutas)
from app.config import HOST, PORT, STATIC_DIR
from app.context import NotLoggedIn, as_user
from app.models import auth
from app.router import PUBLIC, ROUTES, HttpError, Redirect, Request

from app.server_cookie import COOKIE


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC_DIR), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        for c in getattr(self, "_cookies", None) or []:
            self.send_header("Set-Cookie", c)
        self._cookies = []
        super().end_headers()

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, method):
        url = urlparse(self.path)
        handler = ROUTES.get((method, url.path))
        if not handler:
            return False
        is_api = url.path.startswith("/api/")
        body = {}
        if method == "POST":
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        req = Request(url.query, body, dict(self.headers.items()))
        req.user = auth.user_for_session(req.cookies.get(COOKIE))
        self._cookies = req.set_cookies
        try:
            try:
                if is_api and not req.user and url.path not in PUBLIC:
                    raise HttpError(401, "No has iniciado sesión.")
                with as_user(req.user):  # los modelos leen el usuario de aquí
                    result = handler(req)
            except NotLoggedIn as e:
                raise HttpError(401, str(e))
            except (KeyError, ValueError, TypeError) as e:  # datos que faltan o mal formados en la petición
                raise HttpError(400, f"Petición no válida: {e}")
            except HttpError:
                raise
            except Exception as e:  # cualquier otro fallo: se registra y se responde, sin cortar la conexión
                traceback.print_exc()
                raise HttpError(500, f"Error interno: {e}")
        except HttpError as e:
            if is_api:
                self._send(e.status, json.dumps({"error": str(e)}, ensure_ascii=False).encode(),
                           "application/json; charset=utf-8")
            else:  # login/callback: página de error legible con enlace de vuelta
                page = (f"<!doctype html><meta charset=utf-8><title>myspoty</title>"
                        f"<body style='font:16px system-ui;background:#0b0b10;color:#eee;padding:40px'>"
                        f"<h1>Algo ha fallado</h1><p>{html.escape(str(e))}</p><p><a style='color:#c6ff3d' href='/'>Volver</a></p>")
                self._send(e.status, page.encode(), "text/html; charset=utf-8")
            return True
        if isinstance(result, Redirect):
            self.send_response(302)
            self.send_header("Location", result.location)
            self.end_headers()
        else:
            self._send(200, json.dumps(result, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        return True

    def do_GET(self):
        if self._dispatch("GET"):
            return
        # Direcciones de la web sin "#" (/playlists, /tags…): si no es un archivo, se sirve la página.
        path = urlparse(self.path).path
        if "." not in path.rsplit("/", 1)[-1] and not path.startswith("/api/"):
            self.path = "/index.html"
        super().do_GET()  # archivos estáticos

    def do_POST(self):
        if not self._dispatch("POST"):
            self.send_error(404)

    def log_message(self, fmt, *args):
        # No registrar la query del callback (lleva el código de autorización).
        msg = fmt % args
        if "/callback?" in msg:
            msg = msg.split("/callback?")[0] + "/callback?…" + msg.split('" ', 1)[-1]
        print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def serve():
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

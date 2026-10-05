"""Servidor HTTP: sirve la web estática (views/static) y despacha /api/* a los controladores."""
import json
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import app.controllers  # noqa: F401  (registra las rutas)
from app.config import HOST, PORT, STATIC_DIR
from app.router import ROUTES, HttpError, Request


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC_DIR), **kw)

    def end_headers(self):
        # Que el navegador revalide siempre: así se ven los cambios de la web sin forzar la recarga.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, method):
        url = urlparse(self.path)
        handler = ROUTES.get((method, url.path))
        if not handler:
            return False
        body = {}
        if method == "POST":
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        try:
            self._json(handler(Request(url.query, body)))
        except HttpError as e:
            self._json({"error": str(e)}, e.status)
        return True

    def do_GET(self):
        if not self._dispatch("GET"):
            super().do_GET()  # archivos estáticos

    def do_POST(self):
        if not self._dispatch("POST"):
            self.send_error(404)

    def log_message(self, fmt, *args):
        print(f"[{datetime.now():%H:%M:%S}] {fmt % args}", flush=True)


def serve():
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

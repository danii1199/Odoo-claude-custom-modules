"""Servidor web de "Mi rutina Fuerta".

Uso:  python3 server.py   ->  http://localhost:8000   (o con Docker: docker compose up -d --build)
"""
import json
import os
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import bot
import core

STATIC = Path(__file__).parent / "static"
# En Docker se escucha en 0.0.0.0; en local basta con 127.0.0.1.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))
AUTO_PLAN_EVERY = 30 * 60  # segundos entre comprobaciones del plan semanal automático


def slim(it):
    """Rutina sin la descripción larga, para mandar al navegador."""
    return {k: v for k, v in it.items() if k != "description"}


def plans_payload(start, end):
    plans = core.get_plans(start, end)
    status = core.get_status(start, end)
    done = {}
    for pid, day in core.history_between(start, end):
        done.setdefault(day, []).append(pid)
    out = {}
    for day in sorted(set(plans) | set(done) | set(status)):
        p = plans.get(day, {})
        out[day] = {
            "note": p.get("note"),
            "source": p.get("source"),
            "blocks": [slim(core.BY_ID[i]) for i in p.get("postIds", []) if i in core.BY_ID],
            "done": done.get(day, []),
            "status": status.get(day, {}).get("status"),
            "statusNote": status.get(day, {}).get("note"),
            # Hechas ese día que no estaban en el plan (p. ej. desde "Hoy" o el catálogo).
            "extra": [slim(core.BY_ID[i]) for i in done.get(day, [])
                      if i in core.BY_ID and i not in p.get("postIds", [])],
        }
    return out


def auto_plan_loop():
    """Si el plan automático está activo, rellena los días de entreno de esta semana que estén vacíos."""
    while True:
        try:
            if core.get_settings()["autoPlan"]:
                created = core.plan_week()
                if created:
                    print(f"[auto] Planificados: {', '.join(created)}", flush=True)
        except Exception as e:  # que un fallo puntual no mate el hilo
            print(f"[auto] Error planificando: {e}", flush=True)
        time.sleep(AUTO_PLAN_EVERY)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

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

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        qlist = lambda k: [x for x in q.get(k, "").split(",") if x] or None

        if url.path == "/api/meta":
            return self._json({**core.meta(), "bot": bot.available(), "model": bot.MODEL})
        if url.path == "/api/history":
            return self._json([
                {"postId": pid, "doneOn": d, **(slim(core.BY_ID[pid]) if pid in core.BY_ID else {})}
                for pid, d in core.recent_history(60)
            ])
        if url.path == "/api/plans":
            return self._json(plans_payload(q["from"], q["to"]))
        if url.path == "/api/routines":
            res = core.search(q=q.get("q"), types=qlist("types"), groups=qlist("groups"),
                              intensities=qlist("intensities"),
                              materials=qlist("materials"),
                              min_minutes=int(q["min"]) if q.get("min") else None,
                              max_minutes=int(q["max"]) if q.get("max") else None,
                              offset=int(q.get("offset", 0)), limit=int(q.get("limit", 30)))
            return self._json({"total": res["total"], "items": [slim(it) for it in res["items"]]})
        if url.path == "/api/settings":
            return self._json(core.get_settings())
        if url.path == "/api/catalog/ids":
            return self._json(core.catalog_ids())
        if url.path == "/api/away":
            return self._json(core.away_ranges(q.get("since") or datetime.now().date().isoformat()))
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._body()
        if path == "/api/generate":
            return self._json(core.generate(data))
        if path == "/api/history":
            core.mark_done(data.get("postIds", []), data.get("doneOn"))
            return self._json({"ok": True})
        if path == "/api/history/remove":
            core.unmark_done(data.get("postIds", []), data.get("doneOn"))
            return self._json({"ok": True})
        if path == "/api/plan":
            ids = core.save_plan(data["day"], data.get("postIds", []), data.get("note"), data.get("source", "manual"))
            return self._json({"ok": True, "postIds": ids})
        if path == "/api/plan/week":
            return self._json(core.plan_week(data.get("start"), bool(data.get("overwrite"))))
        if path == "/api/plan/auto":
            minutes = int(data["minutes"]) if data.get("minutes") else None
            return self._json({"postIds": core.plan_day(data["day"], minutes)})
        if path == "/api/catalog/import":
            items = data.get("items")
            if not isinstance(items, list):
                return self._json({"error": "Formato no válido"}, 400)
            res = core.import_items(items)
            print(f"[catálogo] +{res['added']} nuevas, {res['updated']} actualizadas", flush=True)
            return self._json(res)
        if path == "/api/day/move":
            try:
                return self._json({"result": core.move_plan(data["from"], data["to"])})
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
        if path == "/api/day/skip":
            core.skip_day(data["day"], data.get("note"))
            return self._json({"ok": True})
        if path == "/api/day/clear":
            core.clear_status(data["start"], data.get("end") or data["start"])
            return self._json({"ok": True})
        if path == "/api/away/update":
            core.update_away(data["oldStart"], data["oldEnd"], data["start"], data["end"],
                             data.get("note"), data.get("removePlans", True))
            return self._json({"ok": True})
        if path == "/api/away":
            core.set_away(data["start"], data["end"], data.get("note"), data.get("removePlans", True))
            return self._json({"ok": True})
        if path == "/api/plan/remove":
            core.delete_plan(data["day"])
            return self._json({"ok": True})
        if path == "/api/settings":
            return self._json(core.save_settings(data))
        if path == "/api/bot/chat":
            return self._json(bot.chat(data.get("history", []), data.get("message", "")))
        self.send_error(404)

    def log_message(self, fmt, *args):
        print(f"[{datetime.now():%H:%M:%S}] {fmt % args}", flush=True)


if __name__ == "__main__":
    threading.Thread(target=auto_plan_loop, daemon=True).start()
    status = f"entrenador activo ({bot.MODEL})" if bot.available() else "entrenador desactivado (sin API key)"
    print(f"Catálogo: {len(core.CATALOG)} rutinas, {status}  ->  http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

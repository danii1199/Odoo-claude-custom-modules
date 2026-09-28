"""Tarea de fondo: si el plan automático está activo, rellena los días de entreno vacíos de la semana."""
import threading
import time

from app.config import AUTO_PLAN_EVERY
from app.models.settings import get_settings
from app.services.planner import plan_week


def _loop():
    while True:
        try:
            if get_settings()["autoPlan"]:
                created = plan_week()
                if created:
                    print(f"[auto] Planificados: {', '.join(created)}", flush=True)
        except Exception as e:  # que un fallo puntual no mate el hilo
            print(f"[auto] Error planificando: {e}", flush=True)
        time.sleep(AUTO_PLAN_EVERY)


def start():
    threading.Thread(target=_loop, daemon=True).start()

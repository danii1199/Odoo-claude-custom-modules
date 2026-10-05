"""Tarea de fondo: sincroniza con Spotify a cada usuario al arrancar y después cada hora (escalonados)."""
import threading
import time

from app.context import as_user
from app.models import auth
from app.services.sync import safe_sync

EVERY = 60 * 60   # segundos entre rondas
GAP = 20          # segundos entre un usuario y el siguiente (para no saturar el límite de Spotify de la app)


def _loop():
    time.sleep(10)  # deja arrancar el servidor
    while True:
        start = time.time()
        for user_id in auth.users_with_tokens():
            with as_user(user_id):
                safe_sync("cada hora")
            time.sleep(GAP)
        time.sleep(max(60, EVERY - (time.time() - start)))


def start():
    threading.Thread(target=_loop, daemon=True).start()

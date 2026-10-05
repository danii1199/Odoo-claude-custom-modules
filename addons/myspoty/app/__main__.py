"""Arranque: python -m app  ->  http://127.0.0.1:8001   (o con Docker: docker compose up -d --build)

MYSPOTY_NO_SYNC=1 arranca sin la sincronización horaria (para pruebas: no toca Spotify).
"""
import os

from app import scheduler, server
from app.config import PORT
from app.services import spotify

if __name__ == "__main__":
    state = "listo" if spotify.configured() else "falta SPOTIFY_CLIENT_ID en .env"
    print(f"myspoty ({state})  ->  http://127.0.0.1:{PORT}", flush=True)
    if not os.environ.get("MYSPOTY_NO_SYNC"):
        scheduler.start()
    server.serve()

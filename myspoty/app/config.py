"""Configuración leída del entorno (.env en Docker)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# PostgreSQL del contenedor `postgres` (ver ../postgres). En Docker viene del .env del proyecto.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://myspoty@127.0.0.1:5432/myspoty")
STATIC_DIR = Path(__file__).resolve().parent / "views" / "static"

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8001))

# App registrada en https://developer.spotify.com/dashboard (flujo PKCE: no hace falta client secret).
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
# Direcciones de vuelta del login registradas en el panel de Spotify (separadas por comas). Spotify solo acepta
# http con la IP de loopback (no "localhost"); para otros usuarios hace falta una dirección https (Tailscale, dominio…).
# Se usa la que coincide con la dirección por la que se ha entrado; si ninguna coincide, la primera.
REDIRECT_URIS = [u.strip() for u in os.environ.get("SPOTIFY_REDIRECT_URIS", f"http://127.0.0.1:{PORT}/callback").split(",") if u.strip()]
SCOPES = " ".join([
    "streaming", "user-read-email", "user-read-private",                      # Web Playback SDK
    "user-read-playback-state", "user-modify-playback-state", "user-read-currently-playing",
    "playlist-read-private", "playlist-read-collaborative",
    "playlist-modify-private", "playlist-modify-public",
    "user-library-read", "user-library-modify",
    "user-read-recently-played", "user-top-read",
])

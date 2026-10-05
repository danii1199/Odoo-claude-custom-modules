"""Configuración leída del entorno (Docker la define en el Dockerfile)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# PostgreSQL del contenedor `postgres` (ver ../postgres). En Docker viene del .env del proyecto.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://rutinas@127.0.0.1:5432/rutinas")
STATIC_DIR = Path(__file__).resolve().parent / "views" / "static"

# En Docker se escucha en 0.0.0.0; en local basta con 127.0.0.1.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))
AUTO_PLAN_EVERY = 30 * 60  # segundos entre comprobaciones del plan semanal automático

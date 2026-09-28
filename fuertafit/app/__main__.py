"""Arranque: python -m app  ->  http://localhost:8000   (o con Docker: docker compose up -d --build)"""
from app import scheduler, server
from app.config import PORT
from app.models import catalog
from app.services import coach

if __name__ == "__main__":
    scheduler.start()
    status = f"entrenador activo ({coach.MODEL})" if coach.available() else "entrenador desactivado (sin API key)"
    print(f"Catálogo: {len(catalog.CATALOG)} rutinas, {status}  ->  http://localhost:{PORT}", flush=True)
    server.serve()

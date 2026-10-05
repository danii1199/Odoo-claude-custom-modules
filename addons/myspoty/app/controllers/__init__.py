"""Controlador: rutas. Cada módulo registra las suyas con @route al importarse."""
from app.controllers import (  # noqa: F401  (se importan para registrar sus rutas)
    auth_controller, library_controller, lyrics_controller, smart_controller, stats_controller,
)

"""Controlador: rutas /api. Cada módulo registra las suyas con @route al importarse."""
from app.controllers import (  # noqa: F401  (se importan para registrar sus rutas)
    catalog_controller, coach_controller, day_controller, history_controller, plan_controller, settings_controller,
)

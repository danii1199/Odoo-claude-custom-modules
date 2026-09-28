"""Ajustes del usuario (clave -> valor JSON)."""
import json

from app.models.db import connect

DEFAULT_SETTINGS = {
    "autoPlan": False,       # rellenar sola cada semana en el calendario
    # Semana tipo según las guías de la OMS y el ACSM: cada grupo muscular 2 veces por semana con ≥48 h entre
    # sesiones del mismo grupo, cardio 2 días, core 2 días y fin de semana de descanso.
    # 45 min = calentamiento (5-10) + ~25-30 de trabajo + vuelta a la calma/estiramientos (5-10).
    "dailyMinutes": 45,
    # Grupos de cada día de la semana (0 = lunes). Lista vacía = descanso. El primero es el principal del día.
    "week": {"0": ["Pierna y glúteo", "Core"], "1": ["Torso"], "2": ["Cardio"],
             "3": ["Pierna y glúteo", "Core"], "4": ["Torso", "Cardio"], "5": [], "6": []},
    "materials": [],         # material disponible; vacío = cualquiera
    "warmup": True,
    "cooldown": True,
    "preferences": "",       # texto libre para el entrenador con IA (solo si hay API key)
    "catalogUpdated": None,  # última actualización del catálogo desde FuertaFit
}


def get_settings():
    with connect() as conn:
        rows = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    return {k: json.loads(rows[k]) if k in rows else v for k, v in DEFAULT_SETTINGS.items()}


def save_settings(values):
    with connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(k, json.dumps(v)) for k, v in values.items() if k in DEFAULT_SETTINGS],
        )
    return get_settings()

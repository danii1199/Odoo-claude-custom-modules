"""Operaciones del calendario que combinan planes y estados de día: mover, saltar y vacaciones."""
from datetime import date, timedelta

from app.models import day_status, plans

WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _short(day):
    d = date.fromisoformat(day)
    return f"{WEEKDAYS[d.weekday()]} {d.day}/{d.month}"


def move_plan(src, dst):
    """Mueve la rutina de `src` a `dst`. Si `dst` ya tenía rutina, se intercambian."""
    existing = plans.get_plans(min(src, dst), max(src, dst))
    a, b = existing.get(src), existing.get(dst)
    if not a:
        raise ValueError("Ese día no tiene rutina que mover.")
    plans.save_plan(dst, a["postIds"], a["note"], a["source"])
    day_status.clear_status(dst, dst)
    if b:
        plans.save_plan(src, b["postIds"], b["note"], b["source"])
        return "swapped"
    plans.delete_plan(src)
    # Marcado como movido para que el plan automático no vuelva a rellenarlo.
    day_status.set_status(src, src, "moved", f"Movida al {_short(dst)}")
    return "moved"


def skip_day(day, note=None):
    day_status.set_status(day, day, "skipped", note or "Saltado")


def set_away(start, end, note=None, remove_plans=True):
    if end < start:
        start, end = end, start
    if remove_plans:
        plans.delete_range(start, end)
    day_status.set_status(start, end, "away", note or "Fuera")


def update_away(old_start, old_end, start, end, note=None, remove_plans=True):
    """Cambia fechas y/o motivo de una ausencia. Los días que dejan de estar fuera quedan libres
    (sus rutinas, si se quitaron al marcar la ausencia, no vuelven)."""
    day_status.clear_away(old_start, old_end)
    set_away(start, end, note, remove_plans)


def away_ranges(since):
    """Ausencias desde `since`, agrupando días seguidos con el mismo motivo."""
    ranges = []
    for day, note in day_status.away_days(since):
        last = ranges[-1] if ranges else None
        if last and last["note"] == note and date.fromisoformat(day) - date.fromisoformat(last["end"]) == timedelta(1):
            last["end"] = day
        else:
            ranges.append({"start": day, "end": day, "note": note})
    return ranges

"""Plan semanal automático: rellena el calendario según la semana tipo de los ajustes."""
import random
from datetime import date, timedelta

from app.models.day_status import clear_status, get_status
from app.models.plans import get_plans, save_plan
from app.models.settings import get_settings
from app.services.generator import generate


def monday_of(day):
    d = date.fromisoformat(day) if isinstance(day, str) else day
    return d - timedelta(days=d.weekday())


def plan_week(start=None, overwrite=False):
    """Rellena la semana que empieza el lunes `start` según los ajustes del plan semanal.

    Solo toca días de hoy en adelante con grupos asignados; sin `overwrite` respeta los que ya tienen plan.
    Devuelve {día: [ids]} de lo generado.
    """
    s = get_settings()
    monday = monday_of(start or date.today())
    days = [monday + timedelta(i) for i in range(7)]
    existing = get_plans(days[0].isoformat(), days[-1].isoformat())
    blocked = get_status(days[0].isoformat(), days[-1].isoformat())  # saltados, movidos o fuera
    # No repetir rutinas dentro de la misma semana.
    used = {pid for d, p in existing.items() for pid in p["postIds"]
            if not overwrite or date.fromisoformat(d) < date.today()}
    created = {}
    for d in days:
        key = d.isoformat()
        groups = s["week"].get(str(d.weekday())) or []
        if not groups or d < date.today() or key in blocked or (key in existing and not overwrite):
            continue
        ids = _auto_day(key, groups, s, used)
        if ids:
            used.update(ids)
            created[key] = ids
    return created


def plan_day(day, minutes=None):
    """Genera un día suelto con los ajustes del plan semanal (en día de descanso: sin grupo fijo).

    `minutes` sustituye a la duración por defecto solo para este día.
    """
    s = get_settings()
    groups = s["week"].get(str(date.fromisoformat(day).weekday())) or []
    monday = monday_of(day)
    week = get_plans(monday.isoformat(), (monday + timedelta(6)).isoformat())
    used = {pid for d, p in week.items() if d != day for pid in p["postIds"]}
    return _auto_day(day, groups, s, used, minutes)


def _auto_day(day, groups, s, used, minutes=None):
    clear_status(day, day)  # generar a mano un día saltado/movido lo vuelve a activar
    res = generate({"minutes": minutes or s["dailyMinutes"], "groups": groups, "materials": s["materials"] or None,
                    "warmup": s["warmup"], "cooldown": s["cooldown"], "exclude": list(used),
                    "seed": f"{day}-{random.random()}"})
    ids = [b["id"] for b in res["blocks"]]
    if ids:
        save_plan(day, ids, " + ".join(groups) or "Libre", source="auto")
    return ids

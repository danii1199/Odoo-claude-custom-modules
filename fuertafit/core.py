"""Catálogo, historial, planes y generador de rutinas (sin dependencias externas)."""
import json
import os
import random
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
CATALOG_PATH = DATA_DIR / "catalogo.json"
DB_PATH = DATA_DIR / "historial.db"

# Tipos que no cuentan como "bloque principal" salvo que se pidan expresamente.
COOLDOWN_TYPE = "Cuerpo-Mente"
WARMUP_TYPE = "Calentamiento"
SIDE_TYPES = {COOLDOWN_TYPE, WARMUP_TYPE}
# Para la vuelta a la calma preferimos estiramientos/yoga antes que meditación.
COOLDOWN_TITLES = re.compile(r"calma|estira|yoga|movilidad|pilates", re.IGNORECASE)

# Grupo muscular / enfoque de cada rutina, deducido del texto. Gana la primera regla que encaje.
GROUP_RULES = [
    ("Calentamiento", r"calentamiento"),
    ("Cuerpo-Mente", r"yoga|pilates|estira|medita|movilidad|relaja|respira|calma"),
    ("Core", r"abdom|\bcore\b|\babs\b"),
    ("Pierna y glúteo", r"pierna|gl[uú]te|tren inferior|inferior|cu[aá]dri"),
    ("Torso", r"torso|tren superior|superior|brazo|pecho|espalda|hombro|b[ií]ceps|tr[ií]ceps"),
    ("Fullbody", r"full ?body|cuerpo completo|todo el cuerpo|total body|amrap|emom|for time|cross house"),
    ("Cardio", r"hiit|cardio|t[aá]bata|combat|dance|music|energy|reacci|nonstop|intensity|quema|salta"),
]
GROUPS = [g for g, _ in GROUP_RULES]
# Para que calentamiento y estiramiento encajen con la zona del día.
UPPER_RX = re.compile(r"superior|torso|brazo|pecho|espalda|hombro", re.IGNORECASE)
LOWER_RX = re.compile(r"inferior|pierna|gl[uú]te", re.IGNORECASE)
# Rutinas que no son un entrenamiento normal (infantiles, tests, programas de embarazo/posparto):
# no se proponen nunca, pero siguen en el buscador.
SKIP_RX = re.compile(r"fuertakids|test de|embaraz|suelo p[eé]lvico|postparto|posparto|prenatal", re.IGNORECASE)


def _group(it):
    head = " ".join([it["title"], it.get("summary") or "", it.get("methodology") or "", *(it.get("tags") or [])])
    # El título manda: algún resumen de FuertaFit está mal («Tren superior 3» dice «tren inferior»).
    for text in (it["title"], head):
        for name, rx in GROUP_RULES:
            if re.search(rx, text, re.IGNORECASE):
                return name
    # En la descripción larga "calentamiento" o "estiramientos" suelen ser parte de la sesión, no su tema.
    for name, rx in GROUP_RULES[2:]:
        if re.search(rx, it.get("description") or "", re.IGNORECASE):
            return name
    return {"Cardiovascular": "Cardio", "Cuerpo-Mente": "Cuerpo-Mente",
            "Calentamiento": "Calentamiento"}.get(it.get("trainingType"), "Fullbody")


# ---------- catálogo ----------

def _field(desc, label):
    m = re.search(label + r"\s*:\s*(.+?)(?=\s*◽|$)", desc or "", re.IGNORECASE)
    if not m:
        return None
    # Algunas descripciones pegan detrás listas de canciones o ejercicios: nos quedamos con la etiqueta.
    value = re.split(r"[.\[👉🏋]|\s{2,}|CANCIONES", m.group(1))[0].strip()
    return value[:30] or None


def load_catalog():
    if not CATALOG_PATH.exists():
        return []
    items = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for it in items:
        desc = it.get("description", "")
        it["methodology"] = _field(desc, "Metodología")
        it["methodologyDetail"] = _field(desc, "Metodología especifica")
        it["materials"] = it.get("materials") or ["No Material"]
        it["group"] = _group(it)
        it["skip"] = bool(SKIP_RX.search(" ".join([it["title"], it.get("summary") or "", *(it.get("tags") or [])])))
    # Fuera vídeos sin duración y presentaciones de programas (no son entrenamientos).
    return [it for it in items if it.get("durationMinutes")
            and not re.match(r"\s*(presentaci|introducci)", it["title"], re.IGNORECASE)]


CATALOG = load_catalog()
BY_ID = {it["id"]: it for it in CATALOG}

# Campos que se guardan en catalogo.json por rutina (lo demás se calcula al cargar).
RAW_FIELDS = ["id", "title", "url", "durationMinutes", "format", "intensity", "location", "trainingType",
              "materials", "trainers", "tags", "summary", "description", "valuation", "totalViews",
              "publishDate", "previewImage"]
POST_URL = "https://webapp.fuertafit.com/#/post/"


def reload_catalog():
    global CATALOG, BY_ID
    CATALOG = load_catalog()
    BY_ID = {it["id"]: it for it in CATALOG}


def catalog_ids():
    """Ids ya guardados en el archivo (incluidos los que se filtran al cargar)."""
    if not CATALOG_PATH.exists():
        return []
    return [it["id"] for it in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))]


def import_items(items):
    """Añade o actualiza rutinas en catalogo.json. Devuelve cuántas son nuevas y cuántas se actualizaron."""
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else []
    by_id = {it["id"]: it for it in raw}
    added = updated = 0
    for it in items:
        if not isinstance(it, dict) or not isinstance(it.get("id"), int) or not isinstance(it.get("title"), str):
            continue
        clean = {k: it.get(k) for k in RAW_FIELDS}
        clean["url"] = POST_URL + str(it["id"])  # nunca confiamos en la URL que llega
        if it["id"] in by_id:
            updated += 1
        else:
            added += 1
        by_id[it["id"]] = clean
    tmp = CATALOG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(CATALOG_PATH)  # escritura atómica
    reload_catalog()
    save_settings({"catalogUpdated": datetime.now().isoformat(timespec="minutes")})
    return {"added": added, "updated": updated, "total": len(CATALOG)}


# ---------- historial ----------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS history ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " post_id INTEGER NOT NULL, done_on TEXT NOT NULL);"
        # Rutinas planificadas para un día (calendario). Una fila por bloque, en orden.
        "CREATE TABLE IF NOT EXISTS plan ("
        " day TEXT NOT NULL, position INTEGER NOT NULL, post_id INTEGER NOT NULL,"
        " note TEXT, source TEXT, PRIMARY KEY (day, position));"
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        # Estado especial de un día: 'skipped' (saltado), 'moved' (su rutina se movió), 'away' (vacaciones/fuera).
        "CREATE TABLE IF NOT EXISTS day_status (day TEXT PRIMARY KEY, status TEXT NOT NULL, note TEXT);"
    )
    return conn


def recent_history(days):
    since = (date.today() - timedelta(days=days)).isoformat()
    with db() as conn:
        rows = conn.execute(
            "SELECT post_id, done_on FROM history WHERE done_on >= ? ORDER BY done_on DESC", (since,)
        ).fetchall()
    return rows


# ---------- generador ----------

def _material_ok(it, mats):
    # Las rutinas suelen listar alternativas ("Casero o Mancuernas"): basta con tener una.
    return mats is None or any(m in mats for m in it["materials"])


def generate(params):
    minutes = max(5, int(params.get("minutes", 30)))
    tolerance = int(params.get("tolerance", 5))
    cooldown = bool(params.get("cooldown", False))
    warmup = bool(params.get("warmup", False))
    avoid_days = int(params.get("avoidDays", 14))
    exclude = set(params.get("exclude", []))
    types = params.get("types") or []
    groups = params.get("groups") or []
    intensities = params.get("intensities") or []
    mats = params.get("materials")
    rng = random.Random(params.get("seed"))

    hist = recent_history(avoid_days)
    recent_ids = {pid for pid, _ in hist}
    # Zona trabajada en los últimos 2 días -> se penaliza para alternar.
    two_days = (date.today() - timedelta(days=2)).isoformat()
    recent_zones = {
        BY_ID[pid].get("methodology") for pid, d in hist if d >= two_days and pid in BY_ID
    }

    pool = [it for it in CATALOG
            if it["id"] not in recent_ids and it["id"] not in exclude and _material_ok(it, mats)]
    def main_ok(it):
        tt = it.get("trainingType")
        if it["skip"] or (groups and it["group"] not in groups) or (types and tt not in types):
            return False
        if intensities and it.get("intensity") not in intensities:
            return False
        # Calentamientos y estiramientos solo como bloque principal si se piden expresamente.
        return bool(types) or tt not in SIDE_TYPES or it["group"] in groups

    main_pool = [it for it in pool if main_ok(it)]
    def side_fits(it):
        """Descarta calentamientos/estiramientos de la otra mitad del cuerpo (p. ej. «tren superior» en día de pierna)."""
        legs, upper = "Pierna y glúteo" in groups, "Torso" in groups
        if legs and not upper and UPPER_RX.search(it["title"]):
            return False
        return not (upper and not legs and LOWER_RX.search(it["title"]))

    short = [it for it in pool if it["durationMinutes"] <= 15 and not it["skip"]]
    warm_all = [it for it in short if it.get("trainingType") == WARMUP_TYPE]
    warm_pool = [it for it in warm_all if side_fits(it)] or warm_all
    cool_all = [it for it in short if it.get("trainingType") == COOLDOWN_TYPE
                and COOLDOWN_TITLES.search(it["title"])] \
        or [it for it in short if it.get("trainingType") == COOLDOWN_TYPE]
    cool_pool = [it for it in cool_all if side_fits(it)] or cool_all

    def weight(it):
        w = 1.0 + (it.get("valuation") or 3) / 5
        if it.get("methodology") in recent_zones:
            w *= 0.3
        return w * rng.random()

    def stem(it):
        # "Brazos 3" y "Brazos 7" son la misma serie: mejor no repetirla en una sesión.
        return re.sub(r"[\d\W_]+", " ", it["title"]).strip().lower()

    def fill(remaining, chosen):
        """Añade rutinas hasta completar el tiempo.

        Con varios grupos, el primero es el principal: se lleva ~60 % del tiempo y es el que rellena lo que sobre;
        los demás se reparten el resto con una rutina cada uno.
        """
        w = {it["id"]: weight(it) for it in main_pool}
        ranked = sorted(main_pool, key=lambda it: w[it["id"]], reverse=True)
        if len(groups) > 1:
            shares = [remaining * 0.6] + [remaining * 0.4 / (len(groups) - 1)] * (len(groups) - 1)
            passes = [([it for it in ranked if it["group"] == g], share) for g, share in zip(groups, shares)]
            ranked = sorted(ranked, key=lambda it: it["group"] != groups[0])  # estable: mantiene el azar dentro
        else:
            passes = []
        used_zones, used_stems = set(), set()
        for candidates, limit in passes + [(ranked, None)]:
            for it in candidates:
                if remaining < 5:
                    return remaining
                d = it["durationMinutes"]
                # Los grupos secundarios no pueden pasarse de su parte; el principal sí, con la tolerancia.
                slack = 0 if limit is not None and it["group"] != groups[0] else tolerance
                if d > min(limit or remaining, remaining) + slack or it in chosen:
                    continue
                zone = it.get("methodology")
                if (zone and zone in used_zones or stem(it) in used_stems) and rng.random() < 0.8:
                    continue  # preferimos variar de zona y de serie dentro de la sesión
                chosen.append(it)
                used_zones.add(zone)
                used_stems.add(stem(it))
                remaining -= d
                if limit is not None:
                    break  # una por grupo en la primera pasada
        return remaining

    best = None
    for _ in range(300):
        head = [rng.choice(warm_pool)] if warmup and warm_pool and minutes >= 20 else []
        tail = [rng.choice(cool_pool)] if cooldown and cool_pool and minutes >= 25 else []
        remaining = minutes - sum(b["durationMinutes"] for b in head + tail)
        main = []
        fill(remaining, main)
        blocks = head + main + tail
        total = sum(b["durationMinutes"] for b in blocks)
        score = abs(total - minutes) * 10 + len(blocks)
        if best is None or score < best[0]:
            best = (score, blocks)
        if total == minutes:
            break

    blocks = best[1] if best else []
    return {
        "minutes": minutes,
        "total": sum(b["durationMinutes"] for b in blocks),
        "blocks": blocks,
        "poolSize": len(main_pool),
    }


def meta():
    def counts(key):
        out = {}
        for it in CATALOG:
            vals = it.get(key)
            for v in (vals if isinstance(vals, list) else [vals]):
                if v:
                    out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    return {
        "total": len(CATALOG),
        "types": counts("trainingType"),
        "intensities": counts("intensity"),
        "materials": counts("materials"),
        "methodologies": counts("methodology"),
        "groups": {g: sum(1 for it in CATALOG if it["group"] == g) for g in GROUPS},
    }


def mark_done(post_ids, day=None):
    day = day or date.today().isoformat()
    with db() as conn:
        # Una misma rutina solo cuenta una vez por día.
        conn.executemany(
            "INSERT INTO history (post_id, done_on) SELECT ?1, ?2 WHERE NOT EXISTS"
            " (SELECT 1 FROM history WHERE post_id = ?1 AND done_on = ?2)",
            [(int(pid), day) for pid in post_ids],
        )


def unmark_done(post_ids, day=None):
    day = day or date.today().isoformat()
    with db() as conn:
        conn.executemany("DELETE FROM history WHERE post_id = ? AND done_on = ?",
                         [(int(pid), day) for pid in post_ids])


def history_between(start, end):
    with db() as conn:
        return conn.execute(
            "SELECT post_id, done_on FROM history WHERE done_on BETWEEN ? AND ? ORDER BY done_on DESC",
            (start, end),
        ).fetchall()


# ---------- calendario ----------

def get_plans(start, end):
    """{día: {"note": str, "source": str, "postIds": [...]}} entre dos fechas (incluidas)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT day, post_id, note, source FROM plan WHERE day BETWEEN ? AND ? ORDER BY day, position",
            (start, end),
        ).fetchall()
    plans = {}
    for day, pid, note, source in rows:
        p = plans.setdefault(day, {"note": note, "source": source, "postIds": []})
        p["postIds"].append(pid)
    return plans


def save_plan(day, post_ids, note=None, source="manual"):
    ids = [int(pid) for pid in post_ids if int(pid) in BY_ID]
    with db() as conn:
        conn.execute("DELETE FROM plan WHERE day = ?", (day,))
        conn.executemany(
            "INSERT INTO plan (day, position, post_id, note, source) VALUES (?, ?, ?, ?, ?)",
            [(day, i, pid, note, source) for i, pid in enumerate(ids)],
        )
    return ids


def delete_plan(day):
    with db() as conn:
        conn.execute("DELETE FROM plan WHERE day = ?", (day,))


# ---------- ajustes ----------

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
    with db() as conn:
        rows = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    return {k: json.loads(rows[k]) if k in rows else v for k, v in DEFAULT_SETTINGS.items()}


def save_settings(values):
    with db() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(k, json.dumps(v)) for k, v in values.items() if k in DEFAULT_SETTINGS],
        )
    return get_settings()


# ---------- búsqueda en el catálogo ----------

def _norm(text):
    return (text or "").lower()


def search(q=None, types=None, groups=None, intensities=None, materials=None,
           min_minutes=None, max_minutes=None, methodology=None, offset=0, limit=30):
    words = _norm(q).split()
    out = []
    for it in CATALOG:
        if types and it.get("trainingType") not in types:
            continue
        if groups and it["group"] not in groups:
            continue
        if intensities and it.get("intensity") not in intensities:
            continue
        if not _material_ok(it, materials or None):
            continue
        d = it["durationMinutes"]
        if (min_minutes and d < min_minutes) or (max_minutes and d > max_minutes):
            continue
        if methodology and _norm(methodology) not in _norm(it.get("methodology")):
            continue
        if words:
            hay = _norm(" ".join([it["title"], it.get("summary") or "", it.get("methodology") or "", it["group"],
                                  it.get("trainingType") or "", " ".join(it.get("trainers") or [])]))
            if not all(w in hay for w in words):
                continue
        out.append(it)
    # Lo más reciente primero.
    out.sort(key=lambda it: it.get("publishDate") or "", reverse=True)
    return {"total": len(out), "items": out[offset:offset + limit]}


# ---------- plan semanal automático ----------

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


# ---------- estados de día: saltar, mover, vacaciones ----------

def _days(start, end):
    d, last = date.fromisoformat(start), date.fromisoformat(end)
    while d <= last:
        yield d.isoformat()
        d += timedelta(1)


def get_status(start, end):
    with db() as conn:
        rows = conn.execute("SELECT day, status, note FROM day_status WHERE day BETWEEN ? AND ?",
                            (start, end)).fetchall()
    return {day: {"status": st, "note": note} for day, st, note in rows}


def set_status(start, end, status, note=None):
    with db() as conn:
        conn.executemany("INSERT OR REPLACE INTO day_status (day, status, note) VALUES (?, ?, ?)",
                         [(d, status, note) for d in _days(start, end)])


def clear_status(start, end):
    with db() as conn:
        conn.execute("DELETE FROM day_status WHERE day BETWEEN ? AND ?", (start, end))


def _short(day):
    d = date.fromisoformat(day)
    return f"{['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'][d.weekday()]} {d.day}/{d.month}"


def move_plan(src, dst):
    """Mueve la rutina de `src` a `dst`. Si `dst` ya tenía rutina, se intercambian."""
    plans = get_plans(min(src, dst), max(src, dst))
    a, b = plans.get(src), plans.get(dst)
    if not a:
        raise ValueError("Ese día no tiene rutina que mover.")
    save_plan(dst, a["postIds"], a["note"], a["source"])
    clear_status(dst, dst)
    if b:
        save_plan(src, b["postIds"], b["note"], b["source"])
        return "swapped"
    delete_plan(src)
    # Marcado como movido para que el plan automático no vuelva a rellenarlo.
    set_status(src, src, "moved", f"Movida al {_short(dst)}")
    return "moved"


def skip_day(day, note=None):
    set_status(day, day, "skipped", note or "Saltado")


def set_away(start, end, note=None, remove_plans=True):
    if end < start:
        start, end = end, start
    if remove_plans:
        with db() as conn:
            conn.execute("DELETE FROM plan WHERE day BETWEEN ? AND ?", (start, end))
    set_status(start, end, "away", note or "Fuera")


def update_away(old_start, old_end, start, end, note=None, remove_plans=True):
    """Cambia fechas y/o motivo de una ausencia. Los días que dejan de estar fuera quedan libres
    (sus rutinas, si se quitaron al marcar la ausencia, no vuelven)."""
    with db() as conn:
        conn.execute("DELETE FROM day_status WHERE status = 'away' AND day BETWEEN ? AND ?", (old_start, old_end))
    set_away(start, end, note, remove_plans)


def away_ranges(since):
    """Ausencias desde `since`, agrupando días seguidos con el mismo motivo."""
    with db() as conn:
        rows = conn.execute("SELECT day, note FROM day_status WHERE status = 'away' AND day >= ? ORDER BY day",
                            (since,)).fetchall()
    ranges = []
    for day, note in rows:
        last = ranges[-1] if ranges else None
        if last and last["note"] == note and date.fromisoformat(day) - date.fromisoformat(last["end"]) == timedelta(1):
            last["end"] = day
        else:
            ranges.append({"start": day, "end": day, "note": note})
    return ranges

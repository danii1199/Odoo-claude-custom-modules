"""Conexión a PostgreSQL (contenedor `postgres`, base de datos `rutinas`) y esquema de tablas.

`connect()` devuelve un envoltorio fino sobre psycopg que admite `?` como marcador (igual que antes con SQLite):
    with connect() as conn:
        conn.execute("SELECT ... WHERE day = ?", (day,)).fetchall()
Al salir del `with` confirma los cambios (o los deshace si hubo un error) y cierra la conexión.
"""
import threading
import time

import psycopg

from app.config import DATABASE_URL

IntegrityError = psycopg.IntegrityError

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalog (id INTEGER PRIMARY KEY, data JSONB NOT NULL);
CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY, post_id INTEGER NOT NULL, done_on TEXT NOT NULL, UNIQUE (post_id, done_on));
-- Rutinas planificadas para un día (calendario). Una fila por bloque, en orden.
CREATE TABLE IF NOT EXISTS plan (
    day TEXT NOT NULL, position INTEGER NOT NULL, post_id INTEGER NOT NULL, note TEXT, source TEXT,
    PRIMARY KEY (day, position));
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
-- Estado especial de un día: 'skipped' (saltado), 'moved' (su rutina se movió), 'away' (vacaciones/fuera).
CREATE TABLE IF NOT EXISTS day_status (day TEXT PRIMARY KEY, status TEXT NOT NULL, note TEXT);
"""

_ready = False
_lock = threading.Lock()


class Conn:
    def __init__(self):
        self.pg = psycopg.connect(DATABASE_URL)

    def execute(self, sql, params=()):
        return self.pg.execute(sql.replace("?", "%s"), params)

    def executemany(self, sql, seq):
        with self.pg.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), list(seq))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        (self.pg.rollback if exc_type else self.pg.commit)()
        self.pg.close()


def _ensure_schema():
    """Crea las tablas la primera vez. Al arrancar, espera a que Postgres esté listo (hasta ~1 min)."""
    global _ready
    with _lock:
        if _ready:
            return
        for attempt in range(30):
            try:
                with psycopg.connect(DATABASE_URL, autocommit=True) as pg:
                    pg.execute(SCHEMA)
                break
            except psycopg.OperationalError:
                if attempt == 29:
                    raise
                time.sleep(2)
        _ready = True


def connect():
    _ensure_schema()
    return Conn()

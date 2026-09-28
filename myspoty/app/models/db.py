"""Conexión a PostgreSQL (contenedor `postgres`, base de datos `myspoty`) y esquema de tablas (multiusuario).

`connect()` devuelve un envoltorio fino sobre psycopg que admite `?` como marcador:
    with connect() as conn:
        conn.execute("SELECT ... WHERE id = ?", (id,)).fetchall()
Al salir del `with` confirma los cambios (o los deshace si hubo un error) y cierra la conexión.

Datos de cada usuario: llevan `user_id` (id de Spotify). Compartidos por todos: `tracks` (copia de canciones) y `lyrics`.
"""
import json
import threading
import time

import psycopg

from app.config import DATABASE_URL

IntegrityError = psycopg.IntegrityError

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, image TEXT, product TEXT,
    created_at TEXT NOT NULL);
-- Permiso de Spotify de cada usuario (lo usa el servidor para la sincronización y el reproductor).
CREATE TABLE IF NOT EXISTS tokens (user_id TEXT PRIMARY KEY, access_token TEXT NOT NULL, refresh_token TEXT NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL);
-- Sesiones del navegador (cookie). Una por dispositivo.
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL, agent TEXT);
-- Códigos para conectar otro dispositivo sin volver a pasar por Spotify.
CREATE TABLE IF NOT EXISTS device_codes (code TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL);
-- Compartido: copia mínima de cada canción (para reglas y estadísticas sin llamar a Spotify).
CREATE TABLE IF NOT EXISTS tracks (id TEXT PRIMARY KEY, uri TEXT NOT NULL, name TEXT NOT NULL, artists TEXT NOT NULL,
    album TEXT, image TEXT, duration_ms INTEGER);
CREATE TABLE IF NOT EXISTS tags (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, color TEXT NOT NULL,
    UNIQUE (user_id, name));
CREATE TABLE IF NOT EXISTS track_tags (track_id TEXT NOT NULL, tag_id INTEGER NOT NULL, added_at TEXT NOT NULL,
    PRIMARY KEY (track_id, tag_id));
CREATE TABLE IF NOT EXISTS track_meta (user_id TEXT NOT NULL, track_id TEXT NOT NULL, rating INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '', PRIMARY KEY (user_id, track_id));
CREATE TABLE IF NOT EXISTS smart (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, rules TEXT NOT NULL,
    spotify_id TEXT, synced_at TEXT);
CREATE TABLE IF NOT EXISTS plays (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, track_id TEXT NOT NULL,
    played_at TEXT NOT NULL, UNIQUE (user_id, track_id, played_at));
CREATE TABLE IF NOT EXISTS spotify_top (user_id TEXT NOT NULL, range TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL,
    PRIMARY KEY (user_id, range, kind));
CREATE TABLE IF NOT EXISTS sync_state (user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY (user_id, key));
CREATE TABLE IF NOT EXISTS liked (user_id TEXT NOT NULL, track_id TEXT NOT NULL, added_at TEXT NOT NULL,
    PRIMARY KEY (user_id, track_id));
-- Compartido: letras de LRCLIB. synced = formato LRC "[mm:ss.xx] línea"; vacías = no encontrada.
CREATE TABLE IF NOT EXISTS lyrics (track_id TEXT PRIMARY KEY, synced TEXT NOT NULL DEFAULT '',
    plain TEXT NOT NULL DEFAULT '', fetched_at TEXT NOT NULL);
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


def _migrate_single_user(pg):
    """Versión antigua (un solo usuario, tabla `auth`) -> multiusuario. Todo lo existente pasa a su dueño."""
    rows = dict(pg.execute("SELECT key, value FROM auth").fetchall())
    user = json.loads(rows["user"]) if "user" in rows else None
    owner = user["id"] if user else None
    pg.execute(SCHEMA)  # crea users, tokens, sessions… (las tablas antiguas no se tocan aquí)
    if user:
        pg.execute("INSERT INTO users (id, name, image, product, created_at) VALUES (%s, %s, %s, %s, now()::text)"
                   " ON CONFLICT DO NOTHING", (owner, user.get("name") or owner, user.get("image"), user.get("product")))
        if "refresh_token" in rows:
            pg.execute("INSERT INTO tokens (user_id, access_token, refresh_token, expires_at) VALUES (%s, %s, %s, %s)"
                       " ON CONFLICT DO NOTHING", (owner, json.loads(rows.get("access_token", '""')),
                                                   json.loads(rows["refresh_token"]), json.loads(rows.get("expires_at", "0"))))

    def add_owner(table):
        pg.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id TEXT")
        pg.execute(f"UPDATE {table} SET user_id = %s WHERE user_id IS NULL", (owner,))
        pg.execute(f"DELETE FROM {table} WHERE user_id IS NULL")  # sin dueño conocido (no debería haber)
        pg.execute(f"ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL")

    for table in ("tags", "track_meta", "smart", "plays", "spotify_top", "sync_state", "liked"):
        add_owner(table)
    pg.execute("ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_name_key, ADD CONSTRAINT tags_user_name UNIQUE (user_id, name)")
    pg.execute("ALTER TABLE track_meta DROP CONSTRAINT track_meta_pkey, ADD PRIMARY KEY (user_id, track_id)")
    pg.execute("ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_track_id_played_at_key,"
               " ADD CONSTRAINT plays_user_track_time UNIQUE (user_id, track_id, played_at)")
    pg.execute("ALTER TABLE spotify_top DROP CONSTRAINT spotify_top_pkey, ADD PRIMARY KEY (user_id, range, kind)")
    pg.execute("ALTER TABLE sync_state DROP CONSTRAINT sync_state_pkey, ADD PRIMARY KEY (user_id, key)")
    pg.execute("ALTER TABLE liked DROP CONSTRAINT liked_pkey, ADD PRIMARY KEY (user_id, track_id)")
    pg.execute("DROP TABLE auth")
    print(f"[db] Migrado a multiusuario: los datos existentes son de «{user['name'] if user else '—'}».", flush=True)


def _ensure_schema():
    """Crea las tablas la primera vez (o migra la versión de un solo usuario). Espera a Postgres (~1 min)."""
    global _ready
    with _lock:
        if _ready:
            return
        for attempt in range(30):
            try:
                with psycopg.connect(DATABASE_URL) as pg:  # una transacción: o migra entero o nada
                    if pg.execute("SELECT to_regclass('auth')").fetchone()[0]:
                        _migrate_single_user(pg)
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

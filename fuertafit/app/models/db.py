"""Conexión a SQLite y esquema de tablas."""
import sqlite3

from app.config import DB_PATH

SCHEMA = (
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


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn

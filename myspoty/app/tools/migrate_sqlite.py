"""Migración única: copia data/musica.db (SQLite, versión antigua) a Postgres.

Uso (con el contenedor construido):  python -m app.tools.migrate_sqlite /ruta/musica.db
No borra nada del SQLite. Si Postgres ya tiene datos, no hace nada (para no duplicar).
"""
import sqlite3
import sys

from app.models.db import connect

TABLES = {  # tabla -> columnas (en este orden)
    "auth": ["key", "value"],
    "tracks": ["id", "uri", "name", "artists", "album", "image", "duration_ms"],
    "tags": ["id", "name", "color"],
    "track_tags": ["track_id", "tag_id", "added_at"],
    "track_meta": ["track_id", "rating", "note"],
    "smart": ["id", "name", "rules", "spotify_id", "synced_at"],
    "plays": ["track_id", "played_at"],
    "spotify_top": ["range", "kind", "data"],
    "sync_state": ["key", "value"],
}


def main(path):
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    have = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    with connect() as dst:
        if dst.execute("SELECT COUNT(*) FROM auth").fetchone()[0]:
            print("Postgres ya tiene datos: no se migra nada.")
            return
        for table, cols in TABLES.items():
            if table not in have:
                continue
            rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
            dst.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
                            " ON CONFLICT DO NOTHING", rows)
            print(f"{table}: {len(rows)} filas")
        # Los ids copiados a mano no mueven los contadores: se ajustan para las filas nuevas.
        for table in ("tags", "smart"):
            dst.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {table}")


if __name__ == "__main__":
    main(sys.argv[1])

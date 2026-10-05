"""Letras sincronizadas desde LRCLIB (lrclib.net: base de datos abierta, sin clave), con caché en Postgres.

La API de Spotify no ofrece letras. LRCLIB devuelve `syncedLyrics` en formato LRC ("[00:13.58] texto") y/o
`plainLyrics` sin tiempos. Si no hay letra se guarda vacía y no se vuelve a buscar hasta pasada una semana.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from app.models.db import connect

API = "https://lrclib.net/api"
HEADERS = {"User-Agent": "myspoty/1.0 (reproductor personal)"}
RETRY_EMPTY = timedelta(days=7)


def _get(path, params):
    req = urllib.request.Request(f"{API}/{path}?{urllib.parse.urlencode(params)}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise  # 5xx u otros: no se guarda nada, se reintenta la próxima vez
    except (urllib.error.URLError, TimeoutError):
        raise


def _lookup(name, artist, album, duration):
    """Devuelve (letra, definitivo). definitivo=False si LRCLIB estaba saturado: no se guarda y se reintenta luego."""
    base = {"track_name": name, "artist_name": artist}
    # 1) exacta (con álbum y duración ayuda a acertar la versión), 2) sin álbum/duración, 3) búsqueda
    for params in ({**base, "album_name": album or "", "duration": duration} if album and duration else None, base):
        if params:
            try:
                hit = _get("get", params)
            except urllib.error.HTTPError:
                continue  # LRCLIB a veces responde 5xx en vez de 404: se sigue con la búsqueda
            if hit and (hit.get("syncedLyrics") or hit.get("plainLyrics")):
                return hit, True
    try:
        results = _get("search", base) or []
    except urllib.error.HTTPError:
        return None, False  # la búsqueda de LRCLIB a veces está saturada (503)
    hit = next((r for r in results if r.get("syncedLyrics")), None) or next((r for r in results if r.get("plainLyrics")), None)
    return hit, True


def get(track_id, name, artist, album=None, duration_ms=None):
    with connect() as conn:
        row = conn.execute("SELECT synced, plain, fetched_at FROM lyrics WHERE track_id = ?", (track_id,)).fetchone()
    if row and (row[0] or row[1] or datetime.fromisoformat(row[2]) > datetime.now() - RETRY_EMPTY):
        return {"synced": row[0], "plain": row[1]}
    # Nombres "limpios": sin "- Remastered", "(feat. …)" para que LRCLIB encuentre la canción.
    clean = name.split(" - ")[0].split(" (feat")[0].strip()
    hit, definitive = _lookup(clean, artist, album, round(duration_ms / 1000) if duration_ms else None)
    synced = (hit or {}).get("syncedLyrics") or ""
    plain = (hit or {}).get("plainLyrics") or ""
    if not definitive:
        return {"synced": "", "plain": "", "retry": True}
    with connect() as conn:
        conn.execute("INSERT INTO lyrics (track_id, synced, plain, fetched_at) VALUES (?, ?, ?, ?)"
                     " ON CONFLICT (track_id) DO UPDATE SET synced = EXCLUDED.synced, plain = EXCLUDED.plain,"
                     " fetched_at = EXCLUDED.fetched_at",
                     (track_id, synced, plain, datetime.now().isoformat(timespec="seconds")))
    return {"synced": synced, "plain": plain}

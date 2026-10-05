"""Cuentas: usuarios (id de Spotify), su permiso de Spotify, sesiones del navegador y códigos de dispositivo."""
import secrets
import time
from datetime import datetime

from app.context import uid
from app.models.db import connect

SESSION_DAYS = 90
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para que no se confundan


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------- usuarios ----------

def upsert_user(profile):
    with connect() as conn:
        conn.execute("INSERT INTO users (id, name, image, product, created_at) VALUES (?, ?, ?, ?, ?)"
                     " ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, image = EXCLUDED.image, product = EXCLUDED.product",
                     (profile["id"], profile["name"], profile.get("image"), profile.get("product"), _now()))


def get_user(user_id=None):
    with connect() as conn:
        r = conn.execute("SELECT id, name, image, product FROM users WHERE id = ?", (user_id or uid(),)).fetchone()
    return {"id": r[0], "name": r[1], "image": r[2], "product": r[3]} if r else None


def users_with_tokens():
    with connect() as conn:
        return [r[0] for r in conn.execute("SELECT user_id FROM tokens ORDER BY user_id")]


# ---------- permiso de Spotify del usuario actual ----------

def get_tokens():
    with connect() as conn:
        r = conn.execute("SELECT access_token, refresh_token, expires_at FROM tokens WHERE user_id = ?", (uid(),)).fetchone()
    return {"access_token": r[0], "refresh_token": r[1], "expires_at": r[2]} if r else None


def save_tokens(access_token, refresh_token, expires_at):
    with connect() as conn:
        conn.execute("INSERT INTO tokens (user_id, access_token, refresh_token, expires_at) VALUES (?, ?, ?, ?)"
                     " ON CONFLICT (user_id) DO UPDATE SET access_token = EXCLUDED.access_token,"
                     " refresh_token = EXCLUDED.refresh_token, expires_at = EXCLUDED.expires_at",
                     (uid(), access_token, refresh_token, expires_at))


def expire_token():
    with connect() as conn:
        conn.execute("UPDATE tokens SET expires_at = 0 WHERE user_id = ?", (uid(),))


# ---------- sesiones (cookie) ----------

def create_session(user_id, agent=None):
    sid = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute("INSERT INTO sessions (id, user_id, created_at, last_seen, agent) VALUES (?, ?, ?, ?, ?)",
                     (sid, user_id, _now(), _now(), (agent or "")[:200]))
    return sid


def user_for_session(sid):
    if not sid:
        return None
    with connect() as conn:
        r = conn.execute("SELECT user_id, last_seen FROM sessions WHERE id = ?", (sid,)).fetchone()
        if not r:
            return None
        if (datetime.now() - datetime.fromisoformat(r[1])).days > SESSION_DAYS:
            conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            return None
        if r[1][:13] != _now()[:13]:  # como mucho una escritura por hora y sesión
            conn.execute("UPDATE sessions SET last_seen = ? WHERE id = ?", (_now(), sid))
    return r[0]


def delete_session(sid):
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))


def sessions_of_user():
    with connect() as conn:
        return [{"agent": a, "lastSeen": s} for a, s in conn.execute(
            "SELECT agent, last_seen FROM sessions WHERE user_id = ? ORDER BY last_seen DESC", (uid(),))]


# ---------- conectar otro dispositivo con un código ----------

def new_device_code(minutes=10):
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
    with connect() as conn:
        conn.execute("DELETE FROM device_codes WHERE expires_at < ? OR user_id = ?", (time.time(), uid()))
        conn.execute("INSERT INTO device_codes (code, user_id, expires_at) VALUES (?, ?, ?)",
                     (code, uid(), time.time() + minutes * 60))
    return code


def use_device_code(code):
    """Un solo uso: devuelve el usuario del código (o None si no existe o caducó)."""
    code = (code or "").strip().upper().replace(" ", "").replace("-", "")
    with connect() as conn:
        r = conn.execute("DELETE FROM device_codes WHERE code = ? RETURNING user_id, expires_at", (code,)).fetchone()
    return r[0] if r and r[1] >= time.time() else None

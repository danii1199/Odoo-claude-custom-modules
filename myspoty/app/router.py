"""Registro de rutas: los controladores declaran sus rutas con @route y el servidor las despacha."""
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

ROUTES = {}   # (método, ruta) -> función(request)
PUBLIC = set()  # rutas /api que no necesitan sesión


class Request:
    def __init__(self, query_string, body, headers=None, user=None):
        self.query = {k: v[0] for k, v in parse_qs(query_string).items()}
        self.body = body
        self.headers = headers or {}
        self.user = user
        self.cookies = {k: m.value for k, m in SimpleCookie(self.headers.get("Cookie", "")).items()}
        self.set_cookies = []  # cabeceras Set-Cookie que añadirá el servidor

    @property
    def origin(self):
        """Dirección por la que se ha entrado (respetando un proxy HTTPS delante: Tailscale, Cloudflare…)."""
        proto = self.headers.get("X-Forwarded-Proto") or "http"
        return f"{proto}://{self.headers.get('X-Forwarded-Host') or self.headers.get('Host', '')}"

    def set_cookie(self, name, value, max_age):
        secure = "; Secure" if self.origin.startswith("https://") else ""
        self.set_cookies.append(f"{name}={value}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Lax{secure}")

    def get(self, key, default=None):
        return self.query.get(key, default)

    def get_list(self, key):
        """Parámetro separado por comas ("a,b") como lista; [] si viene vacío."""
        return [x for x in self.query.get(key, "").split(",") if x]

    def get_int(self, key, default=None):
        value = self.query.get(key)
        return int(value) if value else default


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Redirect:
    """Respuesta de redirección (login con Spotify y vuelta a la web)."""
    def __init__(self, location):
        self.location = location


def route(method, path, public=False):
    def register(handler):
        ROUTES[(method, path)] = handler
        if public:
            PUBLIC.add(path)
        return handler
    return register

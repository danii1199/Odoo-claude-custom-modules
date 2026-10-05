"""Registro de rutas: los controladores declaran sus rutas con @route y el servidor las despacha."""
from urllib.parse import parse_qs

ROUTES = {}  # (método, ruta) -> función(request)


class Request:
    def __init__(self, query_string, body):
        self.query = {k: v[0] for k, v in parse_qs(query_string).items()}
        self.body = body

    def get(self, key, default=None):
        return self.query.get(key, default)

    def get_list(self, key):
        """Parámetro separado por comas ("a,b") como lista; None si viene vacío."""
        return [x for x in self.query.get(key, "").split(",") if x] or None

    def get_int(self, key, default=None):
        value = self.query.get(key)
        return int(value) if value else default


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def route(method, path):
    def register(handler):
        ROUTES[(method, path)] = handler
        return handler
    return register

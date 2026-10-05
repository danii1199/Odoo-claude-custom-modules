"""Usuario de la petición en curso.

El servidor lo fija al empezar cada petición (a partir de la cookie de sesión) y la tarea horaria al recorrer los
usuarios. Los modelos lo leen con `uid()`, así no hay que pasarlo de función en función.
"""
from contextlib import contextmanager
from contextvars import ContextVar

_user = ContextVar("user_id", default=None)


class NotLoggedIn(Exception):
    pass


def uid():
    user = _user.get()
    if not user:
        raise NotLoggedIn("No has iniciado sesión.")
    return user


def current():
    return _user.get()


@contextmanager
def as_user(user_id):
    token = _user.set(user_id)
    try:
        yield
    finally:
        _user.reset(token)

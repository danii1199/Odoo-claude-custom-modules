"""myspoty: reproductor propio de Spotify (Web API + Web Playback SDK) con datos propios encima.

Estructura MVC:
- models/       datos propios en SQLite: sesión de Spotify, canciones, etiquetas, valoraciones, playlists
                inteligentes e historial de escucha
- services/     lógica: cliente de Spotify (OAuth PKCE + API) y playlists inteligentes
- controllers/  rutas: login con Spotify y /api/*
- views/        la web del reproductor (views/static)
"""

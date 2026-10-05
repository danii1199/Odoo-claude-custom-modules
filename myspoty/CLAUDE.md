# myspoty

Reproductor propio de Spotify (Web API + Web Playback SDK) con datos propios encima. Proyecto **independiente**
de "Mi rutina Fuerta" (`../fuertafit`, mismo repo `claude-test`): base de datos, Docker y puerto propios. El usuario tiene Premium.
Interfaz y código en español.

## Multiusuario (desde 2026-09-28)

- Cada usuario = su id de Spotify (`users`); su permiso en `tokens`; sesiones del navegador por cookie HttpOnly
  `myspoty_sid` (`sessions`, 90 días). `app/context.py`: el servidor fija el usuario de cada petición
  (`as_user`) y los modelos filtran con `uid()`. Tablas por usuario llevan `user_id`; `tracks` y `lyrics` son
  compartidas; `track_tags` se filtra a través de `tags.user_id`.
- `/api/*` exige sesión salvo rutas `@route(..., public=True)`. Login: `SPOTIFY_REDIRECT_URIS` (coma) y se usa la
  que coincide con la dirección de entrada (`Request.origin`, respeta `X-Forwarded-*` de un proxy HTTPS).
- Otros dispositivos sin HTTPS: código de 6 letras (`/api/device/code` → `/api/device/login`, 10 min, un uso).
- La sync horaria recorre `auth.users_with_tokens()` con 20 s entre usuarios. `MYSPOTY_NO_SYNC=1` la desactiva
  (pruebas: **nunca** arrancar una instancia de pruebas con tokens reales y la sync activa: renueva el permiso).
- Spotify en modo desarrollo: máx. 25 usuarios, dados de alta por email en el panel (User Management); si no, `/me`
  da 403 y el login lo explica. Para que entren otros hace falta una Redirect URI **https** (pendiente: Tailscale o dominio).
- Bloqueos largos de Spotify (429 con Retry-After > 60 s) se recuerdan por tipo de petición (`_blocked`) y no se
  reintentan. El 2026-09-28 `GET /artists/{id}/albums` quedó bloqueado ~22 h por las pruebas.

## Arquitectura (MVC, paquete `app/`, solo librería estándar de Python)

- `config.py`: `SPOTIFY_CLIENT_ID` (de `.env`), `REDIRECT_URI` = `http://127.0.0.1:8001/callback` (Spotify no acepta
  `localhost`), scopes, `DATA_DIR`.
- `router.py`: `@route`, `Request`, `HttpError`, `Redirect`. `server.py`: despacha rutas; cualquier GET sin extensión
  que no sea ruta devuelve `index.html` (rutas sin `#`); errores no controlados -> 400/500 JSON, nunca cortar conexión;
  el log oculta la query del `/callback`.
- **Datos en Postgres** (contenedor `postgres`, base de datos `myspoty`, volumen `postgres-datos`; ver `../postgres`).
  `DATABASE_URL` en `.env`. Migrado desde SQLite el 2026-09-28 (`app/tools/migrate_sqlite.py`; copia del SQLite en
  `proyectitos/copias-seguridad/`).
- `models/`: `db.py` (conexión con marcadores `?`, esquema y migración desde un solo usuario), `auth.py` (usuarios, tokens, sesiones, códigos), `auth.py` (tokens y perfil), `library.py` (copia mínima de canciones, etiquetas,
  valoración, notas, `find_tracks` para reglas), `smart.py`, `plays.py` (historial y estadísticas).
- `services/spotify.py`: OAuth **PKCE** (sin client secret; `_pending` guarda state->verifier en memoria), renovación
  del token y `api()` para llamadas desde el servidor. `services/smart_playlists.py`: reglas -> preview -> sync
  (crea playlist privada "⚡ nombre" y reescribe con PUT/POST de 100 en 100).
- `services/smart_sources.py`: fuentes de las inteligentes (`rules.sources`, se mezclan alternándolas): `top`,
  `artists` (discografía + búsqueda de tus artistas top, excluye lo conocido), `collab` (colaboradores de tus
  favoritos = "relacionados" caseros), `genre` (búsqueda `genre:"x"`), `liked_recent`, `forgotten`, `history`, `tags`.
  `rules.daily`: la sync horaria las renueva en Spotify cada 24 h. Tabla `liked` = copia de Tus me gusta (se relee
  solo si cambia el total o la más reciente). Caché en memoria del proceso: búsquedas 1 h, discografías 24 h.
- `services/lyrics.py` + `GET /api/lyrics`: letras de **LRCLIB** (lrclib.net, sin clave; Spotify no da letras) con caché
  en la tabla `lyrics` (vacía = sin letra, se reintenta a los 7 días; si la búsqueda de LRCLIB da 503 no se guarda).
  `Now` (player.js): portada + controles a la izquierda, letra LRC sincronizada a la derecha (rAF, 250 ms de adelanto),
  clic en una línea = seek, rueda/arrastre = deja de seguir y muestra «Sincronizar». Con `.now-open` se oculta el dock.
- **Límites de la API (comprobado 2026-09-28):** recomendaciones (404), related-artists, top-tracks de artista y
  `GET /albums?ids=` (403) no disponibles; la búsqueda admite `limit` ≤ 10. Hay rate limit: no lanzar syncs
  completas seguidas en pruebas (la de hoy lo disparó). `api()` espera y reintenta una vez con 429 si Retry-After ≤ 10 s.
- `services/sync.py` + `scheduler.py`: cada hora (y 10 s tras arrancar, y en segundo plano tras el login)
  guarda las últimas 50 escuchas de `/me/player/recently-played` en `plays` (índice único track+hora, hora UTC ->
  Madrid) y los tops `/me/top/{tracks,artists}` de los 3 periodos en `spotify_top`. La web ya no registra escuchas.
  Spotify devuelve `genres` vacío a esta app: la UI lo oculta. `/artists/{id}/top-tracks` da 403 y seguir artistas
  necesitaría el scope `user-follow-*` (no pedido).
- `views/static/`: `index.html`, `css/base.css` + `css/ui.css`, `js/`: `core.js` (utilidades, `api()` al servidor,
  `sp()` a Spotify con el token de `/api/token`, `Aura`), `player.js` (`Player` con el SDK y control remoto, `Now`),
  `editor.js` (`Pop`, `Editor`, `TrackList` con selección Ctrl/Mayús, clic derecho, ⋯ y Supr), `menu.js` (`Menu` con
  submenús, `Ask` diálogos, `Lib` acciones de biblioteca, menús de canción/playlist/álbum/artista, `ctxAttrs` para
  marcar tarjetas y cabeceras con clic derecho), `views.js` (inicio, playlists, playlist, me gusta, álbum, artista),
  `organize.js` (etiquetas, inteligentes, estadísticas),
  `palette.js` (Ctrl+K), `main.js` (rutas y arranque). Scripts clásicos con ámbito global compartido.
- El navegador llama a la Web API de Spotify directamente; el servidor solo guarda la sesión y los datos propios.

## Ejecutar

```bash
sg docker -c "docker compose up -d --build"   # tras cambiar app/
sg docker -c "docker compose up -d --force-recreate"   # tras cambiar .env (restart NO relee el .env)
```
Contenedor `myspoty`, `user: 1000:1000`, puerto `8001` **abierto a la red de casa** (decisión del usuario, sin
contraseña), red Docker externa `proyectitos`. Login con Spotify solo por `http://127.0.0.1:8001`; por `http://IP` el
navegador no reproduce (sin contexto seguro) y la web hace de mando a distancia (`Player`: `canPlayHere`).

## Normas

- No leer ni mostrar `.env` ni los tokens de la tabla `auth`. No pedir al usuario credenciales de Spotify.
- Abierto a la LAN sin autenticación por decisión del usuario; no exponerlo fuera de casa sin HTTPS y autenticación.
- Pruebas: base de datos `myspoty_test` (crearla/borrarla con `docker exec postgres psql -U admin`) y `SPOTIFY_CLIENT_ID=prueba` para lo que no
  necesita sesión; lo que sí la necesita lo prueba el usuario. JS: `node --check` con `node:20-alpine` en Docker y,
  para comportamiento (menús, selección, vistas), jsdom en `node:20-alpine` con `fetch` simulado: cargar todos los
  scripts juntos en un único `<script>` (así comparten el ámbito global como en el navegador).
- Cambios de la API de Spotify para apps nuevas (nov. 2024): sin recomendaciones, audio-features ni previews, y las
  playlists creadas por Spotify devuelven 404. Tenerlo en cuenta antes de proponer funciones.
- **Migración de la API de Spotify (comprobado el 2026-09-28):** en las playlists el campo `tracks` pasa a `items`
  (`items.total`), `/playlists/{id}/tracks` da 403 -> usar `/playlists/{id}/items` (cada elemento trae la canción en
  `item`, no en `track`), y `/me/tracks/contains` da 403 -> `/me/library/contains?uris=`. `/me/tracks` (listar
  Tus me gusta), recently-played, top y search siguen igual. Las escrituras usan `spFirst` (JS) / `_first` (Python):
  primero la dirección nueva y, si Spotify la rechaza, la antigua. Las escrituras no se han probado contra la cuenta
  real para no modificarla.

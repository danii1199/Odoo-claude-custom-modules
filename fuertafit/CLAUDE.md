# Mi rutina Fuerta

Web personal (en español) que genera y planifica rutinas diarias a partir del catálogo de vídeos de FuertaFit
(suscripción del usuario). **Solo enlaza a los vídeos** (`https://webapp.fuertafit.com/#/post/{id}`); nunca se
descargan vídeos ni URLs de streaming.

## Arquitectura (MVC, paquete `app/`)

```
app/
  __main__.py      arranque (python -m app): scheduler + servidor
  config.py        rutas (DATA_DIR, catálogo, BD, estáticos), HOST, PORT
  server.py        http.server: estáticos de views/static + despacho de /api/* vía router
  router.py        @route(método, ruta), Request (query/body), HttpError
  scheduler.py     hilo: si autoPlan, rellena cada 30 min los días vacíos de la semana
  models/          MODELO (datos): db.py (Postgres: conexión con marcadores `?` y esquema), catalog.py, history.py, plans.py,
                   day_status.py (skipped/moved/away), settings.py
  services/        MODELO (negocio): generator.py (generate), planner.py (plan_week/plan_day),
                   calendar.py (mover, saltar, vacaciones), coach.py (bot IA, latente)
  controllers/     CONTROLADOR: *_controller.py registran rutas /api con @route
  views/           VISTA: serializers.py (JSON al navegador) y static/
                   (index.html, css/app.css, js/<pestaña>.js, sync.html, bookmarklet.js)
```

- `models.catalog`: carga la tabla `catalog` (JSONB por rutina) y clasifica cada rutina en un **grupo muscular** por palabras clave
  (`GROUP_RULES`). `CATALOG`/`BY_ID` se reasignan al recargar: úsalos siempre como `catalog.CATALOG`/`catalog.BY_ID`.
- Los modelos no importan servicios ni controladores; los controladores no tocan SQL.
- Frontend sin build: scripts clásicos que comparten ámbito global (`Hoy`, `Cal`, `Week`, `Cat`, `Bot`, `Sync`);
  `common.js` primero y `main.js` (menú por `#` y arranque) al final.
- `services/coach.py`: entrenador con Claude API. **Latente**: solo con `ANTHROPIC_API_KEY` en `.env`, y la pestaña
  "Entrenador" solo aparece entonces. El usuario **no quiere pagar API** aparte de su suscripción.
- `bookmarklet.js` + `sync.html`: marcador que, en webapp.fuertafit.com con la sesión del usuario, descarga solo
  rutinas nuevas y las envía vía `postMessage` a `sync.html` → `POST /api/catalog/import`.
- **Datos en Postgres (contenedor `postgres`, base de datos `rutinas`; ver `../postgres`)**: tablas `catalog`, `history`, `plan`, `settings`, `day_status`.
  `DATABASE_URL` en `.env` (fuera de git). El 2026-09-28 se perdió la antigua carpeta `data/` (SQLite) al recrearse el
  repo: por eso los datos viven ahora en el volumen Docker `postgres-datos`, fuera del repo.

## Ejecutar

Siempre con Docker (el sistema no tiene `python3-venv`; fuera de Docker no hay SDK de Anthropic, y no pasa nada):

```bash
sg docker -c "docker compose up -d --build"   # tras cambiar código (app/ va dentro de la imagen)
sg docker -c "docker compose logs --tail 20"
```

`sg docker` hace falta mientras la sesión no tenga el grupo `docker` activo. Ver la skill `docker-app`.

- Contenedor `fuertafit-rutinas`, `user: 1000:1000`, red Docker externa `proyectitos` (la crea `docker network create proyectitos`).
  Arranca después de `postgres`; si no está listo, reintenta la conexión ~1 min.
- Puerto `8000` publicado en toda la red local (`http://192.168.0.146:8000`). Sin autenticación: decisión del usuario.
- `TZ=Europe/Madrid` en la imagen: "hoy" depende de ello.

## Normas de trabajo

- **No tocar datos reales del usuario** (base de datos `rutinas`) sin pedirlo. Para probar usa
  fechas lejanas y límpialas después, o una base de datos de pruebas (`rutinas_test`, ver skill `probar-cambios`). Ver la skill `probar-cambios`.
- No restaurar ni recrear datos que el usuario haya borrado.
- Nada de funciones que requieran API de pago; preferir reglas deterministas.
- Código y textos de la interfaz en español, mismo estilo que el existente (comentarios breves, sin dependencias).
- Para actualizar el catálogo desde FuertaFit: skill `actualizar-catalogo`.

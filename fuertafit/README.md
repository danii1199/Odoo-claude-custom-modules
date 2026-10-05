# Mi rutina Fuerta

Generador de rutinas diarias a partir del catálogo de FuertaFit. Solo enlaza a los vídeos; no descarga nada.

## Arrancar con Docker

```bash
docker compose up -d --build
```

Necesita el contenedor `postgres` en marcha (`../postgres`, `docker compose up -d` allí primero) y un `.env` con
`DATABASE_URL` (ver `.env.example`). Abre http://localhost:8000. Los datos (catálogo, historial, calendario, ajustes)
viven en Postgres y se conservan aunque borres el contenedor o vuelvas a clonar el repo.

- Ver logs: `docker compose logs -f`
- Parar: `docker compose down`
- Tras cambiar código: `docker compose up -d --build`
- Tras cambiar `.env`: `docker compose up -d --force-recreate`

## Arrancar sin Docker

```bash
python3 -m app
```

Solo usa la librería estándar de Python. Variables opcionales: `HOST`, `PORT`, `DATA_DIR`.

## Entrenador con IA (opcional)

Copia `.env.example` a `.env`, pon tu `ANTHROPIC_API_KEY` y reinicia con `docker compose up -d`.
Sin clave todo funciona igual salvo el chat; la rutina automática diaria usa entonces el generador por reglas.
El modelo se cambia con `ANTHROPIC_MODEL` en `.env`.

## Estructura (MVC)

- `app/models/`: datos (Postgres). `app/services/`: lógica (generador, plan semanal, calendario, bot).
- `app/controllers/`: rutas `/api/*`. `app/views/`: JSON para la web y la web estática (`static/`).
- Datos: base de datos `rutinas` del contenedor `postgres` (volumen `postgres-datos`, fuera del repo).

Detalle en `CLAUDE.md`.

## Acceso desde la red local

El contenedor escucha en todas las interfaces: desde otro ordenador de la red entra en `http://IP-de-este-PC:8000`
(ahora mismo `http://192.168.0.146:8000`). Todos comparten calendario, historial y ajustes. No hay usuarios ni
contraseña: cualquiera de tu red puede usarla. Para limitarla a este ordenador, cambia el puerto en
`docker-compose.yml` a `"127.0.0.1:8000:8000"`.

## Actualizar el catálogo

Pestaña **Actualizar** de la web: arrastra el marcador «⟳ Actualizar Fuerta» a la barra de marcadores, abre
webapp.fuertafit.com con la sesión iniciada y púlsalo. Descarga solo las rutinas nuevas (con tu sesión, desde tu
navegador) y las envía a `/api/catalog/import`. El código del marcador está en `app/views/static/bookmarklet.js`.

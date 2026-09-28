# Mi rutina Fuerta

Generador de rutinas diarias a partir del catálogo de FuertaFit. Solo enlaza a los vídeos; no descarga nada.

## Arrancar con Docker

```bash
docker compose up -d --build
```

Abre http://localhost:8000. La carpeta `data/` se monta en el contenedor, así que el catálogo y el historial
se conservan aunque borres o reconstruyas el contenedor.

- Ver logs: `docker compose logs -f`
- Parar: `docker compose down`
- Tras cambiar código: `docker compose up -d --build`
- Tras sustituir `data/catalogo.json`: `docker compose restart`

## Arrancar sin Docker

```bash
python3 server.py
```

Solo usa la librería estándar de Python. Variables opcionales: `HOST`, `PORT`, `DATA_DIR`.

## Entrenador con IA (opcional)

Copia `.env.example` a `.env`, pon tu `ANTHROPIC_API_KEY` y reinicia con `docker compose up -d`.
Sin clave todo funciona igual salvo el chat; la rutina automática diaria usa entonces el generador por reglas.
El modelo se cambia con `ANTHROPIC_MODEL` en `.env`.

## Archivos

- `server.py`: servidor HTTP y tarea de rutina automática diaria.
- `core.py`: catálogo, generador, historial, calendario y ajustes.
- `bot.py`: entrenador (Claude + herramientas sobre el catálogo, historial y calendario).
- `static/index.html`: la web (Hoy, Calendario, Rutinas, Entrenador).
- `data/catalogo.json`: metadatos de las rutinas con vídeo.
- `data/historial.db`: SQLite con lo hecho, lo planificado y los ajustes (se crea sola).

## Acceso desde la red local

El contenedor escucha en todas las interfaces: desde otro ordenador de la red entra en `http://IP-de-este-PC:8000`
(ahora mismo `http://192.168.0.146:8000`). Todos comparten calendario, historial y ajustes. No hay usuarios ni
contraseña: cualquiera de tu red puede usarla. Para limitarla a este ordenador, cambia el puerto en
`docker-compose.yml` a `"127.0.0.1:8000:8000"`.

## Actualizar el catálogo

Pestaña **Actualizar** de la web: arrastra el marcador «⟳ Actualizar Fuerta» a la barra de marcadores, abre
webapp.fuertafit.com con la sesión iniciada y púlsalo. Descarga solo las rutinas nuevas (con tu sesión, desde tu
navegador) y las envía a `/api/catalog/import`. El código del marcador está en `static/bookmarklet.js`.

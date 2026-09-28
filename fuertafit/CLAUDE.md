# Mi rutina Fuerta

Web personal (en español) que genera y planifica rutinas diarias a partir del catálogo de vídeos de FuertaFit
(suscripción del usuario). **Solo enlaza a los vídeos** (`https://webapp.fuertafit.com/#/post/{id}`); nunca se
descargan vídeos ni URLs de streaming.

## Arquitectura

- `core.py`: todo lo que no es HTTP. Carga `data/catalogo.json`, clasifica cada rutina en un **grupo muscular**
  por palabras clave (`GROUP_RULES`: Calentamiento, Cuerpo-Mente, Core, Pierna y glúteo, Torso, Fullbody, Cardio),
  generador por reglas (`generate`), historial, calendario (`plan`), estados de día (`day_status`: skipped/moved/away),
  ajustes (`settings`, JSON por clave), plan semanal (`plan_week`, `plan_day`), buscador e importación del catálogo.
- `server.py`: `http.server` de la librería estándar. Rutas `/api/*` + estáticos de `static/`. Hilo que, si
  `autoPlan` está activo, rellena cada 30 min los días vacíos de la semana. Cabecera `Cache-Control: no-cache`.
- `bot.py`: entrenador con Claude API + herramientas. **Latente**: solo se activa con `ANTHROPIC_API_KEY` en `.env`,
  y la pestaña "Entrenador" solo aparece entonces. El usuario **no quiere pagar API** aparte de su suscripción.
- `static/index.html`: SPA sin build (hash routing): Hoy, Calendario, Plan semanal, Rutinas, [Entrenador], Actualizar.
- `static/bookmarklet.js` + `static/sync.html`: marcador que, ejecutado en webapp.fuertafit.com con la sesión del
  usuario, descarga solo rutinas nuevas y las envía vía `postMessage` a `sync.html` → `POST /api/catalog/import`.
- `data/` (montado en Docker, no versionar): `catalogo.json` (metadatos crudos, compacto) e `historial.db` (SQLite).

## Ejecutar

Siempre con Docker (el sistema no tiene `python3-venv`; fuera de Docker no hay SDK de Anthropic, y no pasa nada):

```bash
sg docker -c "docker compose up -d --build"   # tras cambiar código
sg docker -c "docker compose logs --tail 20"
```

`sg docker` hace falta mientras la sesión no tenga el grupo `docker` activo. Ver la skill `docker-app`.

- Contenedor `fuertafit-rutinas`, corre como `1000:1000` (si corre como root, `data/` queda con archivos de root).
- Puerto `8000` publicado en toda la red local (`http://192.168.0.146:8000`). Sin autenticación: decisión del usuario.
- `TZ=Europe/Madrid` en la imagen: "hoy" depende de ello.

## Normas de trabajo

- **No tocar datos reales del usuario** (`data/historial.db`, `data/catalogo.json`) sin pedirlo. Para probar usa
  fechas lejanas y límpialas después, o una copia en otro `DATA_DIR`. Haz copia antes de cualquier prueba que
  escriba el catálogo. Ver la skill `probar-cambios`.
- No restaurar ni recrear datos que el usuario haya borrado.
- Nada de funciones que requieran API de pago; preferir reglas deterministas.
- Código y textos de la interfaz en español, mismo estilo que el existente (comentarios breves, sin dependencias).
- Para actualizar el catálogo desde FuertaFit: skill `actualizar-catalogo`.

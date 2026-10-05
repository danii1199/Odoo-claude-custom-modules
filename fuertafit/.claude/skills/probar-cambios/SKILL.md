---
name: probar-cambios
description: Cómo probar cambios de Mi rutina Fuerta (generador, calendario, plan semanal, importación) sin estropear los datos reales del usuario. Úsala antes de cualquier prueba que escriba en el calendario, historial, ajustes o catálogo.
---

# Probar sin tocar los datos del usuario

Los datos reales están en la base de datos `rutinas` de Postgres (catálogo, historial, planes, estados de día, ajustes).
El usuario **no quiere que se restauren ni recreen** datos que haya borrado: deja sus datos como estén.

## 1. Lógica de Python: sobre una base de datos de pruebas

```bash
sg docker -c "docker exec postgres psql -U admin -c 'CREATE DATABASE rutinas_test OWNER rutinas'"
PW=$(grep '^RUTINAS_PASSWORD=' ../postgres/.env | cut -d= -f2-)   # no mostrarla
sg docker -c "docker compose build" && sg docker -c "docker run --rm --network proyectitos \
  -e DATABASE_URL=postgresql://rutinas:$PW@postgres:5432/rutinas_test -v <scratchpad>/t.py:/srv/t.py:ro \
  fuertafit-rutinas python /srv/t.py"
sg docker -c "docker exec postgres psql -U admin -c 'DROP DATABASE rutinas_test'"
```
En `t.py`: importar `app.models.catalog`, `app.services.generator`… (importa el catálogo de prueba con
`catalog.import_items([...])` primero).

## 2. En la web (Docker o navegador): fechas lejanas + limpieza

- Usa fechas de un mes futuro que el usuario no tenga planificado (mira antes
  `GET /api/plans?from=...&to=...` y **anota lo que ya existe**).
- Al terminar, borra solo lo tuyo:
  `POST /api/plan/remove {"day": ...}` y `POST /api/day/clear {"start": ..., "end": ...}`.
- Si cambias ajustes (`/api/settings`, p. ej. `dailyMinutes`), vuelve a poner el valor previo.
- Comprueba al final que lo que existía antes sigue igual.

## 3. Catálogo

`POST /api/catalog/import` escribe en la tabla `catalog` real. Pruébalo en `rutinas_test`, no contra la base real.

## 4. Navegador (Claude in Chrome)

- Tras `docker compose up -d --build` usa `location.reload()`; cambiar solo el `#` no recarga.
- No dispares `alert`/`confirm`: bloquean la extensión. `window.open` desde `javascript_tool` se bloquea como
  ventana emergente: crea un botón temporal y pulsa con `computer` (clic real).
- Si aparece "Cannot access a chrome-extension:// URL of different extension", otra extensión tapa la pestaña:
  no insistas, sigue con `curl` y avisa al usuario.
- Sin navegador, comprueba al menos la sintaxis del JS (no hay node en el sistema): copia `app/views/static/js/*.js`
  al scratchpad y ejecuta `sg docker -c "docker run --rm -v <scratchpad>:/c:ro node:20-alpine node --check /c/hoy.js"`.
  Concaténalos en orden de carga para detectar nombres declarados dos veces entre archivos.

## 5. Refactors: comparar la API antes y después

Arranca la versión vieja y la nueva con copias idénticas de los datos (dos bases de pruebas) y la misma semilla
(`PYTHONPATH` con un `sitecustomize.py` que haga `random.seed(12345)`), recorre la API con el mismo script
y compara las respuestas y el contenido final de las tablas. Así se validó el paso a MVC.
- Las funciones de los módulos están expuestas: `Hoy`, `Cal` (`select`, `move`, `skip`, `generate`), `Week`,
  `Cat`, `Sync`. Útiles para probar desde `javascript_tool`.

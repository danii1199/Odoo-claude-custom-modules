---
name: probar-cambios
description: Cómo probar cambios de Mi rutina Fuerta (generador, calendario, plan semanal, importación) sin estropear los datos reales del usuario. Úsala antes de cualquier prueba que escriba en el calendario, historial, ajustes o catálogo.
---

# Probar sin tocar los datos del usuario

Los datos reales están en `data/historial.db` (historial, planes, estados de día, ajustes) y `data/catalogo.json`.
El usuario **no quiere que se restauren ni recreen** datos que haya borrado: deja sus datos como estén.

## 1. Lógica de Python: sobre una copia

```bash
SP=<scratchpad>/t && mkdir -p $SP && cp data/catalogo.json $SP/ && rm -f $SP/historial.db
DATA_DIR=$SP python3 - <<'EOF'
import sys; sys.path.insert(0, '/media/dani/DANI-DATA/proyectitos/fuertafit')
import core          # DATA_DIR se lee al importar: define la variable antes
print(core.meta()['groups'])
print(core.generate({"minutes": 30, "groups": ["Cardio", "Core"], "seed": 1}))
print(core.plan_week('2026-11-02'))
EOF
```

## 2. En la web (Docker o navegador): fechas lejanas + limpieza

- Usa fechas de un mes futuro que el usuario no tenga planificado (mira antes
  `GET /api/plans?from=...&to=...` y **anota lo que ya existe**).
- Al terminar, borra solo lo tuyo:
  `POST /api/plan/remove {"day": ...}` y `POST /api/day/clear {"start": ..., "end": ...}`.
- Si cambias ajustes (`/api/settings`, p. ej. `dailyMinutes`), vuelve a poner el valor previo.
- Comprueba al final que lo que existía antes sigue igual.

## 3. Catálogo: copia de seguridad antes

`POST /api/catalog/import` reescribe `data/catalogo.json`. Antes: `cp data/catalogo.json <scratchpad>/catalogo.backup.json`.
Después: restaura, compara (`json.load` igual) y `sg docker -c "docker compose restart"`.

## 4. Navegador (Claude in Chrome)

- Tras `docker compose up -d --build` usa `location.reload()`; cambiar solo el `#` no recarga.
- No dispares `alert`/`confirm`: bloquean la extensión. `window.open` desde `javascript_tool` se bloquea como
  ventana emergente: crea un botón temporal y pulsa con `computer` (clic real).
- Si aparece "Cannot access a chrome-extension:// URL of different extension", otra extensión tapa la pestaña:
  no insistas, sigue con `curl` y avisa al usuario.
- Sin navegador, comprueba al menos la sintaxis del JS: extrae los `<script>` de `static/index.html` y
  `static/sync.html` a archivos en el scratchpad y ejecuta
  `sg docker -c "docker run --rm -v <scratchpad>:/c:ro node:20-alpine node --check /c/page.js"` (no hay node en el sistema).
- Las funciones de los módulos están expuestas: `Hoy`, `Cal` (`select`, `move`, `skip`, `generate`), `Week`,
  `Cat`, `Sync`. Útiles para probar desde `javascript_tool`.

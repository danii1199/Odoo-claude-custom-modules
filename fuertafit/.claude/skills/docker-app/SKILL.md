---
name: docker-app
description: Arrancar, reconstruir, reiniciar o revisar la web "Mi rutina Fuerta" en Docker (contenedor fuertafit-rutinas). Úsala tras cambiar código, para ver logs o cuando la web no responda en localhost:8000.
---

# Docker de Mi rutina Fuerta

Todo desde `/media/dani/DANI-DATA/proyectitos/claude-test/fuertafit` (repo git `claude-test`, rama `ruti-fuerta`). Envuelve los comandos en `sg docker -c "..."` porque la
sesión puede no tener aún el grupo `docker` activo (sin él da "permission denied").

| Qué | Comando |
|---|---|
| Aplicar cambios de código (`app/`) | `sg docker -c "docker compose up -d --build"` |
| Tras cambiar `.env` (`restart` no lo relee) | `sg docker -c "docker compose up -d --force-recreate"` |
| Estado | `sg docker -c "docker compose ps"` |
| Logs | `sg docker -c "docker compose logs --tail 30"` |
| Comprobar | `curl -s localhost:8000/api/meta \| head -c 200` |

## Detalles que ya dieron problemas

- `app/` (incluida la web en `app/views/static/`) va **dentro de la imagen**: cambiarla requiere `--build`, no basta `restart`.
- Tras reconstruir se pierden los logs del contenedor anterior; si necesitas auditar peticiones, míralos antes.
- Los datos están en Postgres (`../postgres`, contenedor `postgres`): tiene que estar arrancado antes. Red externa
  `proyectitos`. Copia de seguridad: `sg docker -c "docker exec postgres pg_dump -U admin rutinas" > rutinas.sql`.
- No uses `pkill -f "python3 -m app"`: el patrón coincide con tu propia shell y la mata (exit 144). Para
  pruebas sin Docker usa otro puerto y guarda el PID: `(PORT=8001 DATA_DIR=... python3 -m app & echo $! > pid)`.
- Puerto publicado en toda la LAN (`8000:8000`). IP actual del PC: `hostname -I` (era 192.168.0.146).
- En el navegador, `navigate` a la misma URL cambiando solo el `#` **no recarga** la página: usa
  `location.reload()` para ver el HTML nuevo.
- El bot (`app/services/coach.py`) solo se activa con `ANTHROPIC_API_KEY` en `.env` (`.env.example`). El usuario no quiere pagar
  API: no lo actives ni lo sugieras como necesario.

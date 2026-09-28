---
name: docker-app
description: Arrancar, reconstruir, reiniciar o revisar la web "Mi rutina Fuerta" en Docker (contenedor fuertafit-rutinas). Úsala tras cambiar código, para ver logs o cuando la web no responda en localhost:8000.
---

# Docker de Mi rutina Fuerta

Todo desde `/media/dani/DANI-DATA/proyectitos/fuertafit`. Envuelve los comandos en `sg docker -c "..."` porque la
sesión puede no tener aún el grupo `docker` activo (sin él da "permission denied").

| Qué | Comando |
|---|---|
| Aplicar cambios de código (`*.py`, `static/`) | `sg docker -c "docker compose up -d --build"` |
| Solo recargar datos (`catalogo.json`, `.env`) | `sg docker -c "docker compose restart"` |
| Estado | `sg docker -c "docker compose ps"` |
| Logs | `sg docker -c "docker compose logs --tail 30"` |
| Comprobar | `curl -s localhost:8000/api/meta \| head -c 200` |

## Detalles que ya dieron problemas

- `static/` va **dentro de la imagen** (COPY): cambiar el HTML requiere `--build`, no basta `restart`.
- Tras reconstruir se pierden los logs del contenedor anterior; si necesitas auditar peticiones, míralos antes.
- El contenedor corre como `user: "1000:1000"`. No lo quites: como root deja archivos de root en `data/`
  (si pasa, se pueden borrar y recrear porque la carpeta es del usuario).
- No uses `pkill -f "python3 server.py"`: el patrón coincide con tu propia shell y la mata (exit 144). Para
  pruebas sin Docker usa otro puerto: `HOST=0.0.0.0 PORT=8001 DATA_DIR=... timeout 4 python3 server.py`.
- Puerto publicado en toda la LAN (`8000:8000`). IP actual del PC: `hostname -I` (era 192.168.0.146).
- En el navegador, `navigate` a la misma URL cambiando solo el `#` **no recarga** la página: usa
  `location.reload()` para ver el HTML nuevo.
- El bot (`bot.py`) solo se activa con `ANTHROPIC_API_KEY` en `.env` (`.env.example`). El usuario no quiere pagar
  API: no lo actives ni lo sugieras como necesario.

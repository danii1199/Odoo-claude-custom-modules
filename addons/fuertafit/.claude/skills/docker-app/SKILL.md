---
name: docker-app
description: Aplicar cambios de código de Mi rutina Fuerta (módulo fuertafit) en el Odoo común, migrar datos de la web antigua o comprobar que /fuerta responde. Para todo lo demás de Docker usa la skill raíz odoo-docker.
---

# fuertafit en el Odoo común

Ya no hay contenedor propio (`fuertafit-rutinas`/`fuertafit-odoo` desaparecieron el 2026-10-05): el módulo se monta
desde `addons/fuertafit` (en `/mnt/extra-addons/fuertafit`) en el contenedor `odoo` de la raíz. Comandos desde la raíz y con `sg docker -c "..."`.

| Qué | Comando |
|---|---|
| Cambios en Python, XML, permisos o datos | `docker compose exec -T odoo odoo module upgrade -d claude-main fuertafit && docker compose restart odoo` |
| Solo estáticos (`static/web`) | nada: recarga el navegador (la versión `__V__` cambia sola) |
| Comprobar | `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/fuerta` (303 = pide login: bien) |
| Errores del módulo | `docker compose logs odoo --tail 80 \| grep -A15 -i "error\|traceback"` |

## Migrar desde la web antigua (base `rutinas`)

Solo si el usuario lo pide (escribe en `fuertafit`). Solo **lee** `rutinas`; si el usuario ya tiene historial/plan
en Odoo no duplica nada.

```bash
sg docker -c "docker compose exec -T -e MIGRAR_LOGIN=admin odoo odoo shell -d claude-main --no-http" \
    < addons/fuertafit/scripts/migrar_rutinas.py
```
`RUTINAS_DATABASE_URL` llega al contenedor desde `docker-compose.yml` (contraseña `RUTINAS_PASSWORD` del `.env`).

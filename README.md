# proyectitos

Odoo 20 Community con mis módulos propios. Postgres y Odoo comunes en Docker; cada proyecto es una carpeta de
`addons/` (los extra-addons): cada carpeta de `addons/` es un módulo.

| Proyecto | Módulo | Estado |
|---|---|---|
| [`addons/fuertafit`](addons/fuertafit) | `fuertafit` · Mi rutina Fuerta (web en el sitio web de Odoo, `/fuerta`) | ver su README |
| [`addons/menu_inicio`](addons/menu_inicio) | `menu_inicio` · pantalla de inicio con iconos de apps (estilo Enterprise) | instálalo en cada base |
| [`addons/myspoty`](addons/myspoty) | `myspoty` · reproductor de Spotify | pendiente de portar a Odoo |

## Arrancar

```bash
cp .env.example .env                 # y rellena las contraseñas (solo la primera vez)
docker network create proyectitos    # solo la primera vez
docker compose up -d
```

Odoo: http://localhost:8000 (o `http://IP-de-este-PC:8000` desde la red local).

## Bases de datos

- Gestor: http://localhost:8000/web/database/manager (crear, duplicar, copia de seguridad, restaurar, borrar), con la
  contraseña maestra `ODOO_MASTER_PASSWORD` del `.env`.
- Por consola: `docker compose exec odoo odoo db --help` y `docker compose exec odoo odoo module --help`.
- Los datos viven en los volúmenes Docker `postgres-datos` y `odoo-datos`, **fuera del repo**.
  ⚠️ `docker compose down -v` los borra.
- Copia de todo Postgres: `docker exec postgres pg_dumpall -U admin > ../copias-seguridad/todo.sql`

## Cambios de código

- Python/XML de un módulo: `docker compose exec odoo odoo module upgrade -d <base> <modulo>` y `docker compose restart odoo`.
- `Dockerfile` u `odoo-entrypoint.sh`: `docker compose up -d --build`. `.env`: `docker compose up -d --force-recreate`.
- Módulo nuevo: crea `addons/<modulo>/` con su `__manifest__.py` y `docker compose restart odoo`.

Detalle para Claude en `CLAUDE.md` y en `.claude/skills/`; cada proyecto tiene además los suyos.

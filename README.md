# proyectitos

Odoo 20 Community con mis módulos propios. Postgres y Odoo comunes en Docker; cada proyecto es una carpeta de
`addons/` (los extra-addons): cada carpeta de `addons/` es un módulo.

| Proyecto | Módulo | Estado |
|---|---|---|
| [`addons/fuertafit`](addons/fuertafit) | `fuertafit` · Mi rutina Fuerta (web en el sitio web de Odoo, `/fuerta`) | ver su README |
| [`addons/dbd`](addons/dbd) | `dbd` · enciclopedia de Dead by Daylight (web `/dbd`, catálogo importado de fuentes públicas) | ver su README |
| [`addons/menu_inicio`](addons/menu_inicio) | `menu_inicio` · pantalla de inicio con iconos de apps (estilo Enterprise) | instálalo en cada base |
| [`addons/myspoty`](addons/myspoty) | `myspoty` · reproductor de Spotify | pendiente de portar a Odoo |

## Instalar (en este PC o en otro)

`instalar.sh` lo hace **todo** en un Linux Mint / Ubuntu recién instalado: git, Docker y Compose, Claude Code, el
repo en `~/proyectitos/claude-test`, `.env` con contraseñas al azar, Odoo y Postgres, y restaura las copias. Se puede
repetir sin miedo: no sobrescribe `.env`, el repo ni una base que ya exista.

### Llevarlo a otro PC

1. En este PC: `./preparar-mudanza.sh` (o `./preparar-mudanza.sh claude-main claude-test` para varias bases).
   Crea `../mudanza-<fecha>/` con la copia de las bases (base + adjuntos), el repo tal cual (historial de git y
   cambios sin subir, sin `.env`), tus ajustes de Claude y el instalador. Cópiala a un USB: son **datos reales**,
   no la subas a ningún sitio público.
2. En el PC nuevo: `bash /ruta/al/usb/mudanza-<fecha>/instalar.sh` (pide la contraseña de sudo).
3. Odoo en http://localhost:8000 con tu usuario de siempre. Claude: terminal nueva, `cd ~/proyectitos/claude-test && claude`
   (la primera vez, iniciar sesión). La contraseña maestra del gestor de bases es nueva: `ODOO_MASTER_PASSWORD` en el `.env`.

Sin carpeta de mudanza, `instalar.sh` clona el repo de GitHub; una copia suelta se restaura con
`./instalar.sh ../copias-seguridad/<base>-<fecha>.zip [nombre-base]`.

## Contraseñas (.env)

`./ajustar-env.sh` muestra qué claves tienen valor; `./ajustar-env.sh ODOO_MASTER_PASSWORD --preguntar` la cambia
(sin `--preguntar`, al azar). Las de Postgres se cambian también dentro de Postgres; no edites el `.env` a mano.

## Bases de datos

- Gestor: http://localhost:8000/web/database/manager (crear, duplicar, copia de seguridad, restaurar, borrar), con la
  contraseña maestra `ODOO_MASTER_PASSWORD` del `.env`.
- Por consola: `docker compose exec odoo odoo db --help` y `docker compose exec odoo odoo module --help`.
- Los datos viven en los volúmenes Docker `postgres-datos` y `odoo-datos`, **fuera del repo**.
  ⚠️ `docker compose down -v` los borra.
- Copia de una base: `./copia-seguridad.sh [base]` (por defecto `claude-main`).
- Copia de todo Postgres: `docker exec postgres pg_dumpall -U admin > ../copias-seguridad/todo.sql`

## Cambios de código

- Python/XML de un módulo: `docker compose exec odoo odoo module upgrade -d <base> <modulo>` y `docker compose restart odoo`.
- `Dockerfile` u `odoo-entrypoint.sh`: `docker compose up -d --build`. `.env`: `docker compose up -d --force-recreate`.
- Módulo nuevo: crea `addons/<modulo>/` con su `__manifest__.py` y `docker compose restart odoo`.

Detalle para Claude en `CLAUDE.md` y en `.claude/skills/`; cada proyecto tiene además los suyos.

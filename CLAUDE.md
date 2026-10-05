# proyectitos (repo `claude-test`)

Un **Odoo 20 Community** común donde el usuario va añadiendo sus propios módulos. Cada proyecto es una carpeta de
`addons/` (los extra-addons) que **es el propio módulo** (`__manifest__.py`, `models/`… directamente dentro), su propia memoria (`addons/<proyecto>/CLAUDE.md`) y sus propias
skills (`addons/<proyecto>/.claude/skills`).
Postgres y Docker son **comunes** y viven en la raíz. Todo en español: código, comentarios, interfaz y documentación.

## Estructura

```
docker-compose.yml     servicios `postgres` (16) y `odoo` (20), proyecto Compose `proyectitos`
Dockerfile             FROM odoo:20 + dependencias Python de los módulos (el código NO va en la imagen)
odoo-entrypoint.sh     genera /etc/odoo/odoo.conf: odoo.conf + addons_path + admin_passwd, y lanza el entrypoint oficial
odoo.conf              configuración de Odoo sin secretos (montada como /etc/odoo/odoo.base.conf)
.env / .env.example    contraseñas (fuera de git): Postgres, rol `odoo`, contraseña maestra, ANTHROPIC_API_KEY opcional
postgres/init/         script de la primera vez: roles `odoo` (CREATEDB) y `rutinas`, bases `fuertafit` y `rutinas`
addons/                extra-addons: cada carpeta es un módulo (nombre técnico = nombre de la carpeta)
  fuertafit/           módulo `fuertafit` (Mi rutina Fuerta, web en el sitio web de Odoo) + scripts/, CLAUDE.md, skills
  menu_inicio/         módulo `menu_inicio`: pantalla de inicio con cuadrícula de apps (estilo Enterprise, código propio)
  myspoty/             futuro módulo `myspoty` (aún sin manifest; app antigua en app/), CLAUDE.md y skills
```

- `addons/` se monta **en solo lectura** en `/mnt/extra-addons`. `odoo-entrypoint.sh` mete en `addons_path` cada
  `addons_path` `/mnt/extra-addons` en cuanto hay algún módulo: uno nuevo no necesita tocar `docker-compose.yml`, y una
  carpeta sin `__manifest__.py` (como `myspoty` ahora) simplemente se ignora.
- Dentro del módulo pueden ir `scripts/`, `CLAUDE.md`, `.claude/`…: Odoo solo carga lo que importa el manifest.
- Al trabajar en un proyecto, lee su `CLAUDE.md` y usa sus skills (se cargan solas al tocar archivos de esa carpeta).

## Docker (skill `odoo-docker`)

- Siempre `sg docker -c "..."` (la sesión puede no tener aún el grupo `docker`) y desde la raíz del repo.
- Contenedores `postgres` y `odoo`; red externa `proyectitos`; volúmenes `postgres-datos` (bases de datos) y
  `odoo-datos` (filestore y sesiones). Están **fuera del repo**: clonar o limpiar no los toca.
  Compose avisa de que los volúmenes "were created for project postgres/fuertafit": es normal, se crearon antes de
  unificar (2026-10-05). **No** pongas `external: true` ni los borres.
- Odoo en `http://IP-de-este-PC:8000` (toda la red local, decisión del usuario). Postgres solo en `127.0.0.1:5432`.
- Cambiar código Python o XML de un módulo: `restart` + actualizar el módulo en su base de datos (no hace falta `--build`).
  `--build` si cambian `Dockerfile` u `odoo-entrypoint.sh` (van dentro de la imagen). Cambiar `.env`: `up -d --force-recreate`.

## Bases de datos (skill `odoo-bases-de-datos`)

- Multi-base: `list_db = True`, selector en `/web/login` y gestor en `/web/database/manager`, protegido por la
  contraseña maestra (`ODOO_MASTER_PASSWORD` en `.env`; **no la muestres**). Odoo solo lista las bases cuyo dueño es `odoo`.
- Por consola: `odoo db {init,duplicate,dump,load,rename,drop}` y `odoo module {install,upgrade,uninstall,list}`
  dentro del contenedor (`docker compose exec -T odoo odoo ...`). Gestionan también el filestore.
- Bases actuales: `fuertafit` (Odoo, **datos reales** del usuario) y `rutinas` (web antigua de fuertafit, solo para
  migrar). La de la app antigua de myspoty ya no importa al usuario (2026-10-05).
- En Odoo 20 el servicio `db` de `/jsonrpc` ya no existe: usa el gestor web o el CLI.

## Odoo 20: convenciones de los módulos (ver `addons/fuertafit` como ejemplo)

- Manifest: `version` `20.0.x.y.z`, `author` `danii1199`, `license` `LGPL-3`, `depends` mínimo.
- Permisos en `security/ir.access.csv` (modelo `ir.access`, nuevo en 20): columnas
  `id,name,model_id,group_id/id,operation,domain`; `operation` tipo `r`/`crud`; el dominio sustituye a las `ir.rule`.
- Restricciones SQL con `models.Constraint("UNIQUE (...)", "mensaje")` (no `_sql_constraints`).
- Campos Binary: el valor es un `BinaryValue` (`.decode()`, `.content`), no base64; al escribir, str base64 o BinaryValue.
- Botones de cabecera en listas: `<header><button ... display="always"/></header>`. URLs de backend: `/odoo/action-<xmlid>`.
- JS del backend (OWL 3): `proxy`/`signal` en vez de `useState`/`reactive`, **sin `static props`** (rompe todo el
  webclient), refs con `signal.ref()`, iconos `<i class="oi" data-icon="..."/>`. Detalles en `addons/menu_inicio/CLAUDE.md`.
- Páginas web: `http.route(..., website=True)` + plantilla con `t-call="website.layout"` y zonas `oe_structure`
  editables; CSS propio siempre con prefijo (Bootstrap del sitio usa `.row`, `header`, `nav`, `main`…).
- Vistas `<list>` (no `<tree>`), `invisible="expr"` (no `attrs`). `ir.config_parameter`: `get_str`/`set_str`.
- Tareas periódicas con `ir.cron` en `data/` (`max_cron_threads = 1`). Fechas de "hoy" en `Europe/Madrid` (TZ del contenedor).
- Ante la duda sobre una API de Odoo 20, mira el código real del contenedor:
  `docker compose exec -T odoo grep -rn ... /usr/lib/python3/dist-packages/odoo` en vez de suponer por versiones anteriores.

## Normas

- **No tocar datos reales** (base `fuertafit`) sin pedirlo: prueba en una copia (skill `probar-modulo`).
  Nunca borres, restaures ni sobrescribas una base de datos o volumen sin confirmación explícita.
- No leer ni mostrar `.env`, contraseñas ni tokens. Para usar un valor: `grep '^X=' .env | cut -d= -f2-` dentro de un comando.
- Nada de funciones que obliguen a pagar APIs (el usuario no quiere); preferir reglas deterministas.
- Nuevo proyecto o módulo: skill `nuevo-modulo` (carpeta, montaje, CLAUDE.md y skills propias).
- Sin node ni venv en el sistema: lo que haga falta, en contenedores (`node:20-alpine`, la propia imagen de Odoo).

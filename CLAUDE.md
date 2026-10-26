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
instalar.sh            instala TODO en un Mint/Ubuntu vacío (apt: git, Docker; Claude Code; repo; .env al azar; up; copias .zip)
preparar-mudanza.sh    ../mudanza-<fecha>/: copias de bases + repo en tar.gz (sin .env) + ajustes de Claude + instalar.sh
ajustar-env.sh         cambia una clave del .env sin mostrarla (+ ALTER ROLE en Postgres y recrear contenedores)
copia-seguridad.sh     copia de una base (por defecto claude-main) en ../copias-seguridad/<base>-<fecha>.zip
odoo.conf              configuración de Odoo sin secretos (montada como /etc/odoo/odoo.base.conf)
.env / .env.example    contraseñas (fuera de git): Postgres, rol `odoo`, contraseña maestra, ANTHROPIC_API_KEY opcional
postgres/init/         script de la primera vez: roles `odoo` (CREATEDB) y `rutinas`, base `rutinas`
addons/                extra-addons: cada carpeta es un módulo (nombre técnico = nombre de la carpeta)
  fuertafit/           módulo `fuertafit` (Mi rutina Fuerta, web en el sitio web de Odoo) + scripts/, CLAUDE.md, skills
  dbd/                 módulo `dbd` (enciclopedia de Dead by Daylight, web /dbd), separado de fuertafit
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
  Desde otros equipos, por Tailscale con HTTPS (`sudo tailscale serve --bg 8000`, `proxy_mode = True`): sin HTTPS,
  fuera de `localhost`, el backend de Odoo 20 se queda en blanco (contexto no seguro).
- `restart: unless-stopped`: Postgres y Odoo arrancan solos al encender el PC (salvo que se paren a mano).
- Si se recrea la carpeta `addons/` (reestructurar, clonar de nuevo…), el contenedor sigue viendo la antigua
  (`/mnt/extra-addons` vacío): `restart odoo`.
- Cambiar código Python o XML de un módulo: `restart` + actualizar el módulo en su base de datos (no hace falta `--build`).
  `--build` si cambian `Dockerfile` u `odoo-entrypoint.sh` (van dentro de la imagen). Cambiar `.env`: `up -d --force-recreate`.

## Bases de datos (skill `odoo-bases-de-datos`)

- Multi-base: `list_db = True`, selector en `/web/login` y gestor en `/web/database/manager`, protegido por la
  contraseña maestra (`ODOO_MASTER_PASSWORD` en `.env`; **no la muestres**). Odoo solo lista las bases cuyo dueño es `odoo`.
- Por consola: `odoo db {init,duplicate,dump,load,rename,drop}` y `odoo module {install,upgrade,uninstall,list}`
  dentro del contenedor (`docker compose exec -T odoo odoo ...`). Gestionan también el filestore.
- Bases actuales (2026-10-05): `claude-main` (la principal, con fuertafit, menu_inicio y dbd con el catálogo completo: **datos reales**),
  `claude-test` (pruebas del usuario: fuertafit, menu_inicio y dbd con el catálogo completo) y `rutinas` (web
  antigua de fuertafit, solo para migrar). La base `fuertafit` ya no existe. La de la app antigua de myspoty ya no
  importa al usuario.
- En Odoo 20 el servicio `db` de `/jsonrpc` ya no existe: usa el gestor web o el CLI.

## Odoo 20: convenciones de los módulos (ver `addons/fuertafit` como ejemplo)

- Manifest: `version` `20.0.x.y.z`, `author` `danii1199`, `license` `LGPL-3`, `depends` mínimo.
- Permisos en `security/ir.access.csv` (modelo `ir.access`, nuevo en 20): columnas
  `id,name,model_id,group_id/id,operation,domain`; `model_id` es el nombre del modelo (`fuerta.routine`, no
  `model_fuerta_routine`); `operation` tipo `r`/`crud`; el dominio sustituye a las `ir.rule`.
- QWeb: un `t-call` solo pasa los valores del render y sus atributos (`<t t-call="x" rec="c"/>`); un `t-set` dentro
  del cuerpo del `t-call` **no** llega a la plantilla llamada (tampoco `additional_title` a `website.layout`).
- **Acceso por módulo**: cada módulo tiene su grupo en `security/groups.xml` (`ir.module.category` +
  `res.groups.privilege` + `res.groups` que implica `base.group_user`, con `user_ids` = `base.user_admin`, que es Dani).
  `ir.access.csv`, el menú raíz (`groups=`), las rutas web privadas (`has_group`) y el menú del sitio web usan ese
  grupo; así un usuario nuevo no ve nada hasta que se le da acceso en Ajustes → Usuarios. Odoo copia cada
  `website.menu` por sitio web: para cambiarle los grupos, escribe en todas las copias (busca por `manual_url`).
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

- **No tocar datos reales** (base `claude-main`) sin pedirlo: prueba en una copia (skill `probar-modulo`).
  Nunca borres, restaures ni sobrescribas una base de datos o volumen sin confirmación explícita.
- No leer ni mostrar `.env`, contraseñas ni tokens; para cambiarlos, skill `ajustar-env`. Para usar un valor: `grep '^X=' .env | cut -d= -f2-` dentro de un comando.
- Nada de funciones que obliguen a pagar APIs (el usuario no quiere); preferir reglas deterministas.
- Nuevo proyecto o módulo: skill `nuevo-modulo` (carpeta, montaje, CLAUDE.md y skills propias).
- Sin node ni venv en el sistema: lo que haga falta, en contenedores (`node:20-alpine`, la propia imagen de Odoo).

---
name: ajustar-env
description: Cambiar valores de ~/servicios/.env (contraseñas de Postgres y del rol odoo, contraseña maestra del gestor de bases de datos, ANTHROPIC_API_KEY) sin mostrarlos, aplicándolos también en Postgres y recreando los contenedores. Úsala cuando el usuario quiera cambiar, regenerar, poner o revisar una contraseña o clave del .env, o tras instalar en un PC nuevo.
---

# Ajustar el .env

Todo con `~/servicios/ajustar-env.sh` (con `sg docker -c "..."` si la sesión no tiene el grupo docker). El `.env` vive
en `~/servicios/.env` (fuera de git; `postgres/` y `odoo/` lo enlazan). **Nunca** leas ni muestres `.env` ni los valores: el script no los imprime.

| Qué | Orden |
|---|---|
| Ver qué claves tienen valor (sin valores) | `~/servicios/ajustar-env.sh` |
| Valor nuevo al azar | `~/servicios/ajustar-env.sh <CLAVE>` |
| Valor elegido por el usuario | que lo ejecute él: `! ~/servicios/ajustar-env.sh <CLAVE> --preguntar` (lo pide oculto) |
| Vaciar una clave opcional | `~/servicios/ajustar-env.sh ANTHROPIC_API_KEY --borrar` |

Claves (las de `~/servicios/.env.example`): `POSTGRES_PASSWORD` (superusuario `admin`), `ODOO_PASSWORD` (rol `odoo`),
`RUTINAS_PASSWORD` (rol `rutinas`), `ODOO_MASTER_PASSWORD` (gestor `/web/database/manager`), `ANTHROPIC_API_KEY`.

## Qué hace y por qué

- Las tres contraseñas de Postgres solo se leen del `.env` al crear el volumen `postgres-datos`: cambiarlas solo en el
  `.env` rompe la conexión de Odoo. El script hace antes `ALTER ROLE` en Postgres (necesita el contenedor arrancado).
- Después escribe el `.env` (permisos 600) y hace `./servicios.sh recrear postgres odoo`.
- Tras cambiar la contraseña maestra, dile al usuario que la nueva está en `ODOO_MASTER_PASSWORD` del `.env`; si la
  pide expresamente: `grep '^ODOO_MASTER_PASSWORD=' ~/servicios/.env | cut -d= -f2-` (solo entonces y sin guardarla en archivos).
- Si el usuario quiere elegir la contraseña, no se la pidas por el chat: que use `--preguntar` con `!`.
- `ANTHROPIC_API_KEY` es de pago y el usuario no quiere APIs de pago: no la pongas por iniciativa propia; además
  haría falta descomentar el SDK en el `Dockerfile` y `~/servicios/servicios.sh build odoo`.
- Las contraseñas de los usuarios de Odoo (tu login) no están en el `.env`: se cambian en Odoo (Preferencias / Ajustes → Usuarios).

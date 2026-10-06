#!/bin/sh
# Solo se ejecuta la primera vez (con el volumen vacío). Las bases de datos de Odoo las crea Odoo (rol `odoo`, CREATEDB)
# desde su gestor; aquí solo los roles y la base `fuertafit` y la base antigua `rutinas` (web de fuertafit antes de Odoo, para migrar).
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<SQL
CREATE ROLE odoo LOGIN CREATEDB PASSWORD '$ODOO_PASSWORD';
CREATE DATABASE fuertafit OWNER odoo;
CREATE ROLE rutinas LOGIN PASSWORD '$RUTINAS_PASSWORD';
CREATE DATABASE rutinas OWNER rutinas;
REVOKE ALL ON DATABASE fuertafit FROM PUBLIC;
REVOKE ALL ON DATABASE rutinas FROM PUBLIC;
SQL

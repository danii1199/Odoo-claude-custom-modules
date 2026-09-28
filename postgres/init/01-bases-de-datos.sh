#!/bin/sh
# Solo se ejecuta la primera vez (con el volumen vacío): un usuario y una base de datos por proyecto.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<SQL
CREATE ROLE rutinas LOGIN PASSWORD '$RUTINAS_PASSWORD';
CREATE DATABASE rutinas OWNER rutinas;
CREATE ROLE myspoty LOGIN PASSWORD '$MYSPOTY_PASSWORD';
CREATE DATABASE myspoty OWNER myspoty;
REVOKE ALL ON DATABASE rutinas FROM PUBLIC;
REVOKE ALL ON DATABASE myspoty FROM PUBLIC;
SQL

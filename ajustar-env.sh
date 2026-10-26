#!/bin/bash
# Ajusta un valor del .env sin mostrarlo y lo aplica donde haga falta:
#  - contraseñas de Postgres (POSTGRES_PASSWORD, ODOO_PASSWORD, RUTINAS_PASSWORD): también con ALTER ROLE, porque
#    Postgres solo lee las del .env al crear el volumen; si no, Odoo dejaría de conectar
#  - después recrea los contenedores (docker compose up -d --force-recreate) para que lean el .env nuevo
#
#   ./ajustar-env.sh                              qué claves hay y si tienen valor (sin mostrarlos)
#   ./ajustar-env.sh ODOO_MASTER_PASSWORD         valor nuevo al azar
#   ./ajustar-env.sh ODOO_MASTER_PASSWORD --preguntar   lo escribes tú (no se ve ni queda en el historial)
#   ./ajustar-env.sh ANTHROPIC_API_KEY --borrar   dejarla vacía
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "No hay .env: ejecuta ./instalar.sh primero" >&2; exit 1; }

if [ $# -eq 0 ]; then
    echo "Claves del .env (sin valores):"
    grep -E '^#? ?[A-Z_]+=' .env.example | sed -E 's/^# ?//; s/=.*//' | while read -r clave; do
        if grep -qE "^$clave=.+" .env; then echo "  $clave: con valor"; else echo "  $clave: vacía"; fi
    done
    exit 0
fi

clave="$1"
modo="${2:-}"
grep -qE "^#? ?$clave=" .env.example || { echo "Clave desconocida: $clave (mira .env.example)" >&2; exit 1; }

case "$modo" in
    "")          valor="$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 || true)" ;;
    --preguntar) read -rsp "Nuevo valor de $clave: " valor; echo
                 read -rsp "Repítelo: " otra; echo
                 [ "$valor" = "$otra" ] || { echo "No coinciden; no cambio nada." >&2; exit 1; }
                 [ -n "$valor" ] || { echo "Vacío; para vaciarla usa --borrar." >&2; exit 1; } ;;
    --borrar)    valor="" ;;
    *)           echo "Opción desconocida: $modo (usa --preguntar o --borrar)" >&2; exit 1 ;;
esac

# Contraseñas de roles de Postgres: primero dentro de Postgres (con el contenedor aún con la configuración vieja)
case "$clave" in
    POSTGRES_PASSWORD) rol=admin ;;
    ODOO_PASSWORD)     rol=odoo ;;
    RUTINAS_PASSWORD)  rol=rutinas ;;
    *)                 rol="" ;;
esac
if [ -n "$rol" ]; then
    [ -n "$valor" ] || { echo "Una contraseña de Postgres no puede quedar vacía." >&2; exit 1; }
    if docker compose ps --status running --services 2>/dev/null | grep -qx postgres; then
        printf '%s' "$valor" | docker compose exec -T postgres sh -c \
            'pw="$(cat)"; psql -v ON_ERROR_STOP=1 -q -U admin -v rol="$1" -v pw="$pw" <<SQL
ALTER ROLE :"rol" PASSWORD :'"'"'pw'"'"';
SQL' sh "$rol"
        echo "Contraseña del rol '$rol' cambiada en Postgres."
    else
        echo "Aviso: Postgres no está arrancado; solo cambio el .env (arráncalo y repite si el volumen ya existía)." >&2
    fi
fi

# .env: sustituye la línea (o la descomenta, o la añade) sin pasar el valor por sed
umask 077
CLAVE="$clave" VALOR="$valor" awk '
    BEGIN { hecho = 0 }
    $0 ~ "^#? ?" ENVIRON["CLAVE"] "=" && !hecho { print ENVIRON["CLAVE"] "=" ENVIRON["VALOR"]; hecho = 1; next }
    { print }
    END { if (!hecho) print ENVIRON["CLAVE"] "=" ENVIRON["VALOR"] }
' .env > .env.nuevo
mv .env.nuevo .env
echo "$clave actualizada en .env."

docker compose up -d --force-recreate
echo "Contenedores recreados con el .env nuevo."

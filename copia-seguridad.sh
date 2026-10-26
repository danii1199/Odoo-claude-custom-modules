#!/bin/bash
# Copia de seguridad de una base de Odoo (base + adjuntos del filestore) en ../copias-seguridad/<base>-<fecha>.zip,
# fuera del repo. Se restaura con ./instalar.sh <archivo.zip> o desde /web/database/manager.
#
#   ./copia-seguridad.sh                 copia de claude-main
#   ./copia-seguridad.sh claude-test     copia de otra base
set -euo pipefail
cd "$(dirname "$0")"

base="${1:-claude-main}"
destino="../copias-seguridad/$base-$(date +%F).zip"
mkdir -p ../copias-seguridad

docker compose exec -T odoo odoo db dump "$base" /tmp/copia.zip
docker compose cp odoo:/tmp/copia.zip "$destino"
docker compose exec -T odoo rm -f /tmp/copia.zip
echo "Copia: $(realpath "$destino") ($(du -h "$destino" | cut -f1))"

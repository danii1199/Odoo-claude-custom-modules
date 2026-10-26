#!/bin/bash
# Prepara una carpeta para llevarlo todo a otro PC (cópiala a un USB): copia de las bases, el repo tal cual
# (con su historial de git y los cambios sin subir; sin .env), tus ajustes de Claude y el instalador.
# En el PC nuevo basta con: bash <carpeta>/instalar.sh
#
#   ./preparar-mudanza.sh                          claude-main en ../mudanza-<fecha>/
#   ./preparar-mudanza.sh claude-main claude-test  varias bases
set -euo pipefail
cd "$(dirname "$0")"

bases=("$@")
[ ${#bases[@]} -gt 0 ] || bases=(claude-main)
fecha="$(date +%F)"
destino="$(realpath -m "../mudanza-$fecha")"
mkdir -p "$destino"

for base in "${bases[@]}"; do
    echo "==> Copia de la base '$base'"
    ./copia-seguridad.sh "$base"
    cp "../copias-seguridad/$base-$fecha.zip" "$destino/"
done

echo "==> Repo"
tar --exclude=./.env --exclude=__pycache__ -czf "$destino/claude-test.tar.gz" .
cp instalar.sh "$destino/"
[ -f "$HOME/.claude/settings.json" ] && cp "$HOME/.claude/settings.json" "$destino/claude-settings.json"

cat > "$destino/LEEME.txt" <<'FIN'
Mudanza del Odoo común (proyectitos) a otro PC con Linux Mint / Ubuntu.

1. Copia esta carpeta al PC nuevo (o déjala en el USB).
2. Abre una terminal y ejecuta:   bash /ruta/a/esta/carpeta/instalar.sh
   Pedirá tu contraseña de sudo. Instala git, Docker, Claude Code, el repo en ~/proyectitos/claude-test,
   Odoo y Postgres, y restaura las bases de datos de los .zip de esta carpeta.
3. Odoo: http://localhost:8000 con tu usuario de siempre.
   Claude: en una terminal nueva, cd ~/proyectitos/claude-test && claude (la primera vez, iniciar sesión).

Los .zip son tus datos reales: no los subas a ningún sitio público.
FIN

echo
echo "Carpeta de mudanza: $destino"
ls -lh "$destino"

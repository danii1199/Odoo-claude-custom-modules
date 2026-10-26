#!/bin/bash
# Instala TODO en un PC con Linux Mint / Ubuntu recién instalado (y se puede repetir sin miedo en uno ya montado):
#   1. git, curl, Docker y Compose (con apt) y tu usuario en el grupo `docker`
#   2. Claude Code (y tus ajustes de Claude, si vienen en la carpeta de mudanza)
#   3. el repo en ~/proyectitos/claude-test (de la carpeta de mudanza o, si no está, de GitHub)
#   4. .env con contraseñas al azar, red de Docker, imagen y contenedores de Postgres y Odoo
#   5. las copias de bases de datos (.zip): las que vengan en la carpeta de mudanza o la que se le pase
#
#   bash /media/<usb>/mudanza/instalar.sh             desde la carpeta que genera preparar-mudanza.sh
#   ./instalar.sh                                     dentro del repo: solo instalar y arrancar
#   ./instalar.sh ../copias-seguridad/claude-main-2026-10-26.zip [nombre-base]   + restaurar esa copia
#
# Otra carpeta de destino: DESTINO=/otra/ruta bash instalar.sh
set -euo pipefail

origen="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="${DESTINO:-$HOME/proyectitos/claude-test}"
REPO_URL=https://github.com/danii1199/Odoo-claude-custom-modules.git

paso() { echo; echo "==> $*"; }
falla() { echo "ERROR: $*" >&2; exit 1; }

copia="${1:-}"
nombre="${2:-}"
if [ -n "$copia" ]; then
    [ -f "$copia" ] || falla "No existe la copia: $copia"
    copia="$(realpath "$copia")"
fi

# --- 1. Sistema: git, curl, Docker -------------------------------------------------------------------------------
paso "Paquetes del sistema"
command -v apt-get > /dev/null || falla "Este script es para Linux Mint / Ubuntu / Debian (apt)."
faltan=()
command -v git > /dev/null || faltan+=(git)
command -v curl > /dev/null || faltan+=(curl)
command -v docker > /dev/null || faltan+=(docker.io)
docker compose version > /dev/null 2>&1 || faltan+=(docker-compose-v2)
if [ ${#faltan[@]} -gt 0 ]; then
    echo "Instalando: ${faltan[*]} (pedirá tu contraseña de sudo)"
    sudo apt-get update
    sudo apt-get install -y "${faltan[@]}"
else
    echo "git, curl, Docker y Compose ya están."
fi
systemctl is-active -q docker 2>/dev/null || sudo systemctl enable --now docker || echo "Aviso: no se pudo arrancar el servicio docker"
if ! getent group docker | grep -qw "$USER"; then
    sudo usermod -aG docker "$USER"
    echo "Añadido $USER al grupo docker (del todo efectivo al volver a iniciar sesión)."
fi

# --- 2. Claude Code ----------------------------------------------------------------------------------------------
paso "Claude Code"
export PATH="$HOME/.local/bin:$PATH"
if command -v claude > /dev/null; then
    echo "Ya está: $(claude --version 2>/dev/null || echo claude)"
else
    curl -fsSL https://claude.ai/install.sh | bash
fi
grep -qs '.local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
if [ -f "$origen/claude-settings.json" ] && [ ! -f "$HOME/.claude/settings.json" ]; then
    mkdir -p "$HOME/.claude"
    cp "$origen/claude-settings.json" "$HOME/.claude/settings.json"
    echo "Copiados tus ajustes de Claude (~/.claude/settings.json)."
fi

# --- 3. Repo -----------------------------------------------------------------------------------------------------
paso "Repo"
if [ -f "$origen/docker-compose.yml" ]; then
    repo="$origen"
elif [ -f "$DESTINO/docker-compose.yml" ]; then
    repo="$DESTINO"
    echo "Ya existe en $repo: no lo toco."
elif [ -f "$origen/claude-test.tar.gz" ]; then
    mkdir -p "$DESTINO"
    tar -xzf "$origen/claude-test.tar.gz" -C "$DESTINO"
    repo="$DESTINO"
    echo "Repo copiado de la carpeta de mudanza en $repo (con su historial de git)."
else
    mkdir -p "$(dirname "$DESTINO")"
    git clone "$REPO_URL" "$DESTINO"
    repo="$DESTINO"
fi
repo="$(realpath "$repo")"

# Copias a restaurar: la indicada o las de la carpeta de mudanza (se guardan en ../copias-seguridad/ junto al repo)
copias=()
if [ -n "${_INSTALAR_CON_SG:-}" ]; then
    IFS='|' read -ra copias <<< "${_INSTALAR_COPIAS:-}"
elif [ -n "$copia" ]; then
    copias=("$copia")
elif [ "$origen" != "$repo" ]; then
    mkdir -p "$repo/../copias-seguridad"
    for z in "$origen"/*.zip; do
        [ -f "$z" ] || continue
        guardada="$(realpath "$repo/../copias-seguridad")/$(basename "$z")"
        [ -f "$guardada" ] || cp "$z" "$guardada"
        copias+=("$guardada")
    done
fi

# --- 4. Docker: si esta sesión aún no tiene el grupo docker, se relanza el script con `sg docker` ----------------
if ! docker info > /dev/null 2>&1; then
    [ -z "${_INSTALAR_CON_SG:-}" ] || falla "Docker no responde ni con el grupo docker. Reinicia el PC y repite."
    paso "Continuando con el grupo docker"
    lista="$(IFS='|'; echo "${copias[*]}")"
    exec sg docker -c "_INSTALAR_CON_SG=1 _INSTALAR_COPIAS=$(printf '%q' "$lista") $(printf '%q ' bash "$repo/instalar.sh" "" "$nombre")"
fi

cd "$repo"
paso "Odoo y Postgres en Docker"
if [ ! -f .env ]; then
    clave() { tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 || true; }
    umask 077
    sed -e "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$(clave)/" \
        -e "s/^ODOO_PASSWORD=$/ODOO_PASSWORD=$(clave)/" \
        -e "s/^RUTINAS_PASSWORD=$/RUTINAS_PASSWORD=$(clave)/" \
        -e "s/^ODOO_MASTER_PASSWORD=$/ODOO_MASTER_PASSWORD=$(clave)/" \
        .env.example > .env
    umask 022
    echo "Creado .env con contraseñas al azar (la contraseña maestra del gestor es ODOO_MASTER_PASSWORD)."
fi
docker network inspect proyectitos > /dev/null 2>&1 || docker network create proyectitos > /dev/null
docker compose up -d --build

echo -n "Esperando a Odoo"
for _ in $(seq 90); do
    if docker compose exec -T odoo python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8069/web/health')" > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 2
done
echo

# --- 5. Bases de datos -------------------------------------------------------------------------------------------
for z in "${copias[@]}"; do
    base="${nombre:-$(basename "$z" .zip | sed -E 's/-[0-9]{4}-[0-9]{2}-[0-9]{2}$//')}"
    paso "Base de datos '$base'"
    if docker compose exec -T postgres psql -U admin -Atc "select 1 from pg_database where datname = '$base'" | grep -q 1; then
        echo "Ya existe: no la toco (bórrala antes o indica otro nombre como segundo argumento)."
        continue
    fi
    echo "Restaurando $z…"
    docker compose cp "$z" odoo:/tmp/restaurar.zip
    docker compose exec -T odoo odoo db load "$base" /tmp/restaurar.zip
    docker compose exec -T -u root odoo rm -f /tmp/restaurar.zip
done

paso "Listo"
cat <<FIN
Odoo:        http://localhost:8000 (desde la red local, http://IP-de-este-PC:8000), con tu usuario de siempre.
Repo:        $repo
Claude Code: abre una terminal nueva y ejecuta:  cd $repo && claude
             (la primera vez te pedirá iniciar sesión con tu cuenta).
Si 'docker' da "permission denied" en una terminal nueva: cierra sesión y vuelve a entrar.
FIN

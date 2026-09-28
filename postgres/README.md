# Postgres compartido

Una base de datos y un usuario por proyecto: `rutinas` (fuertafit) y `myspoty`. Los datos viven en el volumen
Docker `postgres-datos`, **fuera del repo**: clonar, limpiar o borrar la carpeta no los toca.

```bash
docker network create proyectitos        # una sola vez (red compartida con las apps)
docker compose up -d                      # arrancar (antes que las apps)
```

- Contraseñas en `.env` (se generan al azar; no se suben a git). Cada app tiene su `DATABASE_URL` en su `.env`.
- Solo accesible desde este PC (`127.0.0.1:5432`) y desde los contenedores de la red `proyectitos` (host `postgres`).
- Copia de seguridad: `docker exec postgres pg_dumpall -U admin > copia.sql`
- Restaurar: `docker exec -i postgres psql -U admin < copia.sql`
- ⚠️ `docker compose down -v` o `docker volume rm postgres-datos` **borran todos los datos**.

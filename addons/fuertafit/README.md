# Mi rutina Fuerta (`fuertafit`)

Módulo de Odoo que genera y planifica rutinas diarias a partir del catálogo de FuertaFit. Solo enlaza a los
vídeos; no descarga nada. Cada usuario de Odoo tiene su calendario, historial y ajustes; el catálogo es común.

## Uso

Odoo (ver el `README.md` de la raíz) → base `fuertafit` → menú **Mi rutina Fuerta**, o directamente
`http://IP-de-este-PC:8000/fuerta`. Pestañas: Hoy, Semana, Calendario, Rutinas, Actualizar (y Entrenador solo con
API key). En Odoo, **Mis datos** y **Catálogo** muestran lo mismo en listas.

## Actualizar el catálogo

Pestaña **Actualizar**: arrastra el marcador «⟳ Actualizar Fuerta» a la barra de marcadores, abre
webapp.fuertafit.com con la sesión iniciada y púlsalo. Trae solo las rutinas nuevas (con tu sesión, desde tu
navegador) y las envía a `/fuerta/api/catalog/import`.

## Tras cambiar código (desde la raíz del repo)

```bash
docker compose exec odoo odoo module upgrade -d fuertafit fuertafit && docker compose restart odoo
```

## Migrar desde la web antigua

La web anterior guardaba los datos en la base `rutinas`. Para pasarlos a tu usuario de Odoo (solo lee `rutinas`):

```bash
docker compose exec -T -e MIGRAR_LOGIN=admin odoo odoo shell -d fuertafit --no-http < addons/fuertafit/scripts/migrar_rutinas.py
```

## Entrenador con IA (opcional, de pago)

Pon `ANTHROPIC_API_KEY` en el `.env` raíz, descomenta el SDK en el `Dockerfile` raíz y
`docker compose up -d --build`. Sin clave todo funciona igual salvo el chat.

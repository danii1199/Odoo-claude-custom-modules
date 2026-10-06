"""Actualiza el catálogo completo (datos + imágenes que falten) desde el shell de Odoo. Mismo código que el botón
«Actualizar catálogo» del backend, pero sin el límite de tiempo de una petición web. Desde la raíz del repo:

    sg docker -c "docker compose exec -T odoo odoo shell -d <bd> --no-http < addons/dbd/scripts/actualizar_catalogo.py"
"""
from odoo.addons.dbd.services.importer import import_all

stats = import_all(env, images=True, log=print)  # noqa: F821 (env lo pone odoo shell)
env.cr.commit()  # noqa: F821
for model, values in stats.items():
    print(model, values)

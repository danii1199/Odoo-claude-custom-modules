{
    "name": "Menú de inicio",
    "summary": "Pantalla de inicio con la cuadrícula de aplicaciones (estilo Enterprise) en vez del desplegable de apps",
    "description": "Sustituye el menú de aplicaciones de arriba a la izquierda por una pantalla de inicio a pantalla "
                   "completa con los iconos de las apps y un buscador de menús. Código propio para Community.",
    "version": "20.0.1.0.1",
    "category": "Hidden/Tools",
    "author": "danii1199",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "menu_inicio/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
}

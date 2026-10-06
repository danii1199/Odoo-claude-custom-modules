from odoo import fields, models

# Rarezas del juego, de menor a mayor (los colores están en static/src/css/dbd.css: .dbd-rarity-<clave>).
RARITIES = [
    ("common", "Común"),
    ("uncommon", "Poco común"),
    ("rare", "Rara"),
    ("very_rare", "Muy rara"),
    ("ultra_rare", "Ultra rara"),
    ("event", "Evento"),
]
DIFFICULTIES = [
    ("easy", "Fácil"),
    ("intermediate", "Intermedia"),
    ("hard", "Difícil"),
    ("very_hard", "Muy difícil"),
]
ROLES = [("survivor", "Superviviente"), ("killer", "Asesino")]


class DbdExternalMixin(models.AbstractModel):
    """Clave del registro en la fuente externa (dbd.tricky.lol): el importador la usa para actualizar en vez de duplicar."""
    _name = "dbd.external.mixin"
    _description = "Registro importable de Dead by Daylight"

    dbd_key = fields.Char("Clave externa", index=True, copy=False,
                          help="Identificador en dbd.tricky.lol (lo rellena «Actualizar catálogo»).")


class DbdCharacterMixin(models.AbstractModel):
    """Campos comunes a supervivientes y asesinos."""
    _name = "dbd.character.mixin"
    _inherit = "dbd.external.mixin"
    _description = "Personaje de Dead by Daylight"
    _order = "sequence, name"

    name = fields.Char("Nombre", required=True, translate=True)
    sequence = fields.Integer("Orden", default=10)
    active = fields.Boolean("Activo", default=True)
    image = fields.Image("Retrato", max_width=1024, max_height=1024)
    chapter = fields.Char("Capítulo / DLC", help="Capítulo o DLC con el que salió; vacío si es del juego base.")
    release_date = fields.Date("Fecha de salida")
    licensed = fields.Boolean("Licenciado", help="Personaje de otra franquicia (sus perks no se enseñan igual).")
    difficulty = fields.Selection(DIFFICULTIES, "Dificultad")
    bio = fields.Html("Resumen", translate=True, help="Estilo de juego y perks propios, en pocas líneas.")
    description = fields.Html("Historia", translate=True)

from odoo import api, fields, models

from .addon import ITEM_TYPES
from .common import RARITIES


class DbdItem(models.Model):
    """Objeto de superviviente (linterna, botiquín…): lo que se lleva a la partida junto con 2 complementos."""
    _name = "dbd.item"
    _inherit = "dbd.external.mixin"
    _description = "Objeto de superviviente"
    _order = "item_type, rarity_order, name"

    name = fields.Char("Nombre", required=True, translate=True)
    active = fields.Boolean("Activo", default=True)
    item_type = fields.Selection(ITEM_TYPES, "Tipo", required=True)
    rarity = fields.Selection(RARITIES, "Rareza", required=True, default="common")
    rarity_order = fields.Integer("Orden de rareza", compute="_compute_rarity_order", store=True)
    event = fields.Char("Evento", help="Si es un objeto de evento (aniversario, Halloween…).")
    image = fields.Image("Icono", max_width=256, max_height=256)
    description = fields.Html("Efecto", translate=True)

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe un objeto con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    @api.depends("rarity")
    def _compute_rarity_order(self):
        keys = [key for key, _label in RARITIES]
        for rec in self:
            rec.rarity_order = keys.index(rec.rarity) if rec.rarity in keys else 0

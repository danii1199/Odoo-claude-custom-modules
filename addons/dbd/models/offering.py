from odoo import api, fields, models

from .common import RARITIES

OFFERING_CATEGORIES = [
    ("bloodpoints", "Puntos de sangre"),
    ("luck", "Suerte"),
    ("fog", "Niebla"),
    ("realm", "Reino"),
    ("hook", "Ganchos"),
    ("chest", "Cofres"),
    ("hatch", "Trampilla"),
    ("mori", "Mori"),
    ("shroud", "Sudario (aparición)"),
    ("other", "Otra"),
]


class DbdOffering(models.Model):
    _name = "dbd.offering"
    _inherit = "dbd.external.mixin"
    _description = "Ofrenda"
    _order = "category, rarity_order, name"

    name = fields.Char("Nombre", required=True, translate=True)
    active = fields.Boolean("Activo", default=True)
    role = fields.Selection([("survivor", "Superviviente"), ("killer", "Asesino"), ("both", "Ambos")], "Bando",
                            required=True, default="both")
    category = fields.Selection(OFFERING_CATEGORIES, "Tipo", required=True, default="other")
    rarity = fields.Selection(RARITIES, "Rareza", required=True, default="common")
    rarity_order = fields.Integer("Orden de rareza", compute="_compute_rarity_order", store=True)
    realm_id = fields.Many2one("dbd.realm", "Reino", ondelete="set null",
                               help="Solo en las ofrendas de reino: el reino al que llevan.")
    image = fields.Image("Icono", max_width=256, max_height=256)
    description = fields.Html("Efecto", translate=True)

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe una ofrenda con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    @api.depends("rarity")
    def _compute_rarity_order(self):
        keys = [key for key, _label in RARITIES]
        for rec in self:
            rec.rarity_order = keys.index(rec.rarity) if rec.rarity in keys else 0

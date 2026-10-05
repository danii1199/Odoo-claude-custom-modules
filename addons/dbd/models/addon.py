from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .common import RARITIES, ROLES

ITEM_TYPES = [
    ("toolbox", "Caja de herramientas"),
    ("medkit", "Botiquín"),
    ("flashlight", "Linterna"),
    ("key", "Llave"),
    ("map", "Mapa"),
    ("fog_vial", "Vial de niebla"),
    ("firecracker", "Petardo"),
]


class DbdAddon(models.Model):
    """Complemento: de un asesino (modifica su poder) o de un objeto de superviviente."""
    _name = "dbd.addon"
    _inherit = "dbd.external.mixin"
    _description = "Complemento"
    _order = "role, killer_id, item_type, rarity_order, name"

    name = fields.Char("Nombre", required=True, translate=True)
    active = fields.Boolean("Activo", default=True)
    role = fields.Selection(ROLES, "Bando", required=True, compute="_compute_role", store=True, readonly=False,
                            precompute=True)
    killer_id = fields.Many2one("dbd.killer", "Asesino", ondelete="cascade", index=True)
    item_type = fields.Selection(ITEM_TYPES, "Objeto")
    rarity = fields.Selection(RARITIES, "Rareza", required=True, default="common")
    rarity_order = fields.Integer("Orden de rareza", compute="_compute_rarity_order", store=True)
    image = fields.Image("Icono", max_width=256, max_height=256)
    description = fields.Html("Efecto", translate=True)

    _name_unique = models.Constraint("UNIQUE (name, killer_id, item_type)", "Ese complemento ya existe.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    @api.depends("killer_id", "item_type")
    def _compute_role(self):
        for rec in self:
            if rec.killer_id:
                rec.role = "killer"
            elif rec.item_type:
                rec.role = "survivor"
            elif not rec.role:
                rec.role = False

    @api.depends("rarity")
    def _compute_rarity_order(self):
        keys = [key for key, _label in RARITIES]
        for rec in self:
            rec.rarity_order = keys.index(rec.rarity) if rec.rarity in keys else 0

    @api.constrains("role", "killer_id", "item_type")
    def _check_owner(self):
        for rec in self:
            if rec.role == "killer" and (not rec.killer_id or rec.item_type):
                raise ValidationError(f"El complemento «{rec.name}» de asesino necesita su asesino (y ningún objeto).")
            if rec.role == "survivor" and (not rec.item_type or rec.killer_id):
                raise ValidationError(f"El complemento «{rec.name}» de superviviente necesita su objeto (y ningún asesino).")

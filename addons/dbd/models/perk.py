from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .common import ROLES


class DbdPerkTag(models.Model):
    _name = "dbd.perk.tag"
    _inherit = "dbd.external.mixin"
    _description = "Etiqueta de perk"
    _order = "name"

    name = fields.Char("Nombre", required=True, translate=True)
    color = fields.Integer("Color")

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe esa etiqueta.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")


class DbdPerk(models.Model):
    _name = "dbd.perk"
    _inherit = "dbd.external.mixin"
    _description = "Perk (habilidad)"
    _order = "role, sequence, name"

    name = fields.Char("Nombre", required=True, translate=True)
    sequence = fields.Integer("Orden", default=10)
    active = fields.Boolean("Activo", default=True)
    role = fields.Selection(ROLES, "Bando", required=True, compute="_compute_role", store=True, readonly=False,
                            precompute=True)
    survivor_id = fields.Many2one("dbd.survivor", "Superviviente", ondelete="set null", index=True)
    killer_id = fields.Many2one("dbd.killer", "Asesino", ondelete="set null", index=True)
    owner_name = fields.Char("Personaje", compute="_compute_owner_name")
    is_general = fields.Boolean("General", compute="_compute_is_general", store=True,
                                help="Perk del juego base que no pertenece a ningún personaje.")
    image = fields.Image("Icono", max_width=256, max_height=256)
    description = fields.Html("Descripción", translate=True)
    tag_ids = fields.Many2many("dbd.perk.tag", string="Etiquetas")

    _name_role_unique = models.Constraint("UNIQUE (name, role)", "Ya existe un perk con ese nombre en ese bando.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    @api.depends("survivor_id", "killer_id")
    def _compute_role(self):
        for rec in self:
            if rec.survivor_id:
                rec.role = "survivor"
            elif rec.killer_id:
                rec.role = "killer"
            elif not rec.role:
                rec.role = False

    @api.depends("survivor_id", "killer_id")
    def _compute_owner_name(self):
        for rec in self:
            rec.owner_name = (rec.survivor_id or rec.killer_id).name or "General"

    @api.depends("survivor_id", "killer_id")
    def _compute_is_general(self):
        for rec in self:
            rec.is_general = not (rec.survivor_id or rec.killer_id)

    @api.constrains("role", "survivor_id", "killer_id")
    def _check_owner(self):
        for rec in self:
            if rec.survivor_id and rec.killer_id:
                raise ValidationError(f"El perk «{rec.name}» no puede ser de un superviviente y de un asesino a la vez.")
            if (rec.role == "survivor" and rec.killer_id) or (rec.role == "killer" and rec.survivor_id):
                raise ValidationError(f"El bando del perk «{rec.name}» no coincide con su personaje.")

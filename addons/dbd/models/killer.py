from odoo import fields, models


class DbdKiller(models.Model):
    _name = "dbd.killer"
    _inherit = "dbd.character.mixin"
    _description = "Asesino"

    real_name = fields.Char("Nombre real", help="Por ejemplo, Evan MacMillan para El Trampero.")
    power_name = fields.Char("Poder", translate=True)
    power_description = fields.Html("Descripción del poder", translate=True)
    power_image = fields.Image("Icono del poder", max_width=256, max_height=256)
    speed = fields.Float("Velocidad (m/s)", digits=(4, 2), default=4.6)
    terror_radius = fields.Integer("Radio de terror (m)", default=32)
    height = fields.Selection([("short", "Bajo"), ("average", "Medio"), ("tall", "Alto")], "Altura", default="tall")
    perk_ids = fields.One2many("dbd.perk", "killer_id", "Perks propios")
    addon_ids = fields.One2many("dbd.addon", "killer_id", "Complementos")
    perk_count = fields.Integer("Nº de perks", compute="_compute_counts")
    addon_count = fields.Integer("Nº de complementos", compute="_compute_counts")

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe un asesino con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    def _compute_counts(self):
        for rec in self:
            rec.perk_count = len(rec.perk_ids)
            rec.addon_count = len(rec.addon_ids)

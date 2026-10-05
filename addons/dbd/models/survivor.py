from odoo import fields, models


class DbdSurvivor(models.Model):
    _name = "dbd.survivor"
    _inherit = "dbd.character.mixin"
    _description = "Superviviente"

    perk_ids = fields.One2many("dbd.perk", "survivor_id", "Perks propios")
    perk_count = fields.Integer("Nº de perks", compute="_compute_perk_count")

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe un superviviente con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

    def _compute_perk_count(self):
        for rec in self:
            rec.perk_count = len(rec.perk_ids)

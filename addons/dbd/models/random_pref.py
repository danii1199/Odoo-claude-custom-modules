from odoo import api, fields, models


class DbdRandomPref(models.Model):
    """Personajes que el usuario ha quitado del sorteo de /dbd/aleatoria. Se guardan los excluidos (no los
    incluidos) para que los personajes nuevos entren en el sorteo sin tocar nada."""
    _name = "dbd.random.pref"
    _description = "Preferencias de la build aleatoria"

    user_id = fields.Many2one("res.users", "Usuario", required=True, default=lambda self: self.env.user,
                              ondelete="cascade", index=True)
    excluded_survivor_ids = fields.Many2many("dbd.survivor", "dbd_random_pref_survivor_rel", "pref_id", "survivor_id",
                                             string="Supervivientes excluidos")
    excluded_killer_ids = fields.Many2many("dbd.killer", "dbd_random_pref_killer_rel", "pref_id", "killer_id",
                                           string="Asesinos excluidos")

    _user_unique = models.Constraint("UNIQUE (user_id)", "Cada usuario tiene una sola preferencia de sorteo.")

    @api.model
    def _mine(self):
        return self.search([("user_id", "=", self.env.uid)], limit=1)

    @api.model
    def get_for_web(self):
        pref = self._mine()
        return {"survivors": pref.excluded_survivor_ids.ids, "killers": pref.excluded_killer_ids.ids}

    @api.model
    def save_from_web(self, data):
        ids = lambda key, model: self.env[model].browse([int(x) for x in data.get(key) or []]).exists().ids
        vals = {"excluded_survivor_ids": [(6, 0, ids("survivors", "dbd.survivor"))],
                "excluded_killer_ids": [(6, 0, ids("killers", "dbd.killer"))]}
        pref = self._mine()
        if pref:
            pref.write(vals)
        else:
            pref = self.create(vals)
        return pref.get_for_web()

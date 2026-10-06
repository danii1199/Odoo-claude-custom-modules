from odoo import fields, models


class DbdRealm(models.Model):
    """Reino: agrupa mapas (y es el destino de las ofrendas de reino)."""
    _name = "dbd.realm"
    _inherit = "dbd.external.mixin"
    _description = "Reino"
    _order = "sequence, name"

    name = fields.Char("Nombre", required=True, translate=True)
    sequence = fields.Integer("Orden", default=10)
    active = fields.Boolean("Activo", default=True)
    image = fields.Image("Imagen", max_width=1024, max_height=1024)
    description = fields.Html("Descripción", translate=True)
    map_ids = fields.One2many("dbd.map", "realm_id", "Mapas")
    offering_ids = fields.One2many("dbd.offering", "realm_id", "Ofrendas de reino")

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe un reino con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")


class DbdMap(models.Model):
    _name = "dbd.map"
    _inherit = "dbd.external.mixin"
    _description = "Mapa"
    _order = "realm_id, sequence, name"

    name = fields.Char("Nombre", required=True, translate=True)
    sequence = fields.Integer("Orden", default=10)
    active = fields.Boolean("Activo", default=True)
    realm_id = fields.Many2one("dbd.realm", "Reino", required=True, ondelete="restrict", index=True)
    image = fields.Image("Imagen", max_width=1024, max_height=1024)
    size = fields.Selection([("small", "Pequeño"), ("medium", "Mediano"), ("large", "Grande")], "Tamaño")
    description = fields.Html("Descripción", translate=True)

    _name_unique = models.Constraint("UNIQUE (name)", "Ya existe un mapa con ese nombre.")
    _dbd_key_unique = models.Constraint("UNIQUE (dbd_key)", "Esa clave externa ya está en uso.")

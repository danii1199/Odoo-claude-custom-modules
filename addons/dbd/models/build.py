from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .common import ROLES

MAX_PERKS = 4
MAX_ADDONS = 2


class DbdBuild(models.Model):
    """Build como en el juego: personaje, 4 perks, objeto (superviviente) o poder (asesino) con 2 complementos y una
    ofrenda. Cada usuario edita solo las suyas; las públicas (`is_public`) las lee todo el mundo, también los
    visitantes sin sesión (dominios en security/ir.access.csv)."""
    _name = "dbd.build"
    _description = "Build"
    _order = "write_date desc, id desc"

    name = fields.Char("Nombre", required=True, default="Mi build")
    user_id = fields.Many2one("res.users", "Usuario", required=True, default=lambda self: self.env.user,
                              ondelete="cascade", index=True)
    role = fields.Selection(ROLES, "Bando", required=True, default="survivor")
    survivor_id = fields.Many2one("dbd.survivor", "Superviviente", ondelete="set null")
    killer_id = fields.Many2one("dbd.killer", "Asesino", ondelete="set null")
    perk_ids = fields.Many2many("dbd.perk", string="Perks")
    item_id = fields.Many2one("dbd.item", "Objeto", ondelete="set null")
    item_type = fields.Selection(related="item_id.item_type")
    addon_ids = fields.Many2many("dbd.addon", string="Complementos")
    offering_id = fields.Many2one("dbd.offering", "Ofrenda", ondelete="set null")
    is_random = fields.Boolean("Aleatoria", help="Generada con la ruleta.")
    is_public = fields.Boolean("Pública", help="La ven todos en la lista de builds publicadas de la web.")
    author_name = fields.Char("Autor", compute="_compute_author_name", store=True,
                              help="Nombre del usuario guardado aquí: quien ve una build pública no puede leer usuarios.")
    note = fields.Text("Notas")
    character_name = fields.Char("Personaje", compute="_compute_character_name")

    @api.depends("user_id.name")
    def _compute_author_name(self):
        for rec in self:
            rec.author_name = rec.user_id.name

    @api.depends("role", "survivor_id", "killer_id")
    def _compute_character_name(self):
        for rec in self:
            char = rec.survivor_id if rec.role == "survivor" else rec.killer_id
            rec.character_name = char.name or "Cualquiera"

    @api.onchange("role")
    def _onchange_role(self):
        """Al cambiar de bando se vacía lo que no vale para el otro."""
        if self.role == "survivor":
            self.killer_id = False
        else:
            self.survivor_id = self.item_id = False
        self.perk_ids = self.perk_ids.filtered(lambda p: p.role == self.role)
        self.addon_ids = self.addon_ids.filtered(lambda a: a.role == self.role)

    @api.constrains("role", "survivor_id", "killer_id", "perk_ids", "item_id", "addon_ids", "offering_id")
    def _check_build(self):
        for rec in self:
            errors = []
            if len(rec.perk_ids) > MAX_PERKS:
                errors.append(f"como mucho {MAX_PERKS} perks")
            if rec.perk_ids.filtered(lambda p: p.role != rec.role):
                errors.append("hay perks del otro bando")
            if len(rec.addon_ids) > MAX_ADDONS:
                errors.append(f"como mucho {MAX_ADDONS} complementos")
            if rec.role == "survivor":
                if rec.killer_id:
                    errors.append("una build de superviviente no lleva asesino")
                if rec.addon_ids and not rec.item_id:
                    errors.append("los complementos necesitan un objeto")
                if rec.addon_ids.filtered(lambda a: a.item_type != rec.item_id.item_type):
                    errors.append("los complementos tienen que ser del tipo del objeto")
            else:
                if rec.survivor_id or rec.item_id:
                    errors.append("una build de asesino no lleva superviviente ni objeto")
                if rec.addon_ids and not rec.killer_id:
                    errors.append("los complementos de poder necesitan un asesino")
                if rec.addon_ids.filtered(lambda a: a.killer_id != rec.killer_id):
                    errors.append("los complementos tienen que ser del poder de ese asesino")
            if rec.offering_id and rec.offering_id.role not in (rec.role, "both"):
                errors.append("la ofrenda es del otro bando")
            if errors:
                raise ValidationError(f"Build «{rec.name}» no válida: " + "; ".join(errors) + ".")

    def action_open_web(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": f"/dbd/build?id={self.id}", "target": "self"}

    # ---------- web (/dbd/build) ----------
    def to_web(self):
        """Lo que necesita el editor de la web para pintar la build guardada."""
        self.ensure_one()
        return {
            "id": self.id, "name": self.name, "role": self.role, "random": self.is_random, "note": self.note or "",
            "public": self.is_public, "author": self.author_name or "", "mine": self.user_id == self.env.user,
            "character": (self.survivor_id if self.role == "survivor" else self.killer_id).id or None,
            "perks": self.perk_ids.ids, "item": self.item_id.id or None, "addons": self.addon_ids.ids,
            "offering": self.offering_id.id or None,
            "updated": fields.Datetime.to_string(self.write_date),
        }

    @api.model
    def save_from_web(self, data):
        """Crea o actualiza (si trae `id` y es del usuario) una build desde el JSON de la web."""
        role = data.get("role")
        if role not in ("survivor", "killer"):
            raise ValidationError("Bando no válido.")
        char = data.get("character") or False
        vals = {
            "name": (data.get("name") or "").strip()[:80] or "Mi build",
            "role": role,
            "survivor_id": char if role == "survivor" else False,
            "killer_id": char if role == "killer" else False,
            "perk_ids": [(6, 0, [int(x) for x in data.get("perks") or []])],
            "item_id": (data.get("item") or False) if role == "survivor" else False,
            "addon_ids": [(6, 0, [int(x) for x in data.get("addons") or []])],
            "offering_id": data.get("offering") or False,
            "is_random": bool(data.get("random")),
            "is_public": bool(data.get("public")),
            "note": (data.get("note") or "")[:2000] or False,
        }
        build = self.search([("id", "=", int(data["id"])), ("user_id", "=", self.env.uid)]) if data.get("id") else self.browse()
        if build:
            build.write(vals)  # el dominio de ir.access impide tocar las de otro usuario
        else:
            build = self.create(vals)
        return build

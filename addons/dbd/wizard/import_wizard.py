import json

from odoo import fields, models
from odoo.exceptions import UserError

from ..services.importer import import_all


class DbdImportWizard(models.TransientModel):
    """Botón «Actualizar catálogo»: trae lo nuevo de dbd.tricky.lol (y las imágenes de la wiki) sin borrar nada."""
    _name = "dbd.import.wizard"
    _description = "Actualizar catálogo de Dead by Daylight"

    with_images = fields.Boolean("Descargar imágenes que falten", default=True,
                                 help="La primera vez son unas 1.600 imágenes: puede tardar varios minutos.")
    force_images = fields.Boolean("Volver a descargar todas las imágenes",
                                  help="Sustituye también las que ya hay (incluidas las que hayas subido a mano).")
    result = fields.Text("Resultado", readonly=True)

    def action_import(self):
        self.ensure_one()
        try:
            stats = import_all(self.env, images=self.with_images, force_images=self.force_images)
        except Exception as e:  # red caída, API cambiada…: que se vea en pantalla
            raise UserError(f"No se pudo actualizar el catálogo: {e}") from e
        names = {"dbd.perk.tag": "Etiquetas", "dbd.realm": "Reinos", "dbd.map": "Mapas", "dbd.survivor": "Supervivientes",
                 "dbd.killer": "Asesinos", "dbd.perk": "Perks", "dbd.addon": "Complementos", "dbd.offering": "Ofrendas", "dbd.item": "Objetos"}
        lines = [f"{names.get(k, k)}: " + ", ".join(f"{n} {label}" for label, n in v.items()) for k, v in stats.items()]
        self.result = "\n".join(lines) or json.dumps(stats)
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id,
                "view_mode": "form", "target": "new"}

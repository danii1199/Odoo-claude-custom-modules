import json

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestBuilds(HttpCase):
    """Builds: validación del modelo y API de la web (/dbd/api/builds*). Usa los datos de ejemplo del módulo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.meg = cls.env.ref("dbd.survivor_meg")
        cls.trapper = cls.env.ref("dbd.killer_trapper")
        cls.surv_perks = cls.env["dbd.perk"].search([("role", "=", "survivor")], limit=5)
        cls.killer_perk = cls.env["dbd.perk"].search([("role", "=", "killer")], limit=1)
        cls.medkit = cls.env["dbd.item"].create({"name": "Test Med-Kit", "item_type": "medkit", "rarity": "rare"})
        cls.med_addons = cls.env["dbd.addon"].create([
            {"name": f"Test venda {n}", "role": "survivor", "item_type": "medkit", "rarity": "common"} for n in range(3)
        ])

    def _post(self, url, data):
        return self.url_open(url, data=json.dumps(data), headers={"Content-Type": "application/json"})

    def test_model_validation(self):
        Build = self.env["dbd.build"]
        b = Build.save_from_web({"role": "survivor", "character": self.meg.id, "perks": self.surv_perks[:4].ids,
                                 "item": self.medkit.id, "addons": self.med_addons[:2].ids})
        self.assertEqual(b.to_web()["perks"], self.surv_perks[:4].ids)
        for bad in ({"perks": self.surv_perks.ids}, {"perks": self.killer_perk.ids},
                    {"addons": self.med_addons.ids}, {"item": False, "addons": self.med_addons[:1].ids}):
            with self.assertRaises(ValidationError):
                Build.save_from_web({**b.to_web(), **bad})

    def test_web_api(self):
        self.authenticate("admin", "admin")
        r = self._post("/dbd/api/builds/guardar", {"name": "Mi Meg", "role": "survivor", "character": self.meg.id,
                                                   "perks": self.surv_perks[:2].ids})
        self.assertEqual(r.status_code, 200, r.text)
        build = r.json()
        self.assertEqual(build["name"], "Mi Meg")
        mine = self.url_open("/dbd/api/builds").json()
        self.assertIn(build["id"], [b["id"] for b in mine])
        # inválida → 400 con el mensaje
        r = self._post("/dbd/api/builds/guardar", {**build, "perks": self.killer_perk.ids})
        self.assertEqual(r.status_code, 400)
        self.assertIn("otro bando", r.json()["error"])
        # sin JSON → 415
        r = self.url_open("/dbd/api/builds/guardar", data={"x": "1"})
        self.assertEqual(r.status_code, 415)
        # borrar
        self.assertEqual(self._post("/dbd/api/builds/borrar", {"id": build["id"]}).status_code, 200)
        self.assertNotIn(build["id"], [b["id"] for b in self.url_open("/dbd/api/builds").json()])

    def test_pages_and_catalog_public(self):
        for url in ("/dbd/build", "/dbd/aleatoria"):
            self.assertEqual(self.url_open(url).status_code, 200, url)
        cat = self.url_open("/dbd/api/catalogo").json()
        self.assertTrue(cat["perks"] and cat["survivors"] and cat["killers"])
        self.assertIn(self.medkit.id, [i["id"] for i in cat["items"]])


@tagged("post_install", "-at_install")
class TestPublicBuilds(HttpCase):
    """Login obligatorio para crear, builds públicas/privadas y preferencias del sorteo (usuario de portal, como los
    que se crean cuenta desde la web)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal = cls.env["res.users"].create({
            "name": "Jugadora Portal", "login": "jugadora", "password": "jugadora-1234",
            "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })
        cls.meg = cls.env.ref("dbd.survivor_meg")
        cls.perks = cls.env["dbd.perk"].search([("role", "=", "survivor")], limit=4)

    def _post(self, url, data):
        return self.url_open(url, data=json.dumps(data), headers={"Content-Type": "application/json"})

    def test_build_page_requires_login(self):
        r = self.url_open("/dbd/build?r=s&c=1", allow_redirects=False)
        self.assertIn(r.status_code, (302, 303))
        self.assertIn("/web/login?redirect=%2Fdbd%2Fbuild%3Fr%3Ds%26c%3D1", r.headers["Location"])
        self.assertEqual(self.url_open("/dbd/aleatoria").status_code, 200)  # la aleatoria no exige sesión
        self.assertEqual(self.url_open("/dbd/builds").status_code, 200)

    def test_public_and_private(self):
        self.authenticate("jugadora", "jugadora-1234")
        self.assertEqual(self.url_open("/dbd/build").status_code, 200)
        pub = self._post("/dbd/api/builds/guardar", {"name": "Pública", "role": "survivor", "character": self.meg.id,
                                                     "perks": self.perks.ids, "public": True}).json()
        priv = self._post("/dbd/api/builds/guardar", {"name": "Privada", "role": "survivor", "public": False}).json()
        self.assertTrue(pub["public"] and pub["author"] == "Jugadora Portal" and pub["mine"])
        self.assertEqual(self.url_open(f"/dbd/api/builds/{priv['id']}").status_code, 200)  # la propia sí
        # sorteo: guardar personajes quitados
        prefs = self._post("/dbd/api/aleatoria/prefs/guardar", {"survivors": [self.meg.id], "killers": []}).json()
        self.assertEqual(prefs["survivors"], [self.meg.id])
        self.assertEqual(self.url_open("/dbd/api/aleatoria/prefs").json()["survivors"], [self.meg.id])
        # anónimo: ve la pública, no la privada, y no puede guardar
        self.logout()
        ids = [b["id"] for b in self.url_open("/dbd/api/builds/publicas").json()]
        self.assertIn(pub["id"], ids)
        self.assertNotIn(priv["id"], ids)
        self.assertEqual(self.url_open(f"/dbd/api/builds/{pub['id']}").status_code, 200)
        self.assertEqual(self.url_open(f"/dbd/api/builds/{priv['id']}").status_code, 404)
        r = self.url_open("/dbd/api/builds/guardar", data=json.dumps({"name": "x", "role": "survivor"}),
                          headers={"Content-Type": "application/json"}, allow_redirects=False)
        self.assertIn(r.status_code, (302, 303))  # auth="user": al login, sin guardar nada
        self.assertFalse(self.env["dbd.build"].search_count([("name", "=", "x")]))
        # otro usuario no puede editar la build ajena (crea una nueva suya en su lugar)
        self.authenticate("admin", "admin")
        other = self._post("/dbd/api/builds/guardar", {**pub, "name": "Robada"}).json()
        self.assertNotEqual(other["id"], pub["id"])
        self.assertEqual(self.env["dbd.build"].browse(pub["id"]).name, "Pública")

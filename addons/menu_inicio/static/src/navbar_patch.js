/** Barra superior: el botón de apps abre/cierra el menú de inicio en vez del desplegable. */
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { homeMenu } from "./home_menu_state";

patch(NavBar.prototype, {
    get homeMenuIsOpen() {
        return homeMenu.isOpen();
    },
    // Odoo necesita un setter junto al getter en los patch (ver website/navbar.js).
    set homeMenuIsOpen(_) {},

    onHomeMenuToggle() {
        // Sin app abierta (recién entrado) no hay nada a lo que volver: se queda abierto.
        if (homeMenu.isOpen() && !this.menuService.getCurrentApp()) {
            return;
        }
        homeMenu.toggle();
    },

    // En móvil, «Todas las apps» del menú lateral abre también el menú de inicio.
    onAllAppsBtnClick() {
        this._closeAppMenuSidebar();
        homeMenu.show();
    },
});

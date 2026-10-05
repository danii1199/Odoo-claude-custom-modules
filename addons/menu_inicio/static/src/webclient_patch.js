/** Al entrar en /odoo sin ninguna acción se muestra el menú de inicio en vez de abrir la primera app. */
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { homeMenu } from "./home_menu_state";

patch(WebClient.prototype, {
    _loadDefaultApp() {
        homeMenu.show();
    },
});

/** Al entrar en /odoo sin ninguna acción (o volver a esa URL con «Atrás») se muestra el menú de inicio en vez de
 *  abrir la primera app. */
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { homeMenu } from "./home_menu_state";

patch(WebClient.prototype, {
    _loadDefaultApp() {
        // La entrada del historial de /odoo nace sin estado: al volver a ella con «Atrás», el router de Odoo la
        // tomaría por un clic en un enlace y no recargaría nada (URL de inicio con la app anterior pintada).
        // Con estado, el popstate lanza ROUTE_CHANGE → loadRouterState → aquí otra vez → menú de inicio.
        if (!browser.history.state?.nextState) {
            browser.history.replaceState({ nextState: router.current }, "", browser.location.href);
        }
        homeMenu.show({ standalone: true });
    },
});

/** Estado compartido del menú de inicio. Lo leen la barra (botón), el propio menú y el WebClient.
 *  - isOpen: si se ve.
 *  - standalone: abierto «en lugar de» una app (URL /odoo sin acción: al entrar o al volver con «Atrás»).
 *    Entonces no se puede cerrar con Esc ni con el botón: lo que hay detrás no corresponde a la URL. */
import { signal } from "@odoo/owl";

const isOpen = signal(false);
const standalone = signal(false);

export const homeMenu = {
    isOpen,
    standalone,
    show: ({ standalone: alone = false } = {}) => {
        standalone.set(alone);
        isOpen.set(true);
    },
    hide: () => {
        isOpen.set(false);
        standalone.set(false);
    },
    toggle: () => (isOpen() ? homeMenu.hide() : homeMenu.show()),
};

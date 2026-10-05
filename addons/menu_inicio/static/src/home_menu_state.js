/** Estado compartido del menú de inicio: abierto o cerrado. Lo leen la barra (botón) y el propio menú. */
import { signal } from "@odoo/owl";

const isOpen = signal(false);

export const homeMenu = {
    isOpen,
    show: () => isOpen.set(true),
    hide: () => isOpen.set(false),
    toggle: () => isOpen.set(!isOpen()),
};

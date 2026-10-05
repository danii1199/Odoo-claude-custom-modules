/** Pantalla de inicio: cuadrícula de apps + buscador de menús. Se pinta sobre la acción actual, bajo la barra. */
import { Component, onMounted, onPatched, proxy, signal, useListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { homeMenu } from "./home_menu_state";

/** Quita tildes y pasa a minúsculas para buscar sin importar cómo se escriba. */
const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export class HomeMenu extends Component {
    static template = "menu_inicio.HomeMenu";

    search = signal.ref();

    setup() {
        this.menuService = useService("menu");
        this.homeMenu = homeMenu;
        this.state = proxy({ query: "", focused: 0 });

        // Si se abre otra acción por otro camino (migas, systray…), se cierra el menú de inicio.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => homeMenu.hide());

        // Teclear en cualquier sitio con el menú abierto escribe en el buscador; Esc vuelve a la app.
        useListener(window, "keydown", (ev) => this.onWindowKeydown(ev));

        const focusSearch = () => {
            if (homeMenu.isOpen() && this.search()) {
                this.search().focus();
            }
        };
        onMounted(focusSearch);
        onPatched(focusSearch);
    }

    get apps() {
        return this.menuService.getApps().map((app) => {
            const [iconClass, iconColor, iconBg] = (app.webIcon || "").split(",");
            return { ...app, iconClass, iconColor, iconBg };
        });
    }

    /** Menús con acción que coinciden con la búsqueda, con su ruta ("Ventas / Pedidos / Presupuestos"). */
    get results() {
        const q = norm(this.state.query.trim());
        if (!q) {
            return [];
        }
        const all = this.menuService.getAll();
        const byId = Object.fromEntries(all.map((m) => [m.id, m]));
        const parentOf = {};
        for (const m of all) {
            for (const c of m.children || []) {
                parentOf[c] = m.id;
            }
        }
        const path = (m) => {
            const names = [];
            for (let cur = m; cur && cur.id !== "root"; cur = byId[parentOf[cur.id]]) {
                names.unshift(cur.name);
            }
            return names.join(" / ");
        };
        return all
            .filter((m) => m.actionID && m.id !== "root")
            .map((m) => ({ menu: m, label: path(m) }))
            .filter((r) => norm(r.label).includes(q))
            .slice(0, 30);
    }

    get filteredApps() {
        const q = norm(this.state.query.trim());
        return q ? this.apps.filter((a) => norm(a.name).includes(q)) : this.apps;
    }

    get canClose() {
        return !!this.menuService.getCurrentApp();
    }

    async open(menu) {
        homeMenu.hide();
        this.state.query = "";
        await this.menuService.selectMenu(menu);
    }

    onInput(ev) {
        this.state.query = ev.target.value;
        this.state.focused = 0;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.onWindowKeydown(ev);
            return;
        }
        const items = this.state.query.trim() ? this.results : this.filteredApps;
        if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
            ev.preventDefault();
            const step = ev.key === "ArrowDown" ? 1 : -1;
            this.state.focused = Math.max(0, Math.min(items.length - 1, this.state.focused + step));
        } else if (ev.key === "Enter" && items.length) {
            ev.preventDefault();
            const item = items[this.state.focused] || items[0];
            this.open(item.menu || item);
        }
    }

    onWindowKeydown(ev) {
        if (!homeMenu.isOpen()) {
            return;
        }
        if (ev.key === "Escape" && this.canClose) {
            ev.preventDefault();
            this.state.query = "";
            homeMenu.hide();
        }
    }
}

registry.category("main_components").add("menu_inicio.HomeMenu", { Component: HomeMenu });

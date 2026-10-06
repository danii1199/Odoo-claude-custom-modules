/* Editor de builds (/dbd/build, exige sesión: el controlador manda al login). Usa DbdLoadout (loadout.js).
   Carga una build de ?id= (propia) o de los parámetros de un enlace (?r=s&c=…&p=…: «Copiar y editar» de una
   pública o «Abrir en el editor» de la ruleta). «Pública» = sale en /dbd/builds para todo el mundo. */
(function () {
    "use strict";
    const L = window.DbdLoadout;

    const TITLES = {
        character: (s) => (s.role === "survivor" ? "Elige superviviente" : "Elige asesino"),
        perk: () => "Elige un perk",
        item: () => "Elige un objeto",
        addon: () => "Elige un complemento",
        offering: () => "Elige una ofrenda",
    };
    const KINDS = { character: null, perk: "perks", item: "items", addon: "addons", offering: "offerings" };

    async function init() {
        const page = document.querySelector(".dbd-build-page");
        if (!page) return;
        const root = page.querySelector(".dbd-loadout");
        const canSave = root.dataset.canSave === "1";
        const nameInput = page.querySelector(".dbd-build-name");
        const noteInput = page.querySelector(".dbd-build-note");
        const publicInput = page.querySelector(".dbd-build-public");
        const myBuilds = page.querySelector(".dbd-my-builds");

        await L.catalog();

        const lo = new L.Loadout(root, {
            onSlotClick: async (slot, index) => {
                const s = lo.state;
                if (slot === "item" && s.role === "killer") {
                    lo.message("El poder va con el asesino: elige el asesino.");
                    return;
                }
                const list = L.options(s, slot, index);
                if (!list.length) {
                    lo.message(slot === "addon"
                        ? (s.role === "survivor" ? "Elige antes un objeto." : "Elige antes un asesino.")
                        : "No hay opciones.");
                    return;
                }
                lo.message("");
                const current = slot === "perk" ? s.perks[index] : slot === "addon" ? s.addons[index] : s[slot];
                const kind = KINDS[slot];
                const value = await L.pick({ title: TITLES[slot](s), list: list.map((x) => ({ ...x, kind })), selected: current });
                if (value === undefined) return;
                if (slot === "perk") s.perks[index] = value;
                else if (slot === "addon") s.addons[index] = value;
                else s[slot] = value;
                L.sanitize(s); // p. ej. al cambiar de objeto o de asesino se van los complementos que ya no valen
                lo.render();
            },
        });

        const syncInputs = () => {
            nameInput.value = lo.state.name || "";
            noteInput.value = lo.state.note || "";
            publicInput.checked = !!lo.state.public;
        };
        nameInput.addEventListener("input", () => (lo.state.name = nameInput.value));
        noteInput.addEventListener("input", () => (lo.state.note = noteInput.value));
        publicInput.addEventListener("change", () => (lo.state.public = publicInput.checked));

        // ---------- builds guardadas ----------
        let saved = [];
        async function loadMine() {
            if (!canSave || !myBuilds) return;
            try {
                const r = await fetch("/dbd/api/builds", { credentials: "same-origin" });
                saved = r.ok ? await r.json() : [];
            } catch {
                saved = [];
            }
            renderMine();
        }
        function renderMine() {
            if (!myBuilds) return;
            if (!saved.length) {
                myBuilds.innerHTML = `<p class="dbd-muted">Aún no has guardado ninguna build.</p>`;
                return;
            }
            myBuilds.innerHTML = saved.map((b) => L.buildCard(b, { deletable: true, active: b.id === lo.state.id })).join("");
        }
        myBuilds && myBuilds.addEventListener("click", async (ev) => {
            const card = ev.target.closest(".dbd-saved");
            if (!card) return;
            const b = saved.find((x) => x.id === Number(card.dataset.id));
            if (!b) return;
            if (ev.target.closest(".dbd-saved-delete")) {
                // Sin confirm(): el botón cambia a «¿Seguro?» y hay que pulsarlo otra vez
                const btn = ev.target.closest(".dbd-saved-delete");
                if (!btn.classList.contains("confirm")) {
                    btn.classList.add("confirm");
                    btn.textContent = "¿Borrar?";
                    setTimeout(() => { btn.classList.remove("confirm"); btn.textContent = "×"; }, 3000);
                    return;
                }
                await L.postJSON("/dbd/api/builds/borrar", { id: b.id });
                if (lo.state.id === b.id) lo.state.id = null;
                return loadMine();
            }
            lo.setState(L.fromSaved(b));
            syncInputs();
            history.replaceState(null, "", `/dbd/build?id=${b.id}`);
            renderMine();
            window.scrollTo({ top: 0, behavior: "smooth" });
        });

        // ---------- botones ----------
        page.querySelector(".dbd-build-actions").addEventListener("click", async (ev) => {
            const action = ev.target.closest("[data-action]")?.dataset.action;
            if (!action) return;
            const s = lo.state;
            if (action === "save") {
                if (!canSave) {
                    lo.message(root.dataset.logged === "1" ? "Tu usuario no puede guardar builds." : "Inicia sesión para guardar.");
                    return;
                }
                try {
                    const b = await L.postJSON("/dbd/api/builds/guardar", L.payload(s));
                    s.id = b.id;
                    s.name = b.name;
                    s.public = b.public;
                    syncInputs();
                    history.replaceState(null, "", `/dbd/build?id=${b.id}`);
                    lo.message(b.public ? "Guardada ✔ y publicada en «Builds»." : "Guardada ✔ (privada).");
                    loadMine();
                } catch (e) {
                    lo.message(e.message);
                }
            } else if (action === "new") {
                lo.setState(L.emptyState(s.role));
                syncInputs();
                history.replaceState(null, "", "/dbd/build");
                lo.message("");
                renderMine();
            } else if (action === "clear") {
                lo.setState({ ...L.emptyState(s.role), id: s.id, name: s.name, note: s.note });
            } else if (action === "link") {
                const ok = await L.copy(L.shareUrl(s));
                lo.message(ok ? "Enlace copiado: quien lo abra verá esta build (no hace falta cuenta)." : "");
            }
        });

        // ---------- estado inicial ----------
        const params = new URLSearchParams(location.search);
        await loadMine();
        const fromId = params.get("id") && saved.find((b) => b.id === Number(params.get("id")));
        if (fromId) {
            lo.setState(L.fromSaved(fromId));
            renderMine();
        } else {
            const fromLink = L.fromParams(params);
            lo.setState(fromLink || L.emptyState("survivor")); // copia: se guarda como build nueva y privada
        }
        syncInputs();
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();

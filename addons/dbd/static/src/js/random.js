/* Build aleatoria con ruleta (/dbd/aleatoria). Usa DbdLoadout (loadout.js).
   - «¡Girar la ruleta!»: vacía y saca casilla a casilla (personaje, 4 perks, objeto/complementos, ofrenda).
   - «Siguiente casilla»: saca solo la siguiente que falte.
   - Clic en una casilla: vuelve a girar solo esa (si es el personaje con «Personaje al azar» desactivado, lo elige).
   - «Personajes en el sorteo»: retratos que se marcan/desmarcan (por defecto todos). Con sesión se guarda en la
     cuenta (dbd.random.pref, solo los excluidos); sin sesión dura lo que la página.
   Cada casilla gira mostrando opciones al azar cada vez más despacio hasta pararse en la elegida. */
(function () {
    "use strict";
    const L = window.DbdLoadout;
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    /** Precarga las imágenes de una lista (si no, mientras gira se ven casillas vacías). Espera como mucho 1,5 s. */
    const preloaded = new Set();
    function preload(list) {
        const pending = list.filter((x) => x.img && !preloaded.has(x.img)).map((x) => {
            preloaded.add(x.img);
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = img.onerror = resolve;
                img.src = x.img;
            });
        });
        return Promise.race([Promise.all(pending), sleep(1500)]);
    }

    async function init() {
        const page = document.querySelector(".dbd-random-page");
        if (!page) return;
        const root = page.querySelector(".dbd-loadout");
        const opt = (name) => page.querySelector(`[data-opt="${name}"]`).checked;
        const cat = await L.catalog();
        // En segundo plano: retratos y perks, lo más visto al girar
        preload([...cat.survivors, ...cat.killers, ...cat.perks]);

        let busy = false;
        const lo = new L.Loadout(root, { onSlotClick: (slot, index) => onSlotClick(slot, index) });
        lo.state.random = true;
        lo.render();

        // ---------- personajes en el sorteo ----------
        const canSave = root.dataset.canSave === "1";
        const excluded = { survivor: new Set(), killer: new Set() };
        const poolGrid = page.querySelector(".dbd-pool-grid");
        const poolCount = page.querySelector(".dbd-pool-count");
        if (canSave) {
            try {
                const r = await fetch("/dbd/api/aleatoria/prefs", { credentials: "same-origin" });
                const prefs = r.ok ? await r.json() : {};
                (prefs.survivors || []).forEach((id) => excluded.survivor.add(id));
                (prefs.killers || []).forEach((id) => excluded.killer.add(id));
            } catch {
                /* sin preferencias: todos marcados */
            }
        }
        let saveTimer = null;
        function savePool() {
            if (!canSave) return;
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => {
                L.postJSON("/dbd/api/aleatoria/prefs/guardar",
                           { survivors: [...excluded.survivor], killers: [...excluded.killer] })
                    .catch((e) => lo.message("No se pudo guardar la selección: " + e.message));
            }, 600);
        }
        const roster = () => [...(lo.state.role === "survivor" ? L.idx.survivors : L.idx.killers).values()];
        function renderPool() {
            const ex = excluded[lo.state.role];
            const list = roster();
            poolGrid.innerHTML = list.map((c) => `
                <button type="button" class="dbd-pool-char ${ex.has(c.id) ? "off" : ""}" data-id="${c.id}" title="${L.esc(c.name)}">
                    ${L.picture(c, "", true)}<span>${L.esc(c.name)}</span>
                </button>`).join("");
            poolCount.textContent = `(${list.length - list.filter((c) => ex.has(c.id)).length} de ${list.length})`;
        }
        poolGrid.addEventListener("click", (ev) => {
            const btn = ev.target.closest(".dbd-pool-char");
            if (!btn || busy) return;
            const id = Number(btn.dataset.id);
            const ex = excluded[lo.state.role];
            ex.has(id) ? ex.delete(id) : ex.add(id);
            renderPool();
            savePool();
        });
        page.querySelector(".dbd-pool-actions").addEventListener("click", (ev) => {
            const action = ev.target.closest("[data-pool]")?.dataset.pool;
            if (!action || busy) return;
            const ex = excluded[lo.state.role];
            ex.clear();
            if (action === "none") roster().forEach((c) => ex.add(c.id));
            renderPool();
            savePool();
        });
        renderPool();

        /** Opciones de una casilla para el sorteo: las del loadout menos los personajes quitados. */
        function candidates(slot, i) {
            const list = L.options(lo.state, slot, i, { noEvent: opt("noEvent") });
            return slot === "character" ? list.filter((c) => !excluded[lo.state.role].has(c.id)) : list;
        }

        /** Casillas que se sortean, en orden, según las opciones y el bando. */
        function sequence() {
            const seq = [];
            if (opt("character")) seq.push(["character", 0]);
            for (let i = 0; i < 4; i++) seq.push(["perk", i]);
            if (opt("item")) {
                if (lo.state.role === "survivor") seq.push(["item", 0]);
                seq.push(["addon", 0], ["addon", 1]);
            }
            if (opt("offering")) seq.push(["offering", 0]);
            return seq;
        }

        const get = (slot, i) => (slot === "perk" ? lo.state.perks[i] : slot === "addon" ? lo.state.addons[i] : lo.state[slot]);
        const set = (slot, i, v) => {
            if (slot === "perk") lo.state.perks[i] = v;
            else if (slot === "addon") lo.state.addons[i] = v;
            else lo.state[slot] = v;
        };

        /** Gira una casilla: enseña opciones al azar cada vez más despacio y se para en la ganadora. */
        async function spin(slot, i) {
            const list = candidates(slot, i);
            const el = lo.slotEl(slot, i);
            if (slot === "character" && !list.length) {
                lo.message("No hay personajes en el sorteo: marca alguno en «Personajes en el sorteo».");
            }
            if (!list.length) {
                set(slot, i, null);
                lo.renderSlot(slot, i);
                return;
            }
            const winner = L.pickRandom(list).id;
            if (!opt("fast")) {
                await preload(list);
                el.classList.add("spinning");
                const steps = 16;
                for (let n = 0; n < steps; n++) {
                    lo.renderSlot(slot, i, L.pickRandom(list).id);
                    el.classList.add("spinning");
                    await sleep(35 + Math.round(Math.pow(n / steps, 2.2) * 190)); // se va frenando
                }
                el.classList.remove("spinning");
            }
            set(slot, i, winner);
            lo.renderSlot(slot, i);
            el.classList.remove("landed");
            void el.offsetWidth; // reinicia la animación
            el.classList.add("landed");
            if (slot === "character" && lo.state.role === "killer") lo.renderSlot("item"); // el poder va con el asesino
        }

        async function run(fn) {
            if (busy) return;
            busy = lo.locked = true;
            page.classList.add("dbd-busy");
            try {
                await fn();
            } finally {
                busy = lo.locked = false;
                page.classList.remove("dbd-busy");
                lo.render();
            }
        }

        function resetForSpin() {
            const keepChar = !opt("character") ? lo.state.character : null;
            lo.state = { ...L.emptyState(lo.state.role), character: keepChar, random: true };
            lo.render();
        }

        async function spinAll() {
            resetForSpin();
            for (const [slot, i] of sequence()) await spin(slot, i);
            lo.message("");
        }

        async function spinNext() {
            const pending = sequence().filter(([slot, i]) => !get(slot, i));
            if (!pending.length) {
                resetForSpin();
                return spinNext();
            }
            const [slot, i] = pending[0];
            await spin(slot, i);
        }

        async function onSlotClick(slot, i) {
            const s = lo.state;
            if (slot === "item" && s.role === "killer") slot = "character";
            if (slot === "character" && !opt("character")) {
                // Personaje fijo: se elige a mano
                const list = L.options(s, "character", 0);
                const v = await L.pick({ title: s.role === "survivor" ? "Elige superviviente" : "Elige asesino", list, selected: s.character });
                if (v === undefined) return;
                s.character = v;
                L.sanitize(s);
                lo.render();
                return;
            }
            await run(async () => {
                await spin(slot, i);
                // Lo que depende de esta casilla se vuelve a sortear (complementos del objeto o del asesino)
                const dependsAddons = (slot === "item") || (slot === "character" && s.role === "killer");
                if (dependsAddons && opt("item")) {
                    s.addons = [null, null];
                    await spin("addon", 0);
                    await spin("addon", 1);
                } else {
                    L.sanitize(s);
                }
            });
        }

        lo.onRoleChange = () => {
            lo.state.random = true;
            lo.message("");
            renderPool();
        };

        page.querySelector(".dbd-build-actions").addEventListener("click", async (ev) => {
            const action = ev.target.closest("[data-action]")?.dataset.action;
            if (!action || busy) return;
            const s = lo.state;
            if (action === "spin") {
                await run(spinAll);
            } else if (action === "next") {
                await run(spinNext);
            } else if (action === "edit") {
                location.href = L.shareUrl(s, "/dbd/build"); // el editor pide iniciar sesión si hace falta
            } else if (action === "link") {
                const ok = await L.copy(L.shareUrl(s));
                lo.message(ok ? "Enlace copiado: quien lo abra verá esta build." : "");
            } else if (action === "save") {
                try {
                    const c = (s.role === "survivor" ? L.idx.survivors : L.idx.killers).get(s.character);
                    const isPublic = page.querySelector(".dbd-build-public")?.checked;
                    const b = await L.postJSON("/dbd/api/builds/guardar", { ...L.payload(s), id: null, random: true,
                                                                             public: isPublic,
                                                                             name: `Aleatoria${c ? " · " + c.name : ""}` });
                    lo.message(`Guardada como «${b.name}»${b.public ? " y publicada en «Builds»" : " (privada)"}.`);
                } catch (e) {
                    lo.message(e.message);
                }
            }
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();

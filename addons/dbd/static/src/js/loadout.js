/* Loadout de Dead by Daylight compartido por el editor (/dbd/build, build.js) y la ruleta (/dbd/aleatoria, random.js).
   - DbdLoadout.catalog(): carga /dbd/api/catalogo una vez (personajes, perks, objetos, complementos, ofrendas).
   - new DbdLoadout.Loadout(el, opciones): estado de la build + pintar las casillas de la plantilla dbd.loadout.
   - DbdLoadout.pick({...}): selector a pantalla completa con buscador; devuelve una promesa con el id elegido,
     null para «quitar» o undefined si se cierra sin elegir.
   - Tooltip con la descripción al pasar el ratón por cualquier [data-tip-kind][data-tip-id].
   Estado: {role, character, perks: [4], item, addons: [2], offering, name, note, id, random}. */
(function () {
    "use strict";

    let catalogPromise = null;
    const idx = {};

    function catalog() {
        if (!catalogPromise) {
            catalogPromise = fetch("/dbd/api/catalogo", { credentials: "same-origin" })
                .then((r) => {
                    if (!r.ok) throw new Error("No se pudo cargar el catálogo");
                    return r.json();
                })
                .then((cat) => {
                    for (const key of ["survivors", "killers", "perks", "items", "addons", "offerings"]) {
                        idx[key] = new Map(cat[key].map((x) => [x.id, x]));
                    }
                    return cat;
                });
        }
        return catalogPromise;
    }

    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
    const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const pickRandom = (arr) => (arr.length ? arr[Math.floor(Math.random() * arr.length)] : null);

    function picture(x, cls = "", lazy = false) {
        if (x && x.img) return `<img class="${cls}" src="${esc(x.img)}" alt=""${lazy ? ' loading="lazy"' : ""}/>`;
        return `<span class="dbd-initial ${cls}">${esc((x && x.name ? x.name : "?").slice(0, 1))}</span>`;
    }

    function emptyState(role = "survivor") {
        return { role, character: null, perks: [null, null, null, null], item: null, addons: [null, null],
                 offering: null, name: "", note: "", id: null, random: false, public: false };
    }

    /* ---------- opciones válidas de cada casilla (las comparten editor y ruleta) ---------- */
    function options(state, slot, index, { noEvent = false } = {}) {
        const role = state.role;
        if (slot === "character") {
            return [...(role === "survivor" ? idx.survivors : idx.killers).values()];
        }
        if (slot === "perk") {
            const taken = state.perks.filter((p, i) => p && i !== index);
            return [...idx.perks.values()].filter((p) => p.role === role && !taken.includes(p.id));
        }
        if (slot === "item") {
            if (role !== "survivor") return [];
            return [...idx.items.values()].filter((i) => !(noEvent && i.event));
        }
        if (slot === "addon") {
            const other = state.addons.filter((a, i) => a && i !== index);
            let list;
            if (role === "survivor") {
                const item = idx.items.get(state.item);
                if (!item) return [];
                list = [...idx.addons.values()].filter((a) => a.role === "survivor" && a.type === item.type);
            } else {
                if (!state.character) return [];
                list = [...idx.addons.values()].filter((a) => a.killer === state.character);
            }
            return list.filter((a) => !other.includes(a.id));
        }
        if (slot === "offering") {
            return [...idx.offerings.values()].filter((o) => o.role === role || o.role === "both");
        }
        return [];
    }

    /** Quita lo que ya no encaja (p. ej. complementos de otro objeto o asesino). */
    function sanitize(state) {
        const ok = (slot, i, id) => id && options(state, slot, i).some((x) => x.id === id);
        state.perks = state.perks.map((p, i) => (ok("perk", i, p) ? p : null));
        if (state.role !== "survivor") state.item = null;
        if (state.item && !idx.items.has(state.item)) state.item = null;
        state.addons = state.addons.map((a, i) => (ok("addon", i, a) ? a : null));
        if (state.offering && !ok("offering", 0, state.offering)) state.offering = null;
        if (state.character && !(state.role === "survivor" ? idx.survivors : idx.killers).has(state.character)) {
            state.character = null;
        }
        return state;
    }

    /* ---------- estado <-> URL (para compartir sin guardar) ---------- */
    function toParams(state) {
        const p = new URLSearchParams();
        p.set("r", state.role === "killer" ? "k" : "s");
        if (state.character) p.set("c", state.character);
        if (state.perks.some(Boolean)) p.set("p", state.perks.map((x) => x || 0).join("."));
        if (state.item) p.set("i", state.item);
        if (state.addons.some(Boolean)) p.set("a", state.addons.map((x) => x || 0).join("."));
        if (state.offering) p.set("o", state.offering);
        if (state.name) p.set("n", state.name);
        return p;
    }

    function fromParams(params) {
        if (!params.has("r")) return null;
        const num = (v) => (Number(v) > 0 ? Number(v) : null);
        const list = (v, n) => {
            const out = (v || "").split(".").map(num);
            while (out.length < n) out.push(null);
            return out.slice(0, n);
        };
        const s = emptyState(params.get("r") === "k" ? "killer" : "survivor");
        Object.assign(s, { character: num(params.get("c")), perks: list(params.get("p"), 4), item: num(params.get("i")),
                           addons: list(params.get("a"), 2), offering: num(params.get("o")), name: params.get("n") || "" });
        return s;
    }

    /* ---------- casillas ---------- */
    class Loadout {
        constructor(root, { onSlotClick, onRoleChange, readonly = false } = {}) {
            this.root = root;
            this.readonly = readonly;
            this.state = emptyState();
            this.onSlotClick = onSlotClick;
            this.onRoleChange = onRoleChange;
            this.msg = root.querySelector(".dbd-loadout-msg");
            root.querySelectorAll(".dbd-role-switch button").forEach((btn) => {
                btn.addEventListener("click", () => !this.locked && !this.readonly && this.setRole(btn.dataset.role, { keep: true }));
            });
            root.querySelectorAll(".dbd-slot").forEach((el) => {
                el.addEventListener("click", () => {
                    if (this.onSlotClick && !this.locked) {
                        this.onSlotClick(el.dataset.slot, Number(el.dataset.index || 0), el);
                    }
                });
            });
        }

        setRole(role, { keep = false } = {}) {
            if (role === this.state.role && keep) return;
            const prev = this.state;
            this.state = emptyState(role);
            if (keep) Object.assign(this.state, { name: prev.name, note: prev.note, id: prev.id, public: prev.public });
            this.render();
            if (this.onRoleChange) this.onRoleChange(role);
        }

        setState(state) {
            this.state = sanitize(Object.assign(emptyState(state.role), state));
            this.render();
        }

        message(text) {
            if (!this.msg) return;
            this.msg.textContent = text || "";
            this.msg.hidden = !text;
        }

        slotEl(slot, index = 0) {
            return this.root.querySelector(`.dbd-slot[data-slot="${slot}"][data-index="${index}"]`) ||
                this.root.querySelector(`.dbd-slot[data-slot="${slot}"]:not([data-index])`);
        }

        /** Pinta una casilla. `value` permite pintar algo distinto del estado (lo usa la ruleta mientras gira). */
        renderSlot(slot, index = 0, value) {
            const s = this.state;
            const el = this.slotEl(slot, index);
            if (!el) return;
            const role = s.role;
            let x = null;
            let html = "";
            let tipKind = null;
            el.className = el.className.replace(/\bdbd-rarity-\S+/g, "").replace(/\s+(filled|disabled|fixed)\b/g, "");
            if (slot === "character") {
                const id = value !== undefined ? value : s.character;
                x = (role === "survivor" ? idx.survivors : idx.killers).get(id);
                html = `<div class="dbd-slot-portrait">${picture(x)}</div>
                        <div class="dbd-slot-label">${x ? esc(x.name) : role === "survivor" ? "Elige superviviente" : "Elige asesino"}</div>`;
            } else if (slot === "perk") {
                const id = value !== undefined ? value : s.perks[index];
                x = idx.perks.get(id);
                tipKind = "perks";
                html = `<div class="dbd-slot-diamond"><div>${x ? picture(x) : "<span class='dbd-slot-plus'>+</span>"}</div></div>
                        <div class="dbd-slot-label">${x ? esc(x.name) : "Perk " + (index + 1)}</div>`;
            } else if (slot === "item") {
                if (role === "survivor") {
                    const id = value !== undefined ? value : s.item;
                    x = idx.items.get(id);
                    tipKind = "items";
                    html = `<div class="dbd-slot-box">${x ? picture(x) : "<span class='dbd-slot-plus'>+</span>"}</div>
                            <div class="dbd-slot-label">${x ? esc(x.name) : "Objeto"}</div>`;
                } else {
                    const k = idx.killers.get(s.character);
                    html = `<div class="dbd-slot-box dbd-slot-power">${k && k.powerImg ? picture({ img: k.powerImg }) : "<span class='dbd-slot-plus'>⚔</span>"}</div>
                            <div class="dbd-slot-label">${k ? esc(k.power || "Poder") : "Poder del asesino"}</div>`;
                    el.classList.add("fixed"); // va con el asesino: no se elige
                    if (k) el.classList.add("filled");
                }
            } else if (slot === "addon") {
                const id = value !== undefined ? value : s.addons[index];
                x = idx.addons.get(id);
                tipKind = "addons";
                const canHave = options(s, "addon", index).length > 0 || x;
                html = `<div class="dbd-slot-box dbd-slot-small">${x ? picture(x) : "<span class='dbd-slot-plus'>+</span>"}</div>
                        <div class="dbd-slot-label">${x ? esc(x.name) : "Complemento " + (index + 1)}</div>`;
                if (!canHave) el.classList.add("disabled");
            } else if (slot === "offering") {
                const id = value !== undefined ? value : s.offering;
                x = idx.offerings.get(id);
                tipKind = "offerings";
                html = `<div class="dbd-slot-box dbd-slot-card">${x ? picture(x) : "<span class='dbd-slot-plus'>+</span>"}</div>
                        <div class="dbd-slot-label">${x ? esc(x.name) : "Ofrenda"}</div>`;
            }
            el.innerHTML = html;
            if (x) {
                el.classList.add("filled");
                if (x.rarity) el.classList.add("dbd-rarity-" + x.rarity);
            }
            if (x && tipKind) {
                el.dataset.tipKind = tipKind;
                el.dataset.tipId = x.id;
            } else {
                delete el.dataset.tipKind;
                delete el.dataset.tipId;
            }
        }

        render() {
            const s = this.state;
            this.root.querySelectorAll(".dbd-role-switch button").forEach((b) => {
                b.classList.toggle("active", b.dataset.role === s.role);
            });
            this.root.classList.toggle("dbd-loadout-killer", s.role === "killer");
            this.renderSlot("character");
            for (let i = 0; i < 4; i++) this.renderSlot("perk", i);
            this.renderSlot("item");
            for (let i = 0; i < 2; i++) this.renderSlot("addon", i);
            this.renderSlot("offering");
        }
    }

    /* ---------- selector ---------- */
    function pick({ title, list, selected = null, allowNone = true }) {
        return new Promise((resolve) => {
            const overlay = document.createElement("div");
            overlay.className = "dbd-picker";
            overlay.innerHTML = `
                <div class="dbd-picker-box" role="dialog" aria-label="${esc(title)}">
                    <header>
                        <h2>${esc(title)}</h2>
                        <input type="search" class="dbd-search" placeholder="Buscar…"/>
                        <button type="button" class="dbd-picker-close" aria-label="Cerrar">×</button>
                    </header>
                    <div class="dbd-picker-grid">
                        ${allowNone ? `<button type="button" class="dbd-picker-opt dbd-picker-none" data-id="">
                            <span class="dbd-picker-img"><span class="dbd-initial">∅</span></span><span>Ninguno</span></button>` : ""}
                        ${list.map((x) => `
                            <button type="button" class="dbd-picker-opt ${x.rarity ? "dbd-rarity-" + x.rarity : ""} ${x.id === selected ? "selected" : ""}"
                                    data-id="${x.id}" data-search="${esc(norm([x.name, x.owner, ...(x.tags || [])].join(" ")))}"
                                    ${x.desc !== undefined ? `data-tip-kind="${x.kind}" data-tip-id="${x.id}"` : ""}>
                                <span class="dbd-picker-img">${picture(x, "", true)}</span>
                                <span>${esc(x.name)}${x.owner && x.owner !== "General" ? `<small>${esc(x.owner)}</small>` : ""}</span>
                            </button>`).join("")}
                    </div>
                </div>`;
            document.body.appendChild(overlay);
            const search = overlay.querySelector("input");
            const close = (value) => {
                overlay.remove();
                document.removeEventListener("keydown", onKey);
                hideTip();
                resolve(value);
            };
            const onKey = (ev) => ev.key === "Escape" && close(undefined);
            document.addEventListener("keydown", onKey);
            overlay.addEventListener("click", (ev) => {
                if (ev.target === overlay || ev.target.closest(".dbd-picker-close")) return close(undefined);
                const opt = ev.target.closest(".dbd-picker-opt");
                if (opt) close(opt.dataset.id ? Number(opt.dataset.id) : null);
            });
            search.addEventListener("input", () => {
                const q = norm(search.value.trim());
                overlay.querySelectorAll(".dbd-picker-opt[data-search]").forEach((o) => {
                    o.hidden = q && !o.dataset.search.includes(q);
                });
            });
            search.focus();
        });
    }

    /* ---------- tooltip con la descripción ---------- */
    let tip = null;
    function hideTip() {
        if (tip) tip.hidden = true;
    }
    function setupTooltip() {
        tip = document.createElement("div");
        tip.className = "dbd-tip";
        tip.hidden = true;
        document.body.appendChild(tip);
        document.addEventListener("mouseover", (ev) => {
            const el = ev.target.closest("[data-tip-kind][data-tip-id]");
            const x = el && idx[el.dataset.tipKind] && idx[el.dataset.tipKind].get(Number(el.dataset.tipId));
            if (!x) return hideTip();
            const sub = [x.owner && x.owner !== "General" ? x.owner : "", x.rarity ? (window.DbdLoadout.rarities[x.rarity] || "") : ""]
                .filter(Boolean).join(" · ");
            tip.className = "dbd-tip" + (x.rarity ? " dbd-rarity-" + x.rarity : "");
            tip.innerHTML = `<strong>${esc(x.name)}</strong>${sub ? `<small>${esc(sub)}</small>` : ""}<div>${x.desc || ""}</div>`;
            tip.hidden = false;
        });
        document.addEventListener("mousemove", (ev) => {
            if (!tip || tip.hidden) return;
            const pad = 16;
            const w = tip.offsetWidth, h = tip.offsetHeight;
            let x = ev.clientX + pad, y = ev.clientY + pad;
            if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
            if (y + h > window.innerHeight - 8) y = Math.max(8, window.innerHeight - h - 8);
            tip.style.left = Math.max(8, x) + "px";
            tip.style.top = y + "px";
        });
    }

    /* ---------- guardar / builds del usuario ---------- */
    async function postJSON(url, body) {
        const r = await fetch(url, { method: "POST", credentials: "same-origin",
                                     headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || "Error " + r.status);
        return data;
    }

    function payload(state) {
        return { id: state.id, name: state.name, note: state.note, role: state.role, character: state.character,
                 perks: state.perks.filter(Boolean), item: state.item, addons: state.addons.filter(Boolean),
                 offering: state.offering, random: state.random, public: !!state.public };
    }

    /** Enlace para compartir: por defecto al visor público (/dbd/builds/ver), que no exige sesión. */
    function shareUrl(state, path = "/dbd/builds/ver") {
        if (path === "/dbd/builds/ver" && state.id && state.public) return `${location.origin}${path}?id=${state.id}`;
        return `${location.origin}${path}?${toParams(state).toString()}`;
    }

    const padded = (arr, n) => [...(arr || []), ...Array(n).fill(null)].slice(0, n);

    /** Build guardada (formato de la API) → estado del loadout. */
    function fromSaved(b) {
        return { ...emptyState(b.role), ...b, perks: padded(b.perks, 4), addons: padded(b.addons, 2) };
    }

    /** Tarjeta resumida de una build (listas de «Mis builds» y «Builds»). */
    function buildCard(b, { deletable = false, active = false, href = null } = {}) {
        const c = (b.role === "survivor" ? idx.survivors : idx.killers).get(b.character);
        const perks = (b.perks || []).map((id) => idx.perks.get(id)).filter(Boolean);
        const extra = [["items", idx.items.get(b.item)], ...(b.addons || []).map((id) => ["addons", idx.addons.get(id)]),
                       ["offerings", idx.offerings.get(b.offering)]].filter(([, x]) => x);
        const search = norm([b.name, c && c.name, b.author, ...perks.map((p) => p.name)].join(" "));
        const tag = href ? "a" : "div";
        return `<${tag} class="dbd-saved ${active ? "active" : ""}" data-id="${b.id}" data-role="${b.role}" data-search="${esc(search)}"${href ? ` href="${esc(href)}"` : ""}>
            <div class="dbd-saved-portrait">${picture(c)}</div>
            <div class="dbd-saved-body">
                <strong>${esc(b.name)}</strong>
                <small>${c ? esc(c.name) : "Cualquiera"} · ${b.role === "survivor" ? "Superviviente" : "Asesino"}${b.random ? " · aleatoria" : ""}${b.author && !b.mine ? " · por " + esc(b.author) : ""}</small>
                <div class="dbd-saved-perks">${perks.map((p) => `<span data-tip-kind="perks" data-tip-id="${p.id}">${picture(p)}</span>`).join("")}</div>
                ${extra.length ? `<div class="dbd-saved-extra">${extra.map(([kind, x]) => `<span class="dbd-rarity-${x.rarity}" data-tip-kind="${kind}" data-tip-id="${x.id}">${picture(x)}</span>`).join("")}</div>` : ""}
            </div>
            ${deletable ? `<button type="button" class="dbd-saved-delete" title="Borrar">×</button>` : ""}
        </${tag}>`;
    }

    async function copy(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch {
            window.prompt("Copia el enlace:", text);
            return false;
        }
    }

    window.DbdLoadout = { catalog, idx, Loadout, pick, options, sanitize, emptyState, toParams, fromParams, payload,
                          postJSON, shareUrl, copy, esc, norm, picture, pickRandom, fromSaved, buildCard, rarities: {} };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setupTooltip);
    else setupTooltip();
    catalog().then((cat) => (window.DbdLoadout.rarities = cat.rarities)).catch(() => {});
})();

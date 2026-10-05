/* Builds publicadas (/dbd/builds) y visor de una build (/dbd/builds/ver). Usa DbdLoadout (loadout.js).
   - Lista: «Publicadas» (de todos, sin sesión) y «Mías» (con sesión); filtro por bando y buscador.
   - Visor: ?id=N (pública, o propia aunque sea privada) o los parámetros de un enlace (?r=s&c=…), en solo lectura.
     «Copiar y editar» lleva al editor con la build (el editor pide sesión) para guardarla como propia. */
(function () {
    "use strict";
    const L = window.DbdLoadout;

    async function getJSON(url) {
        const r = await fetch(url, { credentials: "same-origin" });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || "Error " + r.status);
        return data;
    }

    async function initList(page) {
        const list = page.querySelector(".dbd-build-list");
        const search = page.querySelector(".dbd-search");
        const count = page.querySelector(".dbd-count");
        const empty = page.querySelector(".dbd-empty");
        let source = "public";
        let role = "";
        let builds = [];

        function apply() {
            const q = L.norm(search.value.trim());
            let shown = 0;
            list.querySelectorAll(".dbd-saved").forEach((card) => {
                const ok = (!role || card.dataset.role === role) && (!q || card.dataset.search.includes(q));
                card.hidden = !ok;
                if (ok) shown++;
            });
            count.textContent = builds.length ? (shown === builds.length ? `${shown}` : `${shown} / ${builds.length}`) : "";
            empty.hidden = shown > 0 || !builds.length;
        }

        async function load() {
            list.innerHTML = `<p class="dbd-muted">Cargando…</p>`;
            try {
                builds = await getJSON(source === "mine" ? "/dbd/api/builds" : "/dbd/api/builds/publicas");
            } catch (e) {
                builds = [];
                list.innerHTML = `<p class="dbd-muted">${L.esc(e.message)}</p>`;
                return;
            }
            list.innerHTML = builds.length
                ? builds.map((b) => L.buildCard(b, { href: source === "mine" ? `/dbd/build?id=${b.id}` : `/dbd/builds/ver?id=${b.id}` })).join("")
                : `<p class="dbd-muted">${source === "mine" ? "Aún no tienes builds guardadas." : "Todavía no hay builds publicadas. ¡Publica la primera!"}</p>`;
            apply();
        }

        page.querySelector(".dbd-builds-source").addEventListener("click", (ev) => {
            const btn = ev.target.closest("[data-source]");
            if (!btn) return;
            source = btn.dataset.source;
            page.querySelectorAll(".dbd-builds-source button").forEach((b) => b.classList.toggle("active", b === btn));
            load();
        });
        page.querySelector('[data-filter="role"]').addEventListener("click", (ev) => {
            const btn = ev.target.closest("button");
            if (!btn) return;
            role = btn.dataset.value;
            page.querySelectorAll('[data-filter="role"] button').forEach((b) => b.classList.toggle("active", b === btn));
            apply();
        });
        search.addEventListener("input", apply);
        await L.catalog();
        load();
    }

    async function initView(page) {
        const root = page.querySelector(".dbd-loadout");
        await L.catalog();
        const lo = new L.Loadout(root, { readonly: true });
        const params = new URLSearchParams(location.search);
        let state = null;
        let meta = "";
        try {
            if (params.get("id")) {
                const b = await getJSON(`/dbd/api/builds/${Number(params.get("id"))}`);
                state = L.fromSaved(b);
                meta = [b.author && "por " + b.author, b.public ? "pública" : "privada", b.random ? "aleatoria" : ""]
                    .filter(Boolean).join(" · ");
            } else {
                state = L.fromParams(params);
            }
        } catch (e) {
            lo.message(e.message);
        }
        if (!state) {
            lo.setState(L.emptyState("survivor"));
            lo.message(lo.msg.textContent || "No hay ninguna build que mostrar.");
            page.querySelector(".dbd-build-actions").hidden = true;
            return;
        }
        lo.setState(state);
        page.querySelector(".dbd-view-name").textContent = state.name || "Build";
        page.querySelector(".dbd-view-meta").textContent = meta;
        page.querySelector(".dbd-view-note").textContent = state.note || "";
        document.title = `${state.name || "Build"} | Dead by Daylight`;
        // Copia: sin id ni «pública», para guardarla como propia
        const copy = { ...state, id: null, public: false, name: state.name ? `${state.name} (copia)` : "" };
        page.querySelector(".dbd-view-copy").href = L.shareUrl(copy, "/dbd/build");
        page.querySelector('[data-action="link"]').addEventListener("click", async () => {
            const ok = await L.copy(location.href);
            lo.message(ok ? "Enlace copiado." : "");
        });
    }

    function init() {
        const list = document.querySelector(".dbd-builds-page");
        if (list) initList(list);
        const view = document.querySelector(".dbd-build-view");
        if (view) initView(view);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();

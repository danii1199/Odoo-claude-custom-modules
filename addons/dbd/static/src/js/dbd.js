/* Filtros de las páginas de /dbd (sin dependencias). En cada bloque .dbd-filterable:
   - .dbd-chips[data-filter=X]: botones con data-value (valores separados por espacios; vacío = todos);
     un elemento .dbd-item pasa si alguno de sus valores de data-X está entre los del botón activo.
   - .dbd-search: texto que se busca en data-search de cada .dbd-item.
   - .dbd-count muestra cuántos se ven y .dbd-empty aparece si no queda ninguno. */
(function () {
    "use strict";

    function setup(box) {
        const items = Array.from(box.querySelectorAll(".dbd-item"));
        const search = box.querySelector(".dbd-search");
        const count = box.querySelector(".dbd-count");
        const empty = box.querySelector(".dbd-empty");
        const groups = Array.from(box.querySelectorAll(".dbd-chips[data-filter]"));

        function apply() {
            const text = (search ? search.value : "").trim().toLowerCase();
            const active = groups.map((g) => {
                const btn = g.querySelector("button.active");
                const value = btn ? btn.dataset.value : "";
                return { key: g.dataset.filter, values: value ? value.split(" ") : null };
            });
            let shown = 0;
            for (const item of items) {
                let ok = !text || (item.dataset.search || "").includes(text);
                for (const f of active) {
                    if (!ok || !f.values) continue;
                    const own = (item.dataset[f.key] || "").split(" ");
                    ok = own.some((v) => f.values.includes(v));
                }
                item.hidden = !ok;
                if (ok) shown++;
            }
            if (count) count.textContent = shown === items.length ? `${items.length}` : `${shown} / ${items.length}`;
            if (empty) empty.hidden = shown > 0 || items.length === 0;
        }

        for (const g of groups) {
            g.addEventListener("click", (ev) => {
                const btn = ev.target.closest("button");
                if (!btn) return;
                g.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
                apply();
            });
        }
        if (search) search.addEventListener("input", apply);
        apply();
    }

    function init() {
        document.querySelectorAll(".dbd-app .dbd-filterable").forEach(setup);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();

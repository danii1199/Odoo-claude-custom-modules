/* Paleta de comandos (Ctrl+K): busca en Spotify y salta a cualquier sección sin tocar el ratón. */
const Palette = (() => {
  const GO = [["Inicio", "/"], ["Playlists", "/playlists"], ["Tus me gusta", "/liked"], ["Etiquetas", "/tags"],
              ["Playlists inteligentes", "/smart"], ["Estadísticas", "/stats"]];
  let items = [], sel = 0, timer = null, seq = 0;

  function open() {
    $("palette").hidden = false;
    $("paletteInput").value = "";
    draw([]);
    setTimeout(() => $("paletteInput").focus(), 10);
  }
  function close() { $("palette").hidden = true; }

  async function search(q) {
    const my = ++seq;
    const nav = GO.filter(([t]) => q && t.toLowerCase().includes(q.toLowerCase()))
      .map(([t, path]) => ({ group: "Ir a", title: t, sub: "", run: () => go(path) }));
    if (q.length < 2) return draw(nav);
    try {
      const r = await sp("/search", { params: { q, type: "track,artist,album,playlist", limit: 5 } });
      if (my !== seq) return;  // llegó una búsqueda más nueva
      const out = [...nav];
      (r.tracks?.items || []).filter(Boolean).forEach(t => {
        const tr = trackFrom(t);
        out.push({ group: "Canciones", title: t.name, sub: tr.artists.join(", "), img: tr.image,
                   run: () => Player.playUris([t.uri]), queue: () => Player.queue(t.uri) });
      });
      (r.artists?.items || []).filter(Boolean).forEach(a => out.push({ group: "Artistas", title: a.name, sub: "Artista", round: true,
        img: pickImage(a.images, 64), run: () => Player.playContext(a.uri) }));
      (r.albums?.items || []).filter(Boolean).forEach(a => out.push({ group: "Álbumes", title: a.name,
        sub: a.artists.map(x => x.name).join(", "), img: pickImage(a.images, 64), run: () => Player.playContext(a.uri) }));
      (r.playlists?.items || []).filter(Boolean).forEach(p => out.push({ group: "Playlists", title: p.name,
        sub: p.owner?.display_name || "", img: pickImage(p.images, 64), run: () => go(`/playlist/${p.id}`), play: () => Player.playContext(p.uri) }));
      draw(out);
    } catch (e) { if (my === seq) draw(nav, e.message); }
  }

  function draw(list, error) {
    items = list; sel = 0;
    let group = null;
    $("paletteRes").innerHTML = (error ? `<div class="grp">${esc(error)}</div>` : "") + (list.length ? list.map((it, i) => {
      const head = it.group !== group ? `<div class="grp">${esc(it.group)}</div>` : "";
      group = it.group;
      return head + `<div class="it ${it.round ? "round" : ""}" data-i="${i}">
        ${it.img !== undefined ? `<img src="${esc(it.img || "")}" alt="">` : ""}
        <div style="min-width:0"><div class="tt">${esc(it.title)}</div><div class="ta">${esc(it.sub)}</div></div></div>`;
    }).join("") : `<div class="grp">${$("paletteInput").value.length > 1 ? "Sin resultados" : "Escribe para buscar · o «etiq», «playl»… para ir a una sección"}</div>`);
    highlight();
  }

  function highlight() {
    $("paletteRes").querySelectorAll(".it").forEach(el => el.classList.toggle("sel", +el.dataset.i === sel));
    $("paletteRes").querySelector(".it.sel")?.scrollIntoView({ block: "nearest" });
  }

  function choose(i, queue = false) {
    const it = items[i];
    if (!it) return;
    close();
    if (queue && it.queue) return it.queue();
    it.run();
  }

  $("paletteInput").oninput = () => { clearTimeout(timer); timer = setTimeout(() => search($("paletteInput").value.trim()), 220); };
  $("paletteInput").onkeydown = e => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(items.length - 1, sel + 1); highlight(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); highlight(); }
    else if (e.key === "Enter") { e.preventDefault(); choose(sel, e.shiftKey); }
    else if (e.key === "Escape") close();
  };
  $("paletteRes").onclick = e => { const it = e.target.closest(".it"); if (it) choose(+it.dataset.i); };
  $("palette").onmousedown = e => { if (e.target === $("palette")) close(); };

  return { open, close, get isOpen() { return !$("palette").hidden; } };
})();

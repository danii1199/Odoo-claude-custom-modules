/* Vistas de tus datos: Etiquetas, Playlists inteligentes y Estadísticas. */
const Organize = (() => {
  /* ---------- Etiquetas ---------- */
  async function tags(stage) {
    await loadTags();
    stage.innerHTML = `<div class="kicker">tu forma de ordenar</div><div class="mega">Eti<span class="outline">quetas</span></div>
      <div class="two">
        <div class="panel">
          <div class="taglist" id="tgList"></div>
          <form class="newtag" id="tgNew">
            <input class="field" type="text" id="tgName" placeholder="Nueva etiqueta: gym, lluvia, domingo…" maxlength="40">
            <input type="color" id="tgColor" value="${randomColor()}">
            <button class="btn sm acc">Crear</button>
          </form>
          <p class="legend">Etiqueta canciones con el botón ${ICON.tag.replace("<svg", '<svg style="width:14px;height:14px;vertical-align:-2px;stroke:currentColor;fill:none;stroke-width:2"')} de cada fila o del reproductor (tecla <kbd>T</kbd>).</p>
        </div>
        <div id="tgDetail"><div class="empty">Elige una etiqueta para ver sus canciones.</div></div>
      </div>`;
    const draw = () => $("tgList").innerHTML = State.tags.map(g => `
      <div class="tg" data-id="${g.id}"><span class="dot" style="color:${g.color}"></span><span class="nm">${esc(g.name)}</span>
        <span class="muted">${g.count}</span></div>`).join("") || '<span class="muted">Aún no tienes etiquetas.</span>';
    draw();
    $("tgNew").onsubmit = async e => {
      e.preventDefault();
      const name = $("tgName").value.trim();
      if (!name) return;
      try { await api("/api/tags", { name, color: $("tgColor").value }); $("tgName").value = ""; $("tgColor").value = randomColor(); await loadTags(); draw(); }
      catch (err) { toast(err.message, true); }
    };
    $("tgList").onclick = e => { const r = e.target.closest(".tg"); if (r) open(+r.dataset.id); };

    async function open(id) {
      document.querySelectorAll("#tgList .tg").forEach(x => x.classList.toggle("sel", +x.dataset.id === id));
      const g = State.tags.find(t => t.id === id);
      $("tgDetail").innerHTML = `
        <div class="row-actions" style="margin-bottom:14px">
          <input class="field short" id="tgEdName" value="${esc(g.name)}" maxlength="40">
          <input type="color" id="tgEdColor" value="${g.color}">
          <button class="btn sm" id="tgSave">Guardar</button>
          <button class="btn sm acc" id="tgPlay">${ICON.play} Reproducir</button>
          <button class="btn sm danger" id="tgDel">Borrar</button>
        </div><div id="tgTracks"><div class="skeleton"></div></div>`;
      const tracks = await api(`/api/tracks/tagged?tags=${id}`);
      tracks.length ? TrackList.render($("tgTracks"), tracks) : $("tgTracks").innerHTML = '<div class="empty">Ninguna canción con esta etiqueta todavía.</div>';
      $("tgPlay").onclick = () => tracks.length ? Player.playUris(tracks.map(t => t.uri)) : toast("No hay canciones");
      $("tgSave").onclick = async () => {
        try { await api("/api/tags", { id, name: $("tgEdName").value.trim(), color: $("tgEdColor").value }); await loadTags(); draw(); open(id); toast("Etiqueta guardada"); }
        catch (err) { toast(err.message, true); }
      };
      $("tgDel").onclick = async () => {
        if ($("tgDel").dataset.sure !== "1") { $("tgDel").dataset.sure = "1"; $("tgDel").textContent = "¿Seguro? Pulsa otra vez"; return; }
        await api("/api/tags/delete", { id }); await loadTags(); draw();
        $("tgDetail").innerHTML = '<div class="empty">Etiqueta borrada. Las canciones siguen en tu Spotify.</div>';
      };
    }
  }

  /* ---------- Playlists inteligentes ---------- */
  const STATES = ["", "must", "any", "none"];  // clic en una etiqueta: nada -> tiene -> cualquiera de -> sin
  const SOURCES = [
    ["top", "🔥", "Tus más escuchadas", "Tu top de Spotify del periodo elegido."],
    ["artists", "🎤", "Más de tus artistas", "Canciones de tus artistas favoritos que aún no tienes."],
    ["collab", "🧲", "Artistas cercanos", "Quien colabora con tus favoritos y todavía no está en tu top."],
    ["genre", "🎧", "Por género", "Busca canciones de los géneros que escribas."],
    ["liked_recent", "💚", "Me gusta recientes", "Lo último que has guardado."],
    ["forgotten", "💎", "Joyas olvidadas", "Tus me gusta que ya no suenan en tus tops ni en tu historial."],
    ["history", "🔁", "Tus más repetidas", "Lo que más has escuchado últimamente (historial de myspoty)."],
    ["tags", "🏷️", "Tus etiquetas", "Reglas con tus etiquetas y estrellas."],
  ];
  const DEFAULTS = { sources: ["top", "artists"], range: "short_term", artists: 8, days: 30, genres: "", onlyNew: true,
                     tagsAll: [], tagsAny: [], tagsNone: [], minRating: 0, limit: 50, order: "mix", daily: true };
  const PRESETS = [
    ["Mi mes en bucle", { sources: ["top"], range: "short_term", order: "random" }],
    ["Descubrimiento casero", { sources: ["artists", "collab"], artists: 8, onlyNew: true }],
    ["Mezcla total", { sources: ["top", "artists", "collab", "liked_recent"], days: 45 }],
    ["Rescate de joyas", { sources: ["forgotten"], order: "random" }],
    ["Recién guardadas", { sources: ["liked_recent"], days: 30, daily: false }],
  ];
  const srcLabel = r => (r.sources || ["tags"]).map(k => SOURCES.find(x => x[0] === k)?.[1] || "").join(" ");

  async function smart(stage) {
    await loadTags();
    stage.innerHTML = `<div class="kicker">se hacen solas</div><div class="mega">Intel<span class="acc">igentes</span></div>
      <div class="two"><div class="panel"><div id="smList"></div><button class="btn acc" id="smNew">⚡ Nueva</button></div>
      <div id="smEdit"></div></div>`;
    let items = [];
    const drawList = async (sel) => {
      items = await api("/api/smart");
      $("smList").innerHTML = items.map(s => `<div class="smartcard ${s.id === sel ? "sel" : ""}" data-id="${s.id}">
        <div><div class="nm">⚡ ${esc(s.name)}</div><div class="muted" style="font-size:12px">${srcLabel(s.rules)} ·
          ${s.syncedAt ? "actualizada " + esc(s.syncedAt.replace("T", " ")) : "sin crear en Spotify"}${s.rules.daily ? " · cada día" : ""}</div></div></div>`).join("")
        || '<p class="muted" style="margin-top:0">Aún no tienes ninguna.</p>';
    };
    const presets = () => $("smEdit").innerHTML = `<div class="panel"><h2 class="sec" style="margin-top:0">Empieza con una plantilla</h2>
      <div class="presets">${PRESETS.map(([n, r], i) => `<button class="preset" data-i="${i}"><b>${esc(n)}</b>
        <span class="muted">${srcLabel(r)} ${esc(r.sources.map(k => SOURCES.find(x => x[0] === k)[2]).join(" + "))}</span></button>`).join("")}</div>
      <p class="legend">O pulsa «⚡ Nueva» y elige tú las fuentes.</p></div>`;
    await drawList();
    presets();
    $("smEdit").addEventListener("click", e => {
      const b = e.target.closest(".preset"); if (!b) return;
      const [name, r] = PRESETS[+b.dataset.i];
      edit({ name, rules: { ...DEFAULTS, ...r } });
    });
    $("smList").onclick = e => { const c = e.target.closest(".smartcard"); if (c) edit(items.find(s => s.id === +c.dataset.id)); };
    $("smNew").onclick = () => edit({ name: "", rules: { ...DEFAULTS } });

    function edit(item) {
      document.querySelectorAll(".smartcard").forEach(c => c.classList.toggle("sel", +c.dataset.id === item.id));
      const r = { ...DEFAULTS, sources: ["tags"], ...JSON.parse(JSON.stringify(item.rules)) };
      const stateOf = id => r.tagsAll.includes(id) ? "must" : r.tagsAny.includes(id) ? "any" : r.tagsNone.includes(id) ? "none" : "";
      $("smEdit").innerHTML = `<div class="panel">
        <input class="field" id="smName" placeholder="Nombre (p. ej. Gym a tope)" value="${esc(item.name)}" style="font:700 20px var(--display)">
        <div class="field-row" style="margin-bottom:6px"><label>Fuentes</label><span class="muted">elige una o varias: se mezclan alternándolas</span></div>
        <div class="sources" id="smSources">${SOURCES.map(([k, ic, t, d]) => `
          <button class="source ${r.sources.includes(k) ? "on" : ""}" data-k="${k}"><span class="ic">${ic}</span><b>${t}</b><span class="muted">${d}</span></button>`).join("")}</div>
        <div id="smParams"></div>
        <div class="field-row"><label>Orden</label>
          <select class="field" id="smOrder">${[["mix", "Mezclar fuentes"], ["random", "Al azar"], ["name", "Por título"]]
            .map(([v, t]) => `<option value="${v}" ${r.order === v ? "selected" : ""}>${t}</option>`).join("")}</select>
          <label style="min-width:auto">Máximo</label><input class="field short" type="number" id="smLimit" min="1" max="500" value="${r.limit}" style="width:90px">
          <label class="check"><input type="checkbox" id="smDaily" ${r.daily ? "checked" : ""}> Actualizar sola cada día</label></div>
        <div class="row-actions">
          <button class="btn acc" id="smSave">Guardar</button>
          ${item.id ? `<button class="btn" id="smSync">⟳ ${item.spotifyId ? "Actualizar" : "Crear"} en Spotify</button>` : ""}
          ${item.spotifyId ? `<a class="btn" href="https://open.spotify.com/playlist/${esc(item.spotifyId)}" target="_blank" rel="noopener">Abrir en Spotify</a>` : ""}
          ${item.id ? `<button class="btn danger" id="smDel">Borrar</button>` : ""}
        </div></div>
        <h2 class="sec">Vista previa <small id="smCount"></small></h2><div id="smPreview"></div>`;

      // Opciones que dependen de las fuentes marcadas.
      const params = () => {
        const has = (...k) => k.some(x => r.sources.includes(x));
        $("smParams").innerHTML = `
          ${has("top", "artists") ? `<div class="field-row"><label>Periodo</label><div class="seg" id="smRange">${[["short_term", "Último mes"], ["medium_term", "6 meses"], ["long_term", "Último año"]]
            .map(([v, t]) => `<button data-v="${v}" class="${r.range === v ? "on" : ""}">${t}</button>`).join("")}</div></div>` : ""}
          ${has("artists", "collab") ? `<div class="field-row"><label>Artistas</label><input class="field short" type="number" id="smArtists" min="1" max="20" value="${r.artists}" style="width:80px">
            <label class="check"><input type="checkbox" id="smOnlyNew" ${r.onlyNew ? "checked" : ""}> Solo canciones que no tengo</label></div>` : ""}
          ${has("genre") ? `<div class="field-row"><label>Géneros</label><input class="field" id="smGenres" placeholder="reggaeton, trap, flamenco…" value="${esc(r.genres)}" style="flex:1"></div>` : ""}
          ${has("liked_recent", "history") ? `<div class="field-row"><label>Últimos</label><input class="field short" type="number" id="smDays" min="1" max="365" value="${r.days}" style="width:80px"> días</div>` : ""}
          ${has("tags") ? `<div class="field-row"><label>Etiquetas</label><div class="chips" id="smTags">${State.tags.map(g => `
              <button class="chip ${stateOf(g.id)}" style="--tc:${g.color}" data-id="${g.id}"><span class="dot" style="color:${g.color}"></span>${esc(g.name)}</button>`).join("") || '<span class="muted">Aún no tienes etiquetas.</span>'}</div></div>
            <p class="legend">Pulsa una etiqueta: <b>relleno</b> = tiene que tenerla · <b>discontinuo</b> = vale con una · <b>tachado</b> = sin ella.</p>
            <div class="field-row"><label>Mínimo</label><div class="stars" id="smStars" style="margin:0">${[1, 2, 3, 4, 5].map(n => `<button class="${n <= r.minRating ? "on" : ""}" data-n="${n}">★</button>`).join("")}</div></div>` : ""}`;
        const on = (id, ev, fn) => { const el = $(id); if (el) el[ev] = fn; };
        on("smRange", "onclick", e => { const b = e.target.closest("button"); if (!b) return; r.range = b.dataset.v; params(); preview(); });
        on("smArtists", "onchange", () => { r.artists = Math.max(1, Math.min(20, +$("smArtists").value || 8)); preview(); });
        on("smOnlyNew", "onchange", () => { r.onlyNew = $("smOnlyNew").checked; preview(); });
        on("smGenres", "oninput", () => { r.genres = $("smGenres").value; preview(700); });
        on("smDays", "onchange", () => { r.days = Math.max(1, Math.min(365, +$("smDays").value || 30)); preview(); });
        on("smTags", "onclick", e => {
          const b = e.target.closest(".chip"); if (!b) return;
          const id = +b.dataset.id, next = STATES[(STATES.indexOf(stateOf(id)) + 1) % STATES.length];
          ["tagsAll", "tagsAny", "tagsNone"].forEach(k => r[k] = r[k].filter(x => x !== id));
          if (next) r[{ must: "tagsAll", any: "tagsAny", none: "tagsNone" }[next]].push(id);
          b.className = "chip " + next; preview();
        });
        on("smStars", "onclick", e => {
          const b = e.target.closest("button"); if (!b) return;
          r.minRating = r.minRating === +b.dataset.n ? 0 : +b.dataset.n;
          $("smStars").querySelectorAll("button").forEach(x => x.classList.toggle("on", +x.dataset.n <= r.minRating)); preview();
        });
      };

      let timer = null, seq = 0;
      const preview = (wait = 250) => {
        clearTimeout(timer);
        timer = setTimeout(async () => {
          const my = ++seq;
          if (!r.sources.length) { $("smCount").textContent = ""; $("smPreview").innerHTML = '<div class="empty">Elige al menos una fuente.</div>'; return; }
          $("smCount").textContent = "buscando canciones…";
          $("smPreview").style.opacity = .5;
          try {
            const tracks = await api("/api/smart/preview", { rules: r });
            if (my !== seq) return;  // llegó una vista previa más nueva
            $("smCount").textContent = plural(tracks.length, "canción", "canciones");
            tracks.length ? TrackList.render($("smPreview"), tracks, { showWhy: true })
                          : $("smPreview").innerHTML = '<div class="empty">Con estas opciones no sale ninguna canción.</div>';
          } catch (err) { if (my === seq) { $("smCount").textContent = ""; toast(err.message, true); } }
          $("smPreview").style.opacity = 1;
        }, wait);
      };

      $("smSources").onclick = e => {
        const b = e.target.closest(".source"); if (!b) return;
        const k = b.dataset.k;
        r.sources = r.sources.includes(k) ? r.sources.filter(x => x !== k) : [...r.sources, k];
        b.classList.toggle("on");
        params(); preview();
      };
      $("smOrder").onchange = () => { r.order = $("smOrder").value; preview(); };
      $("smLimit").onchange = () => { r.limit = Math.max(1, Math.min(500, +$("smLimit").value || 50)); preview(); };
      $("smDaily").onchange = () => { r.daily = $("smDaily").checked; };
      $("smSave").onclick = async () => {
        if (!r.sources.length) return toast("Elige al menos una fuente", true);
        try {
          const { id } = await api("/api/smart", { id: item.id, name: $("smName").value.trim(), rules: r });
          await drawList(id);
          edit(items.find(s => s.id === id));
          toast("Guardada. Pulsa «Crear en Spotify» para que aparezca en tu cuenta.");
        } catch (err) { toast(err.message, true); }
      };
      if (item.id) {
        $("smSync").onclick = async () => {
          const label = $("smSync").textContent;
          $("smSync").disabled = true; $("smSync").textContent = "Creando…";
          try {
            await api("/api/smart", { id: item.id, name: $("smName").value.trim() || item.name, rules: r });
            const res = await api("/api/smart/sync", { id: item.id });
            toast(`Listo: ${plural(res.tracks, "canción", "canciones")} en tu Spotify`);
            Lib.forget();
            await drawList(item.id);
            edit(items.find(s => s.id === item.id));
          } catch (err) { toast(err.message, true); $("smSync").disabled = false; $("smSync").textContent = label; }
        };
        $("smDel").onclick = async () => {
          if ($("smDel").dataset.sure !== "1") { $("smDel").dataset.sure = "1"; $("smDel").textContent = "¿Seguro? Pulsa otra vez"; return; }
          await api("/api/smart/delete", { id: item.id });
          await drawList();
          presets();
          toast("Borrada de myspoty. Si la creaste en Spotify, sigue allí: bórrala desde Playlists si quieres.");
        };
      }
      params();
      preview(0);
    }
  }

  /* ---------- Estadísticas ---------- */
  // Periodos de los tops oficiales de Spotify (su "short_term" son ~4 semanas y "long_term" ~1 año).
  const RANGES = [["short_term", "Último mes", "tu último mes"], ["medium_term", "Últimos 6 meses", "tus últimos 6 meses"],
                  ["long_term", "Último año", "tu último año"]];
  const ago = iso => {
    if (!iso) return "nunca";
    const min = Math.round((Date.now() - new Date(iso)) / 60000);
    return min < 1 ? "ahora mismo" : min < 60 ? `hace ${min} min` : min < 1440 ? `hace ${Math.round(min / 60)} h` : new Date(iso).toLocaleString("es-ES");
  };

  // Cada filtro recarga solo su sección (sin volver arriba ni recargar la otra).
  async function stats(stage) {
    stage.innerHTML = `<div class="kicker">según Spotify</div><div class="mega">Tus <span class="outline">números</span></div>
      <div class="row-actions" style="margin-bottom:6px">
        <span class="muted" id="stSync"></span>
        <button class="btn sm" id="stSyncBtn">⟳ Actualizar ahora</button>
      </div>
      <div class="seg big" id="stRange">${RANGES.map(([r, t], i) => `<button data-r="${r}" class="${i ? "" : "on"}">${t}</button>`).join("")}</div>
      <h2 class="sec" id="stTopTitle">Lo más escuchado en tu último mes <small>datos reales de Spotify, en todos tus dispositivos</small></h2>
      <div id="stTop"><div class="skeleton"></div></div>`;
    let range = "short_term";
    const pick = (seg, attr, value) => seg.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset[attr] === String(value)));
    $("stRange").onclick = e => { const b = e.target.closest("button"); if (!b) return; range = b.dataset.r; pick($("stRange"), "r", range); loadTop(range); };
    $("stSyncBtn").onclick = async () => {
      $("stSyncBtn").disabled = true; $("stSyncBtn").textContent = "Actualizando…";
      try { const r = await api("/api/stats/sync", {}); toast(`Actualizado: ${plural(r.newPlays, "escucha nueva", "escuchas nuevas")}`); await loadTop(range); }
      catch (e) { toast(e.message, true); }
      $("stSyncBtn").disabled = false; $("stSyncBtn").textContent = "⟳ Actualizar ahora";
    };
    await loadTop(range);
  }

  async function loadTop(range) {
    $("stTop").style.opacity = .5;
    const label = RANGES.find(r => r[0] === range)[2];
    $("stTopTitle").firstChild.textContent = `Lo más escuchado en ${label} `;
    // Para marcar como "nuevo" a quien no estaba en tu top del año.
    const [top, year] = await Promise.all([api(`/api/stats/top?range=${range}`),
      range === "long_term" ? null : api("/api/stats/top?range=long_term")]);
    top.yearIds = year ? new Set(year.artists.map(a => a.id)) : null;
    $("stSync").textContent = `Actualizado ${ago(top.lastSync?.at)} · se actualiza solo cada hora`;
    drawTop(top);
    $("stTop").style.opacity = 1;
  }

  function drawTop(top) {
    if (!top.artists.length && !top.tracks.length) {
      $("stTop").innerHTML = '<div class="empty">Aún no hay datos de Spotify. Pulsa «Actualizar ahora».</div>';
      return;
    }
    const isNew = a => top.yearIds && top.yearIds.size && !top.yearIds.has(a.id);
    const artistRow = (a, i) => `
      <div class="ar" data-uri="${esc(a.uri)}" title="Reproducir ${esc(a.name)}"><span class="n">${i + 1}</span>
        ${a.image ? `<img src="${esc(a.image)}" alt="" loading="lazy">` : "<i></i>"}
        <span class="nm">${esc(a.name)}</span>${isNew(a) ? '<span class="new">nuevo</span>' : ""}</div>`;
    $("stTop").innerHTML = `
      <div class="podium">${top.artists.slice(0, 3).map((a, i) => `
        <div class="pod p${i + 1}" data-uri="${esc(a.uri)}" title="Reproducir ${esc(a.name)}">
          <div class="pimg">${a.image ? `<img src="${esc(a.image)}" alt="">` : ""}<span>${i + 1}</span></div>
          <div class="t">${esc(a.name)}</div></div>`).join("")}</div>
      ${top.genres.length ? `<div class="chips" style="justify-content:center;margin:18px 0 6px">${top.genres.map((g, i) =>
        `<span class="chip ${i < 3 ? "on" : ""}">${esc(g)}</span>`).join("")}</div>` : ""}
      <div class="two" style="margin-top:26px">
        <div class="panel"><h2 class="sec" style="margin-top:0">Artistas <small>${top.artists.length}</small></h2>
          <div class="artists" id="stArtists">${top.artists.slice(3, 20).map((a, i) => artistRow(a, i + 3)).join("")}</div>
          ${top.artists.length > 20 ? '<button class="btn sm more" id="stArtMore">Ver todos</button>' : ""}
          ${top.yearIds ? '<p class="legend"><span class="new">nuevo</span> = no estaba en tu top del último año.</p>' : ""}</div>
        <div><h2 class="sec" style="margin-top:0">Canciones <small>${top.tracks.length}</small></h2><div id="stTopTracks"></div>
          ${top.tracks.length > 20 ? '<button class="btn sm more" id="stTrkMore">Ver las ' + top.tracks.length + "</button>" : ""}</div>
      </div>`;
    TrackList.render($("stTopTracks"), top.tracks.slice(0, 20));
    if ($("stArtMore")) $("stArtMore").onclick = () => {
      $("stArtists").insertAdjacentHTML("beforeend", top.artists.slice(20).map((a, i) => artistRow(a, i + 20)).join(""));
      $("stArtMore").remove();
    };
    if ($("stTrkMore")) $("stTrkMore").onclick = () => {
      TrackList.render($("stTopTracks"), top.tracks.slice(20), { append: true });
      $("stTrkMore").remove();
    };
    // Clic en un artista = ponerlo a sonar.
    $("stTop").querySelectorAll("[data-uri]").forEach(el => el.onclick = () => Player.playContext(el.dataset.uri));
  }

  return { tags, smart, stats };
})();

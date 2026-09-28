/* Popovers (etiquetas/valoración/nota y "añadir a playlist") y la lista de canciones reutilizable. */
const Pop = (() => {
  let onClose = null;
  function show(anchor, html) {
    const pop = $("pop");
    pop.innerHTML = html;
    pop.hidden = false;
    const r = anchor.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
    let left = Math.min(innerWidth - w - 12, Math.max(12, r.left + r.width / 2 - w / 2));
    let top = r.top - h - 10;
    if (top < 12) top = Math.min(innerHeight - h - 12, r.bottom + 10);
    pop.style.left = left + "px";
    pop.style.top = top + "px";
    return pop;
  }
  function close() { if ($("pop").hidden) return; $("pop").hidden = true; const fn = onClose; onClose = null; fn && fn(); }
  document.addEventListener("mousedown", e => { if (!$("pop").hidden && !$("pop").contains(e.target) && !e.target.closest("[data-pop]")) close(); });
  return { show, close, set onClose(fn) { onClose = fn; } };
})();

async function loadTags() { State.tags = await api("/api/tags"); return State.tags; }

/* Editor de tus datos sobre una canción: etiquetas, estrellas y nota. Guarda solo, al cambiar algo. */
const Editor = (() => {
  let track = null, meta = null, timer = null, after = null;

  async function open(t, anchor, onSaved) {
    track = t; after = onSaved;
    try { meta = (await api(`/api/tracks/meta?ids=${t.id}`))[t.id]; } catch (e) { return toast(e.message, true); }
    draw(anchor);
    Pop.onClose = () => { if (timer) { clearTimeout(timer); save(); } };
  }

  function draw(anchor) {
    const pop = Pop.show(anchor || $("pop"), `
      <h4>${esc(track.name)}</h4>
      <div class="sub">${esc(track.artists.join(", "))}</div>
      <div class="chips" id="edTags">${State.tags.map(g => `
        <button class="chip ${meta.tags.includes(g.id) ? "on" : ""}" style="--tc:${g.color}" data-id="${g.id}">
          <span class="dot" style="color:${g.color}"></span>${esc(g.name)}</button>`).join("") || '<span class="muted">Aún no tienes etiquetas: crea la primera.</span>'}</div>
      <form class="newtag" id="edNew">
        <input class="field" type="text" id="edName" placeholder="Nueva etiqueta" maxlength="40">
        <input type="color" id="edColor" value="${randomColor()}">
        <button class="btn sm acc">${ICON.plus}</button>
      </form>
      <div class="stars" id="edStars">${[1, 2, 3, 4, 5].map(n => `<button class="${n <= meta.rating ? "on" : ""}" data-n="${n}">★</button>`).join("")}</div>
      <textarea id="edNote" placeholder="Una nota para ti…" maxlength="500">${esc(meta.note)}</textarea>
      <div class="saved" id="edSaved"></div>`);
    pop.querySelectorAll("#edTags .chip").forEach(b => b.onclick = () => {
      const id = +b.dataset.id;
      meta.tags = meta.tags.includes(id) ? meta.tags.filter(x => x !== id) : [...meta.tags, id];
      b.classList.toggle("on");
      queueSave();
    });
    pop.querySelectorAll("#edStars button").forEach(b => b.onclick = () => {
      const n = +b.dataset.n;
      meta.rating = meta.rating === n ? 0 : n;  // pulsar la misma estrella la quita
      pop.querySelectorAll("#edStars button").forEach(x => x.classList.toggle("on", +x.dataset.n <= meta.rating));
      queueSave();
    });
    $("edNote").oninput = () => { meta.note = $("edNote").value; queueSave(800); };
    $("edNew").onsubmit = async e => {
      e.preventDefault();
      const name = $("edName").value.trim();
      if (!name) return;
      try {
        const { id } = await api("/api/tags", { name, color: $("edColor").value });
        await loadTags();
        meta.tags.push(id);
        queueSave(0);
        draw(null);
      } catch (err) { toast(err.message, true); }
    };
  }

  function queueSave(ms = 350) { clearTimeout(timer); timer = setTimeout(save, ms); }
  async function save() {
    timer = null;
    try {
      await api("/api/tracks/meta", { track, tags: meta.tags, rating: meta.rating, note: meta.note });
      const s = document.getElementById("edSaved");
      if (s) s.textContent = "Guardado ✓";
      TrackList.refreshMarks(track.id, meta);
      after && after(meta);
    } catch (e) { toast(e.message, true); }
  }
  return { open };
})();

function randomColor() {
  const c = ["#c6ff3d", "#ff3d8b", "#00d1c1", "#7a5cff", "#ffb13d", "#3da5ff", "#ff5c3d", "#3dff9e"];
  return c[Math.floor(Math.random() * c.length)];
}

/* Lista de canciones al estilo Spotify: selección (clic, Ctrl, Mayús), clic derecho, ⋯, Supr y doble clic para reproducir. */
const TrackList = (() => {
  const lists = new Map();  // contenedor -> {tracks, contextUri, liked, sel, anchor, opts}
  let active = null;        // última lista en la que has pulsado (para Supr, Enter y Ctrl+A)

  // opts: contextUri, append, numberFrom, showPlays (escuchas en vez del álbum),
  //       playlistId + own (permite "Quitar de esta playlist"), onRemove(tracks).
  function render(box, tracks, opts = {}) {
    let L = lists.get(box);
    if (!opts.append || !L) {
      L = { tracks: [], liked: {}, sel: new Set(), anchor: null, opts };
      lists.set(box, L); box.innerHTML = ""; box.classList.add("tracks");
    }
    const start = L.tracks.length;
    L.tracks.push(...tracks);
    box.insertAdjacentHTML("beforeend", tracks.map((t, k) => row(t, start + k, L.opts)).join(""));
    if (!box.dataset.bound) bind(box);
    decorate(box, tracks);
    markPlaying();
  }

  // Artistas y álbum son enlaces cuando se conocen sus ids (las canciones guardadas por myspoty no los traen).
  const artistLinks = t => t.artists.map((name, k) => t.artistIds?.[k]
    ? `<a class="lnk" href="/artist/${t.artistIds[k]}" data-link>${esc(name)}</a>` : esc(name)).join(", ");
  const albumLink = t => t.albumId ? `<a class="lnk" href="/album/${t.albumId}" data-link>${esc(t.album || "")}</a>` : esc(t.album || "");

  const row = (t, i, o) => `
    <div class="trk" data-i="${i}" data-id="${t.id}" data-uri="${esc(t.uri)}">
      <div class="n"><span class="num" data-num="${(o.numberFrom || 0) + i + 1}">${(o.numberFrom || 0) + i + 1}</span>
        <button class="rowplay" data-act="play" title="Reproducir">${ICON.play}</button></div>
      <img src="${esc(t.image || "")}" alt="" loading="lazy">
      <div style="min-width:0"><div class="tt">${esc(t.name)}</div><div class="ta">${artistLinks(t)}</div></div>
      ${o.showPlays ? `<div class="al playcount"><b>${t.plays}</b> ${t.plays === 1 ? "escucha" : "escuchas"} · ${fmtMin(t.minutes)}</div>`
        : o.showWhy ? `<div class="al why" title="De dónde sale">${esc(t.why || "")}</div>`
        : `<div class="al">${albumLink(t)}</div>`}
      <div class="marks"></div>
      <div class="d">${fmtMs(t.duration_ms)}</div>
      <div class="acts">
        <button data-act="like" title="Me gusta">${ICON.heart}</button>
        <button data-act="tag" data-pop title="Etiquetas y valoración">${ICON.tag}</button>
        <button data-act="more" title="Más opciones (o clic derecho)"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></button>
      </div>
    </div>`;

  /* ---------- selección ---------- */
  function select(box, i, { add = false, range = false } = {}) {
    const L = lists.get(box);
    if (range && L.anchor !== null) {
      const [a, b] = [Math.min(L.anchor, i), Math.max(L.anchor, i)];
      if (!add) L.sel.clear();
      for (let k = a; k <= b; k++) L.sel.add(k);
    } else if (add) {
      L.sel.has(i) ? L.sel.delete(i) : L.sel.add(i);
      L.anchor = i;
    } else {
      L.sel = new Set([i]);
      L.anchor = i;
    }
    paintSelection(box);
  }
  function paintSelection(box) {
    const L = lists.get(box);
    box.querySelectorAll(".trk").forEach(r => r.classList.toggle("sel", L.sel.has(+r.dataset.i)));
  }
  const selected = box => { const L = lists.get(box); return [...L.sel].sort((a, b) => a - b).map(i => L.tracks[i]).filter(Boolean); };
  function clearOthers(box) {
    lists.forEach((L, b) => { if (b !== box && L.sel.size) { L.sel.clear(); if (b.isConnected) paintSelection(b); } });
  }

  function menuFor(box, x, y, anchor) {
    const L = lists.get(box);
    Menu.open(x, y, trackMenu(selected(box), { box, anchor, playlistId: L.opts.playlistId, own: L.opts.own,
                                              onRemove: removed => removeRows(box, removed) }));
  }

  function bind(box) {
    box.dataset.bound = 1;
    box.addEventListener("click", e => {
      const r = e.target.closest(".trk");
      if (!r) return;
      active = box; clearOthers(box);
      const L = lists.get(box), i = +r.dataset.i, t = L.tracks[i];
      const btn = e.target.closest("[data-act]"), act = btn?.dataset.act;
      if (e.target.closest("a[data-link]")) return;  // enlace a artista/álbum: solo navegar
      if (act === "play") return Player.state?.track?.id === t.id ? Player.toggle() : play(box, i);
      if (act === "tag") return Editor.open(t, btn);
      if (act === "like") return like(box, t, btn);
      if (act === "more") {
        if (!L.sel.has(i)) select(box, i);
        const rc = btn.getBoundingClientRect();
        return menuFor(box, rc.left, rc.bottom + 6, btn);
      }
      if (e.detail === 2) return play(box, i);
      select(box, i, { add: e.ctrlKey || e.metaKey, range: e.shiftKey });
    });
    box.addEventListener("contextmenu", e => {
      const r = e.target.closest(".trk");
      if (!r) return;
      e.preventDefault();
      active = box; clearOthers(box);
      const L = lists.get(box), i = +r.dataset.i;
      if (!L.sel.has(i)) select(box, i);  // como en Spotify: si no estaba seleccionada, solo esa
      menuFor(box, e.clientX, e.clientY, r);
    });
    box.addEventListener("mousedown", e => { if (e.shiftKey && e.target.closest(".trk")) e.preventDefault(); });  // sin seleccionar texto
  }

  document.addEventListener("keydown", e => {
    if (!active || !active.isConnected || evEl(e).closest("input, textarea, select, .dialog") || Menu.isOpen || Palette.isOpen) return;
    const L = lists.get(active);
    if ((e.key === "Delete" || e.key === "Backspace") && L.sel.size && L.opts.own && L.opts.playlistId) {
      e.preventDefault();
      removeFromPlaylist(selected(active), { playlistId: L.opts.playlistId, onRemove: removed => removeRows(active, removed) });
    } else if (e.key === "Enter" && L.sel.size) {
      e.preventDefault(); play(active, Math.min(...L.sel));
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a") {
      e.preventDefault(); L.sel = new Set(L.tracks.map((_, i) => i)); paintSelection(active);
    }
  });
  // Clic fuera de las listas: se deselecciona todo.
  document.addEventListener("mousedown", e => {
    if (e.button !== 0 || evEl(e).closest(".tracks, .menu, .pop, .palette-bg, .dialog")) return;
    clearOthers(null);
  });

  /* ---------- quitar filas (tras "Quitar de esta playlist") ---------- */
  function removeRows(box, removed) {
    const L = lists.get(box);
    const uris = new Set(removed.map(t => t.uri));
    L.tracks = L.tracks.filter(t => !uris.has(t.uri));  // Spotify quita todas las apariciones de esa canción
    L.sel.clear(); L.anchor = null;
    box.innerHTML = L.tracks.map((t, i) => row(t, i, L.opts)).join("");
    decorate(box, L.tracks);
    markPlaying();
    L.opts.onRemove && L.opts.onRemove(removed);
  }

  /* ---------- reproducir y me gusta ---------- */
  function play(box, i) {
    const L = lists.get(box), t = L.tracks[i];
    if (L.opts.contextUri) return Player.playContext(L.opts.contextUri, t.uri);
    return Player.playUris(L.tracks.slice(i).map(x => x.uri));
  }
  const playTrack = (box, t) => play(box, lists.get(box).tracks.indexOf(t));

  async function like(box, t, btn) {
    const L = lists.get(box), want = !L.liked[t.id];
    L.liked[t.id] = want; btn.classList.toggle("liked", want);
    try { await setLiked(t.id, want); }
    catch (e) { L.liked[t.id] = !want; btn.classList.toggle("liked", !want); toast(e.message, true); }
  }
  function likedOf(box, tracks) {  // true si todas están en "me gusta", false si ninguna, null si mezcla
    const L = lists.get(box), v = tracks.map(t => !!L.liked[t.id]);
    return v.every(Boolean) ? true : v.some(Boolean) ? null : false;
  }
  function setLikedOf(box, tracks, want) {
    const L = lists.get(box);
    tracks.forEach(t => { L.liked[t.id] = want; box.querySelectorAll(`.trk[data-id="${t.id}"] [data-act=like]`).forEach(b => b.classList.toggle("liked", want)); });
  }

  /* ---------- marcas: me gusta, etiquetas, estrellas, escuchas ---------- */
  async function decorate(box, tracks) {
    const ids = [...new Set(tracks.map(t => t.id))];
    const L = lists.get(box);
    for (let i = 0; i < ids.length; i += 40) {
      const chunk = ids.slice(i, i + 40);
      likedContains(chunk).then(res => chunk.forEach((id, k) => {
        L.liked[id] = res[k];
        box.querySelectorAll(`.trk[data-id="${id}"] [data-act=like]`).forEach(b => b.classList.toggle("liked", res[k]));
      })).catch(() => {});
    }
    for (let i = 0; i < ids.length; i += 100) {
      api(`/api/tracks/meta?ids=${ids.slice(i, i + 100).join(",")}`).then(m => Object.entries(m).forEach(([id, v]) => refreshMarks(id, v))).catch(() => {});
    }
  }

  function refreshMarks(id, meta) {
    const dots = State.tags.filter(g => meta.tags.includes(g.id)).slice(0, 4)
      .map(g => `<span class="dot" style="color:${g.color}" title="${esc(g.name)}"></span>`).join("");
    const stars = meta.rating ? `<span class="stars-mini">${"★".repeat(meta.rating)}</span>` : "";
    const plays = meta.plays ? `<span class="plays" title="${meta.plays} ${meta.plays === 1 ? "vez escuchada" : "veces escuchada"} (historial de myspoty)">${meta.plays}×</span>` : "";
    document.querySelectorAll(`.trk[data-id="${id}"] .marks`).forEach(m => m.innerHTML = dots + stars + plays);
  }

  // La que suena: ecualizador en vez del número y botón de pausa al pasar el ratón.
  function markPlaying(st = Player.state) {
    const id = st?.track?.id;
    document.querySelectorAll(".trk").forEach(r => {
      const on = !!id && r.dataset.id === id, num = r.querySelector(".num"), btn = r.querySelector(".rowplay");
      r.classList.toggle("playing", on);
      if (on && !num.querySelector(".eq")) num.innerHTML = '<span class="eq"><i></i><i></i><i></i></span>';
      if (!on && num.querySelector(".eq")) num.textContent = num.dataset.num;
      if (on) num.querySelector(".eq").classList.toggle("paused", !!st.paused);
      const pause = on && !st.paused;
      btn.innerHTML = pause ? ICON.pause : ICON.play;
      btn.title = pause ? "Pausar" : "Reproducir";
    });
  }
  Player.onChange((st, onlyProgress) => { if (!onlyProgress) markPlaying(st); });

  return { render, refreshMarks, markPlaying, playAt: play, playTrack, likedOf, setLikedOf };
})();

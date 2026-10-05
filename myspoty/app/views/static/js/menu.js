/* Menús contextuales al estilo Spotify (clic derecho o botón ⋯) y las acciones sobre tu biblioteca. */

/* ---------- componente de menú con submenús ---------- */
const Menu = (() => {
  // items: [{ label, icon, run, sub: items | () => Promise<items>, danger, disabled, hint } | "sep"]
  const stack = [];  // menús abiertos (el principal y sus submenús)

  function open(x, y, items, level = 0) {
    closeFrom(level);
    const el = document.createElement("div");
    el.className = "menu";
    el.innerHTML = items.map((it, i) => it === "sep" ? '<div class="sep"></div>' : `
      <button class="${it.danger ? "danger" : ""}" data-i="${i}" ${it.disabled ? "disabled" : ""}>
        <span class="ic">${it.icon || ""}</span><span class="lb">${esc(it.label)}</span>
        ${it.sub ? '<span class="ar">›</span>' : it.hint ? `<span class="hint">${esc(it.hint)}</span>` : ""}</button>`).join("");
    document.body.appendChild(el);
    const w = el.offsetWidth, h = el.offsetHeight;
    el.style.left = Math.max(8, Math.min(x, innerWidth - w - 8)) + "px";
    el.style.top = Math.max(8, Math.min(y, innerHeight - h - 8)) + "px";
    stack[level] = el;
    let subTimer = null;
    el.addEventListener("mouseover", e => {
      const b = e.target.closest("button[data-i]");
      if (!b) return;
      clearTimeout(subTimer);
      const it = items[+b.dataset.i];
      subTimer = setTimeout(() => it.sub ? openSub(b, it, level) : closeFrom(level + 1), 120);
    });
    el.addEventListener("click", e => {
      const b = e.target.closest("button[data-i]");
      if (!b || b.disabled) return;
      const it = items[+b.dataset.i];
      if (it.sub) return openSub(b, it, level);
      close();
      it.run && it.run();
    });
    return el;
  }

  async function openSub(btn, it, level) {
    const r = btn.getBoundingClientRect();
    const items = typeof it.sub === "function" ? await it.sub() : it.sub;
    const sub = open(r.right - 4, r.top - 6, items, level + 1);
    if (r.right + sub.offsetWidth > innerWidth - 8) sub.style.left = Math.max(8, r.left - sub.offsetWidth + 4) + "px";
  }

  function closeFrom(level) { while (stack.length > level) stack.pop()?.remove(); }
  function close() { closeFrom(0); }
  const isOpen = () => stack.length > 0;

  document.addEventListener("mousedown", e => { if (isOpen() && !e.target.closest(".menu")) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && isOpen()) { e.stopPropagation(); close(); } }, true);
  window.addEventListener("blur", close);
  document.addEventListener("scroll", close, true);
  return { open, close, get isOpen() { return isOpen(); } };
})();

/* ---------- diálogo pequeño (nombre de playlist, confirmar…) ---------- */
const Ask = (() => {
  function show({ title, text = "", fields = [], ok = "Aceptar", danger = false }) {
    return new Promise(resolve => {
      const bg = document.createElement("div");
      bg.className = "palette-bg";
      bg.innerHTML = `<form class="palette dialog">
        <h3>${esc(title)}</h3>${text ? `<p class="muted">${esc(text)}</p>` : ""}
        ${fields.map((f, i) => f.area
          ? `<textarea class="field" name="f${i}" placeholder="${esc(f.placeholder || "")}" maxlength="300">${esc(f.value || "")}</textarea>`
          : `<input class="field" name="f${i}" placeholder="${esc(f.placeholder || "")}" value="${esc(f.value || "")}" maxlength="100">`).join("")}
        <div class="row-actions" style="justify-content:flex-end;margin-top:14px">
          <button type="button" class="btn" data-cancel>Cancelar</button>
          <button class="btn ${danger ? "danger" : "acc"}">${esc(ok)}</button></div></form>`;
      document.body.appendChild(bg);
      const form = bg.querySelector("form");
      const done = value => { bg.remove(); resolve(value); };
      form.onsubmit = e => {
        e.preventDefault();
        const values = fields.map((_, i) => form.elements["f" + i].value.trim());
        if (fields.length && !values[0]) return form.elements.f0.focus();
        done(fields.length ? values : true);
      };
      bg.querySelector("[data-cancel]").onclick = () => done(null);
      bg.onmousedown = e => { if (e.target === bg) done(null); };
      bg.onkeydown = e => { if (e.key === "Escape") { e.stopPropagation(); done(null); } };
      (form.elements.f0 || form.querySelector("button:not([data-cancel])")).focus();
    });
  }
  return { text: (title, placeholder, value) => show({ title, fields: [{ placeholder, value }] }).then(v => v && v[0]),
           confirm: (title, text, ok, danger = true) => show({ title, text, ok, danger }), show };
})();

/* ---------- acciones sobre tu biblioteca ---------- */
const Lib = (() => {
  let mine = null;  // tus playlists (para "Añadir a playlist")

  async function myPlaylists(force = false) {
    if (mine && !force) return mine;
    mine = [];
    let url = "/me/playlists?limit=50";
    while (url && mine.length < 500) {
      const page = await sp(url);
      mine.push(...page.items.filter(p => p && p.owner?.id === State.me?.id));
      url = page.next;
    }
    return mine;
  }
  const forget = () => { mine = null; };

  async function create(name, description = "") {
    const body = { name, public: false, description };
    const p = await spFirst(["/me/playlists", { method: "POST", body }],
                            [`/users/${State.me.id}/playlists`, { method: "POST", body }]);
    forget();
    return p;
  }

  async function addUris(playlistId, uris) {
    for (let i = 0; i < uris.length; i += 100) await addToPlaylist(playlistId, uris.slice(i, i + 100));
  }

  async function removeUris(playlistId, uris) {
    for (let i = 0; i < uris.length; i += 100) {
      const chunk = uris.slice(i, i + 100).map(uri => ({ uri }));
      await spFirst([`/playlists/${playlistId}/items`, { method: "DELETE", body: { items: chunk } }],
                    [`/playlists/${playlistId}/tracks`, { method: "DELETE", body: { tracks: chunk } }]);
    }
  }

  // Todas las canciones de una playlist o álbum (para copiarlas a otra playlist o a la cola).
  async function urisOf(kind, id, max = 10000) {
    const uris = [];
    let url = kind === "playlist" ? `/playlists/${id}/items?limit=100&fields=next,items(item(uri,is_local))`
                                  : `/albums/${id}/tracks?limit=50`;
    while (url && uris.length < max) {
      const page = await sp(url);
      page.items.forEach(i => { const t = i.item || i.track || i; if (t?.uri && !t.is_local && t.uri.startsWith("spotify:track:")) uris.push(t.uri); });
      url = page.next;
    }
    return uris.slice(0, max);
  }

  async function queueMany(uris) {
    for (const uri of uris) await sp("/me/player/queue", { method: "POST", params: { uri } });
  }

  const libraryUri = (kind, id) => `spotify:${kind}:${id}`;
  const saveToLibrary = (kind, id, want) => spFirst(
    ["/me/library", { method: want ? "PUT" : "DELETE", params: { uris: libraryUri(kind, id) } }],
    kind === "album" ? [`/me/albums`, { method: want ? "PUT" : "DELETE", params: { ids: id } }]
                     : [`/playlists/${id}/followers`, { method: want ? "PUT" : "DELETE" }]);
  const inLibrary = async (kind, id) => (await sp("/me/library/contains", { params: { uris: libraryUri(kind, id) } }))[0];

  const link = (kind, id) => `https://open.spotify.com/${kind}/${id}`;
  async function copyLink(kind, id) {
    try { await navigator.clipboard.writeText(link(kind, id)); toast("Enlace copiado"); }
    catch { toast(link(kind, id)); }
  }

  return { myPlaylists, forget, create, addUris, removeUris, urisOf, queueMany, saveToLibrary, inLibrary, link, copyLink };
})();

/* ---------- menús de cada tipo ---------- */
const ICONS = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z" fill="currentColor" stroke="none"/></svg>',
  queue: '<svg viewBox="0 0 24 24"><path d="M3 6h13M3 12h13M3 18h8M18 15v6M15 18h6"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  heart: '<svg viewBox="0 0 24 24"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>',
  minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg>',
  artist: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
  album: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/></svg>',
  tag: '<svg viewBox="0 0 24 24"><path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/></svg>',
  share: '<svg viewBox="0 0 24 24"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13"/></svg>',
  edit: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
  open: '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4 10 14M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>',
};

const cnt = n => plural(n, "canción", "canciones");

// Submenú "Añadir a playlist": nueva playlist + tus playlists. `getUris` puede ser asíncrono (playlist/álbum entero).
function addToPlaylistSub(getUris, excludeId = null) {
  return async () => {
    let list;
    try { list = await Lib.myPlaylists(); } catch (e) { toast(e.message, true); return []; }
    const run = async (target, isNew) => {
      try {
        const uris = await getUris();
        if (!uris.length) return toast("No hay canciones que añadir", true);
        await Lib.addUris(target.id, uris);
        toast(`${cnt(uris.length)} ${isNew ? "en tu nueva playlist" : "añadidas a"} «${target.name}»`);
      } catch (e) { toast(e.message, true); }
    };
    return [
      { label: "Nueva playlist…", icon: ICONS.plus, run: async () => {
          const name = await Ask.text("Nueva playlist", "Nombre de la playlist");
          if (!name) return;
          try { await run(await Lib.create(name), true); } catch (e) { toast(e.message, true); }
        } },
      "sep",
      ...list.filter(p => p.id !== excludeId).map(p => ({ label: p.name, run: () => run(p, false) })),
    ];
  };
}

const goArtist = async t => {
  let ids = t.artistIds;
  if (!ids?.length) { try { ids = (await sp(`/tracks/${t.id}`)).artists.map(a => a.id); } catch (e) { return toast(e.message, true); } }
  return ids;
};

/* Canciones (una o varias seleccionadas). ctx: {playlistId, own, onRemove, box} */
function trackMenu(tracks, ctx = {}) {
  const one = tracks.length === 1 ? tracks[0] : null;
  const uris = tracks.map(t => t.uri);
  const liked = ctx.box ? TrackList.likedOf(ctx.box, tracks) : null;  // true / false / null (mezcla)
  const items = [
    { label: one ? "Reproducir" : `Reproducir ${cnt(tracks.length)}`, icon: ICONS.play,
      run: () => one && ctx.box ? TrackList.playTrack(ctx.box, one) : Player.playUris(uris) },
    { label: "Añadir a la cola", icon: ICONS.queue, run: async () => {
        try { await Lib.queueMany(uris); toast(`${cnt(uris.length)} en la cola`); } catch (e) { toast(e.message, true); } } },
    "sep",
    { label: "Añadir a playlist", icon: ICONS.plus, sub: addToPlaylistSub(() => uris, ctx.playlistId) },
    { label: liked ? "Quitar de Tus me gusta" : "Guardar en Tus me gusta", icon: ICONS.heart, run: async () => {
        const want = !liked;
        try { for (const t of tracks) await setLiked(t.id, want); toast(want ? "Guardado en Tus me gusta" : "Quitado de Tus me gusta");
              ctx.box && TrackList.setLikedOf(ctx.box, tracks, want); }
        catch (e) { toast(e.message, true); } } },
  ];
  if (ctx.own && ctx.playlistId) items.push({ label: "Quitar de esta playlist", icon: ICONS.minus, danger: true, hint: "Supr",
    run: () => removeFromPlaylist(tracks, ctx) });
  if (one) {
    items.push("sep",
      { label: "Ir al artista", icon: ICONS.artist, sub: async () => {
          const ids = await goArtist(one);
          return (ids || []).map((id, i) => ({ label: one.artists[i] || "Artista", run: () => go(`/artist/${id}`) }));
        } },
      { label: "Ir al álbum", icon: ICONS.album, disabled: !one.albumId, run: () => go(`/album/${one.albumId}`) },
      { label: "Etiquetas y valoración…", icon: ICONS.tag, run: () => Editor.open(one, ctx.anchor || $("tagBtn")) },
      "sep",
      { label: "Compartir", icon: ICONS.share, sub: [
          { label: "Copiar enlace de la canción", icon: ICONS.copy, run: () => Lib.copyLink("track", one.id) },
          { label: "Abrir en Spotify", icon: ICONS.open, run: () => window.open(Lib.link("track", one.id), "_blank", "noopener") },
        ] });
  }
  return items;
}

async function removeFromPlaylist(tracks, ctx) {
  const ok = await Ask.confirm(tracks.length === 1 ? `¿Quitar «${tracks[0].name}»?` : `¿Quitar ${cnt(tracks.length)}?`,
    "Se quitarán de esta playlist en tu Spotify (no de Tus me gusta).", "Quitar");
  if (!ok) return;
  try {
    await Lib.removeUris(ctx.playlistId, [...new Set(tracks.map(t => t.uri))]);
    toast(tracks.length === 1 ? "Quitada de la playlist" : `${cnt(tracks.length)} quitadas`);
    ctx.onRemove && ctx.onRemove(tracks);
  } catch (e) { toast(e.message, true); }
}

/* Playlists. p: {id, uri, name, description, own} */
function playlistMenu(p) {
  const all = () => Lib.urisOf("playlist", p.id);
  const items = [
    { label: "Reproducir", icon: ICONS.play, run: () => Player.playContext(p.uri) },
    { label: "Añadir a la cola", icon: ICONS.queue, hint: "primeras 50", run: async () => {
        try { const uris = await Lib.urisOf("playlist", p.id, 50); await Lib.queueMany(uris); toast(`${cnt(uris.length)} en la cola`); }
        catch (e) { toast(e.message, true); } } },
    "sep",
    { label: "Añadir a otra playlist", icon: ICONS.plus, sub: addToPlaylistSub(all, p.id) },
    { label: "Duplicar como playlist nueva", icon: ICONS.copy, run: async () => {
        const name = await Ask.text("Duplicar playlist", "Nombre", `${p.name} (copia)`);
        if (!name) return;
        try { const uris = await all(); const np = await Lib.create(name, p.description || ""); await Lib.addUris(np.id, uris);
              toast(`Creada «${name}» con ${cnt(uris.length)}`); if (location.pathname === "/playlists") go("/playlists"); }
        catch (e) { toast(e.message, true); } } },
  ];
  if (p.own) items.push({ label: "Editar detalles…", icon: ICONS.edit, run: () => editPlaylist(p) });
  items.push("sep",
    { label: "Compartir", icon: ICONS.share, sub: [
        { label: "Copiar enlace de la playlist", icon: ICONS.copy, run: () => Lib.copyLink("playlist", p.id) },
        { label: "Abrir en Spotify", icon: ICONS.open, run: () => window.open(Lib.link("playlist", p.id), "_blank", "noopener") },
      ] },
    { label: p.own ? "Eliminar playlist…" : "Quitar de tu biblioteca", icon: ICONS.trash, danger: true, run: async () => {
        const ok = await Ask.confirm(p.own ? `¿Eliminar «${p.name}»?` : `¿Quitar «${p.name}» de tu biblioteca?`,
          p.own ? "Desaparecerá de tu biblioteca de Spotify. (Spotify la guarda y puedes recuperarla desde tu cuenta.)" : "", p.own ? "Eliminar" : "Quitar");
        if (!ok) return;
        try { await Lib.saveToLibrary("playlist", p.id, false); Lib.forget(); toast("Hecho"); go("/playlists"); }
        catch (e) { toast(e.message, true); } } });
  return items;
}

async function editPlaylist(p) {
  const v = await Ask.show({ title: "Editar detalles", ok: "Guardar",
    fields: [{ placeholder: "Nombre", value: p.name }, { placeholder: "Descripción (opcional)", value: p.description || "", area: true }] });
  if (!v) return;
  try {
    await sp(`/playlists/${p.id}`, { method: "PUT", body: { name: v[0], description: v[1] } });
    Lib.forget();
    toast("Playlist actualizada");
    window.dispatchEvent(new Event("myspoty:navigate"));  // recarga la vista actual
  } catch (e) { toast(e.message, true); }
}

/* Álbumes. a: {id, uri, name, artistIds, artists} */
function albumMenu(a) {
  return [
    { label: "Reproducir", icon: ICONS.play, run: () => Player.playContext(a.uri) },
    { label: "Añadir a la cola", icon: ICONS.queue, run: async () => {
        try { const uris = await Lib.urisOf("album", a.id); await Lib.queueMany(uris); toast(`${cnt(uris.length)} en la cola`); }
        catch (e) { toast(e.message, true); } } },
    { label: "Añadir a playlist", icon: ICONS.plus, sub: addToPlaylistSub(() => Lib.urisOf("album", a.id)) },
    { label: "Guardar / quitar de tu biblioteca", icon: ICONS.heart, run: async () => {
        try { const has = await Lib.inLibrary("album", a.id); await Lib.saveToLibrary("album", a.id, !has);
              toast(has ? "Álbum quitado de tu biblioteca" : "Álbum guardado en tu biblioteca"); }
        catch (e) { toast(e.message, true); } } },
    "sep",
    { label: "Ir al álbum", icon: ICONS.album, run: () => go(`/album/${a.id}`) },
    ...(a.artistIds?.length ? [{ label: "Ir al artista", icon: ICONS.artist, sub: a.artistIds.map((id, i) => ({ label: a.artists?.[i] || "Artista", run: () => go(`/artist/${id}`) })) }] : []),
    { label: "Copiar enlace del álbum", icon: ICONS.copy, run: () => Lib.copyLink("album", a.id) },
  ];
}

function artistMenu(a) {
  return [
    { label: "Reproducir", icon: ICONS.play, run: () => Player.playContext(a.uri) },
    { label: "Ir al artista", icon: ICONS.artist, run: () => go(`/artist/${a.id}`) },
    { label: "Copiar enlace del artista", icon: ICONS.copy, run: () => Lib.copyLink("artist", a.id) },
  ];
}

/* Clic derecho en tarjetas y cabeceras marcadas con data-ctx (playlist, album, artist). */
const CtxData = new Map();  // clave "tipo:id" -> datos para el menú
function ctxAttrs(kind, data) {
  CtxData.set(`${kind}:${data.id}`, data);
  return `data-ctx="${kind}" data-ctx-id="${esc(data.id)}"`;
}
function openCtx(el, x, y) {
  const kind = el.dataset.ctx, data = CtxData.get(`${kind}:${el.dataset.ctxId}`);
  if (!data) return;
  Menu.open(x, y, kind === "playlist" ? playlistMenu(data) : kind === "album" ? albumMenu(data) : artistMenu(data));
}
document.addEventListener("contextmenu", e => {
  const el = e.target.closest("[data-ctx]");
  if (!el) return;
  e.preventDefault();
  openCtx(el, e.clientX, e.clientY);
});
document.addEventListener("click", e => {  // botones "⋯" de cabeceras y tarjetas
  const b = e.target.closest("[data-ctx-btn]");
  if (!b) return;
  e.preventDefault(); e.stopPropagation();
  const el = b.closest("[data-ctx]") || document.querySelector(b.dataset.ctxBtn);
  const r = b.getBoundingClientRect();
  if (el) openCtx(el, r.left, r.bottom + 6);
}, true);

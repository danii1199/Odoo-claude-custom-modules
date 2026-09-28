/* Vistas de música: Inicio, Playlists, una playlist y Tus me gusta. */
const Views = (() => {
  const skeleton = (n = 6) => `<div>${'<div class="skeleton"></div>'.repeat(n)}</div>`;
  const firstName = () => (State.me?.name || "").split(" ")[0];

  function greeting() {
    const h = new Date().getHours();
    return h < 6 ? "Buenas noches" : h < 14 ? "Buenos días" : h < 21 ? "Buenas tardes" : "Buenas noches";
  }

  // Tarjeta con vinilo. Sin `href` no abre nada (p. ej. álbumes, que no tienen vista propia): solo se reproduce.
  const card = ({ href, image, title, sub, playUri, ph = "♪", ctx = "" }) => `
    <${href ? `a class="card" href="${esc(href)}" data-link` : 'div class="card"'} ${ctx}>
      <div class="sleeve"><div class="vinyl"></div>
        ${image ? `<img src="${esc(image)}" alt="" loading="lazy">` : `<div class="ph">${ph}</div>`}
        ${playUri ? `<button class="play-fab" data-play="${esc(playUri)}" title="Reproducir">${ICON.play}</button>` : ""}
      </div>
      <div class="t">${esc(title)}</div><div class="s">${esc(sub || "")}</div>
    </${href ? "a" : "div"}>`;

  // Botón de play de las tarjetas (sin abrir la playlist).
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-play]");
    if (!b) return;
    e.preventDefault(); e.stopPropagation();
    Player.playContext(b.dataset.play);
  }, true);

  /* ---------- Inicio ---------- */
  async function home(stage) {
    stage.innerHTML = `
      <div class="kicker">${new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })}</div>
      <div class="mega">${greeting()},<br><span class="acc">${esc(firstName() || "tú")}</span><span class="outline">.</span></div>
      <h2 class="sec">Sigue escuchando</h2><div class="strip" id="recent">${skeleton(1)}</div>
      <h2 class="sec">Tu mes en bucle <small>lo que más te ha sonado estas semanas</small></h2><div id="top">${skeleton(5)}</div>
      <h2 class="sec">Atajos</h2>
      <div class="row-actions">
        <button class="btn acc" onclick="Palette.open()">Buscar <kbd>Ctrl</kbd>+<kbd>K</kbd></button>
        <a class="btn" href="/liked" data-link>${ICON.heart} Tus me gusta</a>
        <a class="btn" href="/smart" data-link>⚡ Playlists inteligentes</a>
      </div>`;
    sp("/me/player/recently-played", { params: { limit: 30 } }).then(r => {
      const seen = new Set(), items = [];
      for (const it of r.items) {
        const key = it.context?.uri || it.track.album.uri;
        if (seen.has(key)) continue;
        seen.add(key);
        items.push(it);
      }
      $("recent").innerHTML = items.slice(0, 12).map(it => {
        const ctx = it.context?.uri || it.track.album.uri, img = pickImage(it.track.album.images);
        const isPl = ctx.startsWith("spotify:playlist:"), id = ctx.split(":").pop(), alb = it.track.album;
        const menu = isPl ? ctxAttrs("playlist", { id, uri: ctx, name: "Playlist", own: false })
                          : ctxAttrs("album", { id: alb.id, uri: alb.uri, name: alb.name, artistIds: alb.artists.map(a => a.id), artists: alb.artists.map(a => a.name) });
        return card({ href: isPl ? `/playlist/${id}` : `/album/${alb.id}`, image: img, ctx: menu,
                      title: isPl ? "Playlist" : alb.name, sub: it.track.artists.map(a => a.name).join(", "), playUri: ctx });
      }).join("") || '<div class="empty">Aún no hay nada reciente.</div>';
    }).catch(e => $("recent").innerHTML = `<div class="empty">${esc(e.message)}</div>`);
    sp("/me/top/tracks", { params: { time_range: "short_term", limit: 10 } }).then(r => {
      const tracks = r.items.map(trackFrom).filter(Boolean);
      if (!tracks.length) return $("top").innerHTML = '<div class="empty">Escucha un poco más y aquí aparecerán tus favoritas.</div>';
      TrackList.render($("top"), tracks);
    }).catch(e => $("top").innerHTML = `<div class="empty">${esc(e.message)}</div>`);
  }

  /* ---------- Playlists ---------- */
  async function playlists(stage) {
    stage.innerHTML = `<div class="kicker">tu colección</div><div class="mega">Play<span class="outline">lists</span></div>
      <div class="row-actions" style="margin:-8px 0 22px"><button class="btn acc" id="plNew">${ICON.plus} Nueva playlist</button>
        <span class="muted">Clic derecho en una playlist para más opciones</span></div>
      <div class="grid" id="plGrid">${card({ href: "/liked", title: "Tus me gusta", sub: "Tus canciones guardadas", ph: "♥" })}</div>
      <div id="plMore"></div>`;
    $("plNew").onclick = async () => {
      const name = await Ask.text("Nueva playlist", "Nombre de la playlist");
      if (!name) return;
      try { const p = await Lib.create(name); toast(`Creada «${name}»`); go(`/playlist/${p.id}`); } catch (e) { toast(e.message, true); }
    };
    try {
      let url = "/me/playlists?limit=50", n = 0;
      while (url) {
        const page = await sp(url);
        $("plGrid").insertAdjacentHTML("beforeend", page.items.filter(Boolean).map(p => card({
          href: `/playlist/${p.id}`, image: pickImage(p.images), title: p.name, playUri: p.uri,
          ctx: ctxAttrs("playlist", { id: p.id, uri: p.uri, name: p.name, description: p.description, own: p.owner?.id === State.me?.id }),
          // Spotify renombró "tracks" a "items" en 2025; se leen los dos por si acaso.
          sub: p.owner?.id === State.me?.id ? plural((p.items || p.tracks)?.total ?? 0, "canción", "canciones") : `de ${p.owner?.display_name || "otro usuario"}`,
        })).join(""));
        n += page.items.length;
        url = page.next;
        if (n >= 500) break;
      }
    } catch (e) { $("plMore").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  /* ---------- Una playlist ---------- */
  async function playlist(stage, id) {
    stage.innerHTML = skeleton(8);
    let p;
    try { p = await sp(`/playlists/${id}`, { params: { fields: "id,uri,name,description,images,owner(id,display_name),items(total),tracks(total)" } }); }
    catch (e) {
      stage.innerHTML = `<div class="empty">${e.status === 404 || e.status === 403
        ? "Spotify no deja a las apps nuevas abrir esta playlist (le pasa a las creadas por Spotify, como los «Mix» o «Descubrimiento semanal»)."
        : esc(e.message)}</div>`;
      return;
    }
    const img = pickImage(p.images, 600);
    if (img) Aura.set(img);
    const own = p.owner?.id === State.me?.id;
    let total = (p.items || p.tracks)?.total ?? 0;
    const menu = ctxAttrs("playlist", { id: p.id, uri: p.uri, name: p.name, description: p.description, own });
    stage.innerHTML = `
      <div class="hero" ${menu}>
        ${img ? `<img src="${esc(img)}" alt="">` : '<div class="ph"></div>'}
        <div><div class="kicker">playlist · ${esc(p.owner?.display_name || "")}</div>
          <div class="mega">${esc(p.name)}</div>
          ${p.description ? `<p class="muted">${esc(new DOMParser().parseFromString(p.description, "text/html").body.textContent)}</p>` : ""}
          <div class="row-actions">
            <button class="btn acc" id="plPlay">${ICON.play} Reproducir</button>
            <button class="btn icon-only" data-ctx-btn title="Más opciones"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></button>
            <span class="muted" id="plInfo">${plural(total, "canción", "canciones")}</span>
          </div></div>
      </div>
      <div id="plTracks"></div><button class="btn more" id="plLoad" hidden>Cargar más</button>`;
    $("plPlay").onclick = () => Player.playContext(p.uri);
    let url = `/playlists/${id}/items?limit=100&fields=next,items(item(id,uri,name,duration_ms,artists(id,name),album(id,name,images)))`;
    const load = async append => {
      try {
        const page = await sp(url);
        TrackList.render($("plTracks"), page.items.map(i => trackFrom(i.item || i.track)).filter(Boolean), {
          contextUri: p.uri, append, playlistId: p.id, own,
          onRemove: removed => { total -= removed.length; $("plInfo").textContent = plural(total, "canción", "canciones"); } });
        url = page.next;
        $("plLoad").hidden = !url;
      } catch (e) { toast(e.message, true); }
    };
    $("plLoad").onclick = () => load(true);
    load(false);
  }

  /* ---------- Tus me gusta ---------- */
  async function liked(stage) {
    stage.innerHTML = `<div class="kicker">guardadas</div><div class="mega">Tus <span class="acc">me gusta</span></div>
      <div class="row-actions"><button class="btn acc" id="lkPlay">${ICON.play} Reproducir</button><span class="muted" id="lkInfo"></span></div>
      <h2 class="sec"></h2><div id="lkTracks">${skeleton(8)}</div><button class="btn more" id="lkLoad" hidden>Cargar más</button>`;
    let url = "/me/tracks?limit=50";
    const load = async append => {
      try {
        const page = await sp(url);
        if (!append) $("lkInfo").textContent = plural(page.total, "canción", "canciones");
        TrackList.render($("lkTracks"), page.items.map(i => trackFrom(i.track)).filter(Boolean), { append });
        url = page.next;
        $("lkLoad").hidden = !url;
      } catch (e) { $("lkTracks").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
    };
    $("lkPlay").onclick = () => TrackList.playAt($("lkTracks"), 0);
    $("lkLoad").onclick = () => load(true);
    load(false);
  }

  /* ---------- Álbum ---------- */
  async function album(stage, id) {
    stage.innerHTML = skeleton(8);
    let a;
    try { a = await sp(`/albums/${id}`); } catch (e) { stage.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const img = pickImage(a.images, 600);
    if (img) Aura.set(img);
    const menu = ctxAttrs("album", { id: a.id, uri: a.uri, name: a.name, artistIds: a.artists.map(x => x.id), artists: a.artists.map(x => x.name) });
    const tracks = a.tracks.items.map(t => trackFrom(t, a)).filter(Boolean);
    const mins = Math.round(tracks.reduce((s, t) => s + t.duration_ms, 0) / 60000);
    stage.innerHTML = `
      <div class="hero" ${menu}>
        ${img ? `<img src="${esc(img)}" alt="">` : '<div class="ph"></div>'}
        <div><div class="kicker">${a.album_type === "single" ? "sencillo" : "álbum"} · ${esc((a.release_date || "").slice(0, 4))}</div>
          <div class="mega">${esc(a.name)}</div>
          <p>${a.artists.map(x => `<a href="/artist/${x.id}" data-link class="artist-link">${esc(x.name)}</a>`).join(", ")}
            <span class="muted"> · ${plural(a.total_tracks, "canción", "canciones")}, ${fmtMin(mins)}</span></p>
          <div class="row-actions">
            <button class="btn acc" id="alPlay">${ICON.play} Reproducir</button>
            <button class="btn icon-only" data-ctx-btn title="Más opciones"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></button>
          </div></div>
      </div><div id="alTracks"></div><button class="btn more" id="alLoad" hidden>Cargar más</button>`;
    $("alPlay").onclick = () => Player.playContext(a.uri);
    TrackList.render($("alTracks"), tracks, { contextUri: a.uri });
    let next = a.tracks.next;
    $("alLoad").hidden = !next;
    $("alLoad").onclick = async () => {
      const page = await sp(next);
      TrackList.render($("alTracks"), page.items.map(t => trackFrom(t, a)).filter(Boolean), { append: true });
      next = page.next; $("alLoad").hidden = !next;
    };
  }

  /* ---------- Artista ---------- */
  async function artist(stage, id) {
    stage.innerHTML = skeleton(6);
    let ar;
    try { ar = await sp(`/artists/${id}`); } catch (e) { stage.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const img = pickImage(ar.images, 600);
    if (img) Aura.set(img);
    const menu = ctxAttrs("artist", { id: ar.id, uri: ar.uri, name: ar.name });
    stage.innerHTML = `
      <div class="hero artist-hero" ${menu}>
        ${img ? `<img src="${esc(img)}" alt="">` : '<div class="ph"></div>'}
        <div><div class="kicker">artista</div><div class="mega">${esc(ar.name)}</div>
          <div class="row-actions">
            <button class="btn acc" id="arPlay">${ICON.play} Reproducir</button>
            <button class="btn icon-only" data-ctx-btn title="Más opciones"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></button>
          </div></div>
      </div>
      <div id="arMine"></div>
      <h2 class="sec">Discografía</h2>
      <div class="seg" id="arGroups"><button data-g="album,single" class="on">Todo</button><button data-g="album">Álbumes</button><button data-g="single">Sencillos y EP</button></div>
      <div class="grid" id="arAlbums" style="margin-top:18px"></div><button class="btn more" id="arMore" hidden>Cargar más</button>`;
    $("arPlay").onclick = () => Player.playContext(ar.uri);
    // Tus canciones favoritas de este artista, sacadas de tus tops (Spotify no deja ver sus "populares").
    api("/api/stats/top?range=long_term").then(async t => {
      const seen = new Set(), mine = [];
      for (const r of ["short_term", "medium_term"]) (await api(`/api/stats/top?range=${r}`)).tracks.forEach(x => t.tracks.push(x));
      t.tracks.forEach(x => { if (x.artists.includes(ar.name) && !seen.has(x.id)) { seen.add(x.id); mine.push(x); } });
      if (!mine.length) return;
      $("arMine").innerHTML = `<h2 class="sec">Tus favoritas de ${esc(ar.name)} <small>de tus tops</small></h2><div id="arMineList"></div>`;
      TrackList.render($("arMineList"), mine.slice(0, 10));
    }).catch(() => {});
    let url;
    const load = async append => {
      const page = await sp(url);
      const cards = page.items.filter(Boolean).map(al => card({ href: `/album/${al.id}`, image: pickImage(al.images), title: al.name,
        sub: `${(al.release_date || "").slice(0, 4)} · ${al.album_type === "single" ? "Sencillo" : "Álbum"}`, playUri: al.uri,
        ctx: ctxAttrs("album", { id: al.id, uri: al.uri, name: al.name, artistIds: al.artists.map(x => x.id), artists: al.artists.map(x => x.name) }) })).join("");
      append ? $("arAlbums").insertAdjacentHTML("beforeend", cards) : $("arAlbums").innerHTML = cards || '<div class="empty">Nada por aquí.</div>';
      url = page.next; $("arMore").hidden = !url;
    };
    const group = g => { url = `/artists/${id}/albums?limit=24&include_groups=${g}`; load(false).catch(e => toast(e.message, true)); };
    $("arGroups").onclick = e => { const b = e.target.closest("button"); if (!b) return;
      $("arGroups").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b)); group(b.dataset.g); };
    $("arMore").onclick = () => load(true);
    group("album,single");
  }

  return { home, playlists, playlist, liked, album, artist, card };
})();

/* Reproductor: Web Playback SDK (tu navegador como dispositivo "myspoty") + control remoto de otros dispositivos. */
const Player = (() => {
  const RING = 2 * Math.PI * 29;
  let sdk = null, deviceId = null, activated = false;
  let st = null;            // estado normalizado: {track, paused, position, duration, shuffle, repeat, device, next, local, at}
  let liked = false, trackId = null;
  const listeners = [];

  /* ---------- SDK ---------- */
  // Por http://IP (otro PC de casa) el navegador no puede reproducir: Spotify exige HTTPS o 127.0.0.1.
  const canPlayHere = window.isSecureContext;

  function init() {
    $("ringFg").style.strokeDasharray = RING;
    bindControls();
    setInterval(tick, 1000);
    setInterval(() => { if (!st?.local) refreshRemote(); }, 5000);
    if (!canPlayHere) { refreshRemote(); return; }  // solo mando a distancia de tus otros dispositivos
    window.onSpotifyWebPlaybackSDKReady = () => {
      sdk = new Spotify.Player({ name: "myspoty", volume: $("vol").value / 100,
                                 getOAuthToken: cb => Token.get().then(cb).catch(() => {}) });
      sdk.addListener("ready", ({ device_id }) => { deviceId = device_id; refreshRemote(); });
      sdk.addListener("not_ready", () => { deviceId = null; });
      sdk.addListener("account_error", () => toast("Para reproducir aquí hace falta Spotify Premium.", true));
      sdk.addListener("authentication_error", () => { Token.reset(); toast("Spotify ha rechazado la sesión; vuelve a entrar.", true); });
      sdk.addListener("initialization_error", ({ message }) => toast("El navegador no puede reproducir: " + message, true));
      sdk.addListener("player_state_changed", s => s && fromLocal(s));
      sdk.connect();
    };
    const s = document.createElement("script");
    s.src = "https://sdk.scdn.co/spotify-player.js";
    document.head.appendChild(s);
  }

  function fromLocal(s) {
    const cur = s.track_window.current_track;
    set({ track: trackFrom(cur), paused: s.paused, position: s.position, duration: s.duration,
          shuffle: s.shuffle, repeat: s.repeat_mode, device: { name: "este navegador", id: deviceId },
          next: s.track_window.next_tracks.map(trackFrom).filter(Boolean), local: true });
  }

  async function refreshRemote() {
    try {
      const p = await sp("/me/player", { params: { additional_types: "track" } });
      if (!p || !p.item) { if (!st?.local) set(null); return; }
      if (p.device?.id === deviceId && sdk) return;  // lo lleva el SDK
      set({ track: trackFrom(p.item), paused: !p.is_playing, position: p.progress_ms, duration: p.item.duration_ms,
            shuffle: p.shuffle_state, repeat: { off: 0, context: 1, track: 2 }[p.repeat_state] || 0,
            device: p.device, next: [], local: false });
    } catch (e) { /* sin sesión o sin conexión: se reintenta en el siguiente ciclo */ }
  }

  function set(next) {
    const prevId = trackId;
    st = next ? { ...next, at: Date.now() } : null;
    trackId = st?.track?.id || null;
    if (trackId !== prevId) onTrackChange();
    render();
  }

  async function onTrackChange() {
    liked = false;
    if (!trackId) return;
    Aura.set(st.track.image && st.track.image.replace(/ab67616d0000(1e02|4851)/, "ab67616d0000b273"));
    try { liked = (await likedContains([trackId]))[0]; } catch {}
    render();
  }

  /* posición actual interpolada */
  const position = () => !st ? 0 : st.paused ? st.position : Math.min(st.duration, st.position + (Date.now() - st.at));

  // El historial lo trae el servidor desde Spotify cada hora (incluye otros dispositivos).
  function tick() { if (st) render(true); }

  /* ---------- dibujar ---------- */
  function render(onlyProgress = false) {
    const pos = position(), dur = st?.duration || 0;
    $("ringFg").style.strokeDashoffset = RING * (1 - (dur ? pos / dur : 0));
    $("npTime").textContent = `${fmtMs(pos)} / ${fmtMs(dur)}`;
    listeners.forEach(fn => fn(st, onlyProgress, pos));
    if (onlyProgress) return;
    const t = st?.track;
    $("dock").classList.toggle("is-playing", !!st && !st.paused);
    $("npTitle").textContent = t ? t.name : "Nada sonando";
    $("npArtist").innerHTML = t ? esc(t.artists.join(", ")) : "Pulsa <kbd>Ctrl</kbd>+<kbd>K</kbd> para buscar algo";
    $("npImg").src = t?.image || "";
    $("npImg").style.visibility = t?.image ? "visible" : "hidden";
    $("playIcon").innerHTML = st && !st.paused ? '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>' : '<path d="M7 4v16l13-8z"/>';
    $("shuffleBtn").classList.toggle("on", !!st?.shuffle);
    $("repeatBtn").classList.toggle("on", !!st?.repeat);
    $("repeatBtn").title = ["Repetir: no", "Repetir: lista", "Repetir: canción"][st?.repeat || 0];
    $("likeBtn").classList.toggle("on", liked);
    $("npDevice").innerHTML = st && !st.local && st.device
      ? `Sonando en ${esc(st.device.name)}${canPlayHere ? ' · <button id="hereBtn">escuchar aquí</button>' : ""}`
      : !canPlayHere ? "Mando a distancia: abre Spotify en otro dispositivo" : "";
    const here = document.getElementById("hereBtn");
    if (here) here.onclick = e => { e.stopPropagation(); transferHere(); };
    document.title = t ? `${t.name} · ${t.artists[0] || ""} — myspoty` : "myspoty";
  }

  /* ---------- acciones ---------- */
  function activate() {  // el navegador exige un gesto del usuario antes de sonar
    if (sdk && !activated) { sdk.activateElement?.(); activated = true; }
  }
  const target = () => (deviceId ? { device_id: deviceId } : {});

  async function run(fn) {
    try { await fn(); setTimeout(refreshRemote, 600); }
    catch (e) {
      if (e.status === 404) toast(canPlayHere ? "No hay ningún dispositivo activo. Espera un segundo a que myspoty esté listo o abre Spotify."
                                              : "Abre Spotify en tu móvil u ordenador: desde esta dirección myspoty lo controla, pero el navegador no puede sonar (necesita HTTPS).", true);
      else if (e.status === 403) toast("Spotify no permite esa acción ahora mismo (¿tienes Premium?).", true);
      else toast(e.message, true);
    }
  }

  function play(body) { activate(); return run(() => sp("/me/player/play", { method: "PUT", params: target(), body })); }
  const playUris = (uris, offset = 0) => play({ uris: uris.slice(0, 300), offset: { position: offset } });
  const playContext = (context_uri, uri) => play(uri ? { context_uri, offset: { uri } } : { context_uri });

  function toggle() {
    activate();
    if (!st) return toast("Elige algo que escuchar (Ctrl+K para buscar).");
    if (st.local && sdk) return sdk.togglePlay();
    return run(() => sp(st.paused ? "/me/player/play" : "/me/player/pause", { method: "PUT" }));
  }
  const next = () => st?.local && sdk ? sdk.nextTrack() : run(() => sp("/me/player/next", { method: "POST" }));
  const prev = () => st?.local && sdk ? sdk.previousTrack() : run(() => sp("/me/player/previous", { method: "POST" }));
  function seek(ms) {
    if (!st) return;
    ms = Math.max(0, Math.min(st.duration, ms));
    st.position = ms; st.at = Date.now(); render(true);
    return st.local && sdk ? sdk.seek(ms) : run(() => sp("/me/player/seek", { method: "PUT", params: { position_ms: Math.round(ms) } }));
  }
  const shuffle = () => run(() => sp("/me/player/shuffle", { method: "PUT", params: { state: !st?.shuffle } }));
  const repeat = () => run(() => sp("/me/player/repeat", { method: "PUT", params: { state: ["context", "track", "off"][st?.repeat || 0] } }));
  const queue = uri => run(async () => { await sp("/me/player/queue", { method: "POST", params: { uri, ...target() } }); toast("Añadida a la cola"); });
  const transferHere = () => deviceId
    ? run(() => sp("/me/player", { method: "PUT", body: { device_ids: [deviceId], play: true } }))
    : toast("myspoty aún se está preparando…");

  async function toggleLike() {
    if (!trackId) return;
    const want = !liked;
    liked = want; render();
    try { await setLiked(trackId, want); toast(want ? "Guardada en Tus me gusta" : "Quitada de Tus me gusta"); }
    catch (e) { liked = !want; render(); toast(e.message, true); }
  }

  function bindControls() {
    $("playBtn").onclick = toggle;
    $("nextBtn").onclick = next;
    $("prevBtn").onclick = prev;
    $("shuffleBtn").onclick = shuffle;
    $("repeatBtn").onclick = repeat;
    $("likeBtn").onclick = toggleLike;
    $("tagBtn").onclick = e => st?.track ? Editor.open(st.track, e.currentTarget) : toast("No suena nada");
    $("nowBtn").onclick = () => Now.toggle();
    $("npOpen").onclick = () => st?.track && Now.toggle();
    $("ring").onclick = e => {  // clic en el anillo = saltar a esa posición
      const r = e.currentTarget.getBoundingClientRect();
      let ang = Math.atan2(e.clientY - (r.top + r.height / 2), e.clientX - (r.left + r.width / 2)) + Math.PI / 2;
      if (ang < 0) ang += 2 * Math.PI;
      if (st) seek(st.duration * ang / (2 * Math.PI));
    };
    let vt = null;
    $("vol").oninput = () => {
      const v = +$("vol").value;
      if (st?.local && sdk) return sdk.setVolume(v / 100);
      clearTimeout(vt);
      vt = setTimeout(() => run(() => sp("/me/player/volume", { method: "PUT", params: { volume_percent: v } })), 250);
    };
  }

  return { init, playUris, playContext, toggle, next, prev, seek, queue, toggleLike, position, shuffle, repeat,
           get state() { return st; }, get liked() { return liked; }, onChange: fn => listeners.push(fn) };
})();

/* Pantalla completa "Ahora suena": portada y controles a la izquierda, letra sincronizada a la derecha. */
const Now = (() => {
  let open = false, shownId = null, lines = [], lastIdx = -2, following = true, raf = null, lyricsFor = null;
  const el = () => $("now");
  const I = {
    shuffle: '<svg viewBox="0 0 24 24"><path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>',
    prev: '<svg viewBox="0 0 24 24"><path d="M19 20 9 12l10-8zM5 19V5"/></svg>',
    next: '<svg viewBox="0 0 24 24"><path d="m5 4 10 8-10 8zM19 5v14"/></svg>',
    repeat: '<svg viewBox="0 0 24 24"><path d="m17 2 4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/></svg>',
    sync: '<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/></svg>',
  };

  function toggle(force) {
    open = force ?? !open;
    el().hidden = !open;
    document.body.classList.toggle("now-open", open);
    shownId = null;
    cancelAnimationFrame(raf);
    if (open) { draw(Player.state); raf = requestAnimationFrame(loop); }
  }

  function draw(st) {
    const t = st?.track;
    if (!t) { el().innerHTML = `<button class="btn sm close" onclick="Now.toggle(false)">${ICON.close} Cerrar</button><div class="empty">No suena nada.</div>`; return; }
    shownId = t.id;
    const big = t.image?.replace(/ab67616d0000(1e02|4851)/, "ab67616d0000b273");
    el().innerHTML = `
      <button class="btn sm close" onclick="Now.toggle(false)">${ICON.close} Cerrar</button>
      <div class="now-left">
        <div class="cover3d" id="cover3d"><img src="${esc(big || "")}" alt=""></div>
        <div class="now-meta">
          <div class="kicker">${st.local ? "sonando aquí" : "sonando en " + esc(st.device?.name || "otro dispositivo")}</div>
          <div class="now-title">${esc(t.name)}</div>
          <div class="artist">${esc(t.artists.join(", "))}</div>
        </div>
        <div class="bar" id="nowBar"><i id="nowFill"></i></div>
        <div class="times"><span id="nowPos">0:00</span><span id="nowDur">${fmtMs(st.duration)}</span></div>
        <div class="now-ctrl">
          <button id="nShuffle" title="Aleatorio">${I.shuffle}</button>
          <button id="nPrev" title="Anterior">${I.prev}</button>
          <button id="nPlay" class="big" title="Reproducir / pausa (espacio)"></button>
          <button id="nNext" title="Siguiente">${I.next}</button>
          <button id="nRepeat" title="Repetir">${I.repeat}</button>
        </div>
        <div class="now-acts">
          <button id="nLike" title="Me gusta (L)">${ICON.heart}</button>
          <button id="nTag" title="Etiquetas y valoración (T)">${ICON.tag}</button>
          <span class="muted" id="nNextUp"></span>
        </div>
        <div class="mine" id="nowMine"></div>
      </div>
      <div class="now-right">
        <div class="lyrics" id="lyr"><div class="lyr-status">Buscando la letra…</div></div>
        <button class="btn sync-lyr" id="lyrSync" hidden>${I.sync} Sincronizar</button>
      </div>`;
    $("nPlay").onclick = () => Player.toggle();
    $("nPrev").onclick = () => Player.prev();
    $("nNext").onclick = () => Player.next();
    $("nShuffle").onclick = () => Player.shuffle();
    $("nRepeat").onclick = () => Player.repeat();
    $("nLike").onclick = () => Player.toggleLike();
    $("nTag").onclick = e => Editor.open(t, e.currentTarget, () => mine(t));
    $("nowBar").onclick = e => { const r = e.currentTarget.getBoundingClientRect(); Player.seek(st.duration * (e.clientX - r.left) / r.width); };
    const cover = $("cover3d");
    $("now").querySelector(".now-left").onmousemove = e => {
      const r = cover.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      cover.style.setProperty("--ry", `${x * 16}deg`); cover.style.setProperty("--rx", `${-y * 16}deg`);
    };
    // Letra: si el usuario la mueve a mano deja de seguir la canción hasta que pulse "Sincronizar".
    const lyr = $("lyr");
    const stopFollowing = () => { if (lines.length && following) { following = false; $("lyrSync").hidden = false; } };
    lyr.addEventListener("wheel", stopFollowing, { passive: true });
    lyr.addEventListener("touchmove", stopFollowing, { passive: true });
    lyr.addEventListener("mousedown", e => { if (e.target === lyr) stopFollowing(); });  // arrastrar la barra de scroll
    lyr.onclick = e => {
      const p = e.target.closest("p[data-t]");
      if (p) { Player.seek(+p.dataset.t); resync(); }
    };
    $("lyrSync").onclick = resync;
    controls(st);
    mine(t);
    loadLyrics(t, st.duration);
  }

  function resync() {
    following = true;
    $("lyrSync").hidden = true;
    lastIdx = -2;  // fuerza a recolocar en el siguiente fotograma
  }

  function controls(st) {
    if (!$("nPlay")) return;
    $("nPlay").innerHTML = st && !st.paused ? ICON.pause : ICON.play;
    $("nShuffle").classList.toggle("on", !!st?.shuffle);
    $("nRepeat").classList.toggle("on", !!st?.repeat);
    $("nRepeat").title = ["Repetir: no", "Repetir: lista", "Repetir: canción"][st?.repeat || 0];
    $("nLike").classList.toggle("on", Player.liked);
    const nx = st?.next?.[0];
    $("nNextUp").textContent = nx ? `Siguiente: ${nx.name} · ${nx.artists[0] || ""}` : "";
  }

  // "[01:02.34] texto" -> [{t: ms, text}] (una línea puede llevar varias marcas).
  function parseLRC(text) {
    const out = [];
    for (const raw of text.split(/\r?\n/)) {
      const tags = [...raw.matchAll(/\[(\d+):(\d+(?:\.\d+)?)\]/g)];
      if (!tags.length) continue;
      const words = raw.replace(/\[[^\]]*\]/g, "").trim();
      tags.forEach(m => out.push({ t: Math.round((+m[1] * 60 + +m[2]) * 1000), text: words }));
    }
    return out.sort((a, b) => a.t - b.t);
  }

  async function loadLyrics(t, duration) {
    lines = []; lastIdx = -2; following = true; lyricsFor = t.id;
    const qs = new URLSearchParams({ id: t.id, name: t.name, artist: t.artists[0] || "", album: t.album || "", duration_ms: duration || t.duration_ms || "" });
    let res;
    try { res = await api("/api/lyrics?" + qs); }
    catch (e) { if (lyricsFor === t.id) $("lyr").innerHTML = `<div class="lyr-status">${esc(e.message)}</div>`; return; }
    if (lyricsFor !== t.id || !$("lyr")) return;  // cambió de canción mientras tanto
    if (res.synced) {
      lines = parseLRC(res.synced);
      $("lyr").innerHTML = `<div class="lyr-pad"></div>` + lines.map((l, i) =>
        `<p data-i="${i}" data-t="${l.t}">${esc(l.text) || "♪"}</p>`).join("") + `<div class="lyr-pad"></div>`
        + '<div class="lyr-src">Letra: LRCLIB</div>';
    } else if (res.plain) {
      $("lyr").innerHTML = `<div class="lyr-status small">Letra sin sincronizar</div>`
        + res.plain.split(/\r?\n/).map(l => `<p class="plain">${esc(l) || "&nbsp;"}</p>`).join("") + '<div class="lyr-src">Letra: LRCLIB</div>';
    } else {
      $("lyr").innerHTML = res.retry ? `<div class="lyr-status">El servicio de letras está saturado.<br><span class="muted">Vuelve a abrir la pantalla completa en un momento.</span></div>`
                                     : `<div class="lyr-status">No hay letra para esta canción.<br><span class="muted">(Puede ser instrumental o no estar aún en LRCLIB.)</span></div>`;
    }
  }

  // Cada fotograma: progreso y línea actual de la letra.
  function loop() {
    raf = requestAnimationFrame(loop);
    const st = Player.state;
    if (!st || !$("nowFill")) return;
    const pos = Player.position();
    $("nowFill").style.width = `${Math.min(100, (pos / (st.duration || 1)) * 100)}%`;
    $("nowPos").textContent = fmtMs(pos);
    if (!lines.length) return;
    let idx = -1;
    for (let i = 0; i < lines.length && lines[i].t <= pos + 250; i++) idx = i;  // 250 ms de adelanto, como Spotify
    if (idx === lastIdx) return;
    lastIdx = idx;
    const ps = $("lyr").querySelectorAll("p[data-i]");
    ps.forEach((p, i) => { p.classList.toggle("on", i === idx); p.classList.toggle("past", i < idx); });
    if (following && idx >= 0) {
      const box = $("lyr"), p = ps[idx];
      box.scrollTo({ top: p.offsetTop - box.clientHeight / 2 + p.clientHeight / 2, behavior: "smooth" });
    }
  }

  Player.onChange((st, onlyProgress) => {
    if (!open || onlyProgress) return;
    if (st?.track?.id !== shownId) return draw(st);
    controls(st);
  });

  async function mine(t) {
    try {
      const m = (await api(`/api/tracks/meta?ids=${t.id}`))[t.id];
      const tags = State.tags.filter(g => m.tags.includes(g.id));
      if (!$("nowMine")) return;
      $("nowMine").innerHTML = (tags.length || m.rating) ? `
        <div class="chips">${tags.map(g => `<span class="chip on" style="--tc:${g.color}">${esc(g.name)}</span>`).join("")}
        ${m.rating ? `<span class="stars-mini" style="font-size:16px">${"★".repeat(m.rating)}</span>` : ""}</div>` : "";
    } catch {}
  }

  return { toggle, get open() { return open; } };
})();

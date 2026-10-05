/* Arranque: comprueba la sesión, enseña la entrada o la app, rutas sin recarga y atajos de teclado. */
const ROUTES = [
  [/^\/$/, () => Views.home],
  [/^\/playlists$/, () => Views.playlists],
  [/^\/playlist\/([A-Za-z0-9]+)$/, () => Views.playlist],
  [/^\/liked$/, () => Views.liked],
  [/^\/album\/([A-Za-z0-9]+)$/, () => Views.album],
  [/^\/artist\/([A-Za-z0-9]+)$/, () => Views.artist],
  [/^\/tags$/, () => Organize.tags],
  [/^\/smart$/, () => Organize.smart],
  [/^\/stats$/, () => Organize.stats],
];

function route() {
  Pop.close();
  Menu.close();
  if (Now.open) Now.toggle(false);
  const path = location.pathname;
  const found = ROUTES.find(([rx]) => rx.test(path)) || ROUTES[0];
  const params = path.match(found[0])?.slice(1) || [];
  document.querySelectorAll(".rail a[data-link]:not(.logo)").forEach(a => {
    const href = a.getAttribute("href");
    a.classList.toggle("on", href === "/" ? path === "/" : path.startsWith(href.replace(/s$/, "")));
  });
  const stage = $("stage");
  stage.scrollTop = 0;
  found[1]()(stage, ...params).catch?.(e => stage.innerHTML = `<div class="empty">${esc(e.message)}</div>`);
}
window.addEventListener("myspoty:navigate", route);
window.addEventListener("popstate", route);

function showGate(status) {
  $("gate").hidden = false;
  if (!status.configured) {
    $("loginBtn").hidden = true;
    $("gateText").textContent = "Falta un paso para conectar con Spotify.";
    $("setup").hidden = false;
    $("setup").innerHTML = `
      <b>Configura tu app de Spotify</b>
      <ol>
        <li>En <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener">developer.spotify.com/dashboard</a>, abre tu app.</li>
        <li>Comprueba que la <i>Redirect URI</i> es exactamente <code>${esc(status.redirectUri)}</code>.</li>
        <li>Pega el <i>Client ID</i> en el archivo <code>.env</code> de la carpeta <code>myspoty</code>, detrás de <code>SPOTIFY_CLIENT_ID=</code>.</li>
        <li>Recrea el contenedor: <code>docker compose up -d --force-recreate</code> y recarga esta página.</li>
      </ol>`;
  }
  // Spotify solo vuelve del login a las direcciones registradas: desde otra (p. ej. otro PC por http://IP) se entra con código.
  const canLogin = status.redirectUris.some(u => new URL(u).host === location.host);
  if (!canLogin && status.configured) {
    $("loginBtn").hidden = true;
    $("gateText").textContent = "Desde esta dirección Spotify no deja iniciar sesión: entra con un código de un dispositivo donde ya tengas myspoty abierto.";
  }
  $("devForm").onsubmit = async e => {
    e.preventDefault();
    try { await api("/api/device/login", { code: $("devCode").value }); location.href = "/"; }
    catch (err) { toast(err.message, true); }
  };
  if (new URLSearchParams(location.search).get("login") === "cancelado") toast("Has cancelado el inicio de sesión en Spotify.", true);
}

function userMenu(anchor) {
  const me = State.me || {};
  const pop = Pop.show(anchor, `<h4>${esc(me.name || "")}</h4>
    <div class="sub">Cuenta ${me.product === "premium" ? "Premium ✓" : esc(me.product || "")}</div>
    ${me.product && me.product !== "premium" ? '<p class="muted" style="font-size:13px">Para reproducir en myspoty hace falta Premium; lo demás funciona igual.</p>' : ""}
    <div class="list"><button id="devBtn">📱 Conectar otro dispositivo</button>
      <button id="liteBtn">${Lite.on ? "✓ " : ""}Modo ligero (para equipos lentos)</button>
      <button id="logoutBtn">Cerrar sesión en este dispositivo</button></div>`);
  pop.querySelector("#devBtn").onclick = async () => {
    Pop.close();
    try {
      const { code, minutes } = await api("/api/device/code", {});
      Ask.show({ title: "Conectar otro dispositivo", ok: "Hecho",
        text: `Abre myspoty en el otro dispositivo y escribe este código en la pantalla de entrada. Sirve una vez durante ${minutes} minutos.` })
        .then(() => {});
      setTimeout(() => document.querySelector(".dialog h3")?.insertAdjacentHTML("afterend", `<div class="bigcode">${code.slice(0, 3)} ${code.slice(3)}</div>`), 0);
    } catch (e) { toast(e.message, true); }
  };
  pop.querySelector("#liteBtn").onclick = () => { const on = Lite.toggle(); Pop.close(); toast(on ? "Modo ligero activado en este equipo" : "Modo ligero desactivado en este equipo"); };
  pop.querySelector("#logoutBtn").onclick = async () => { await api("/api/logout", {}); location.href = "/"; };
}

document.addEventListener("keydown", e => {
  const typing = evEl(e).closest("input, textarea, select");
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); return Palette.isOpen ? Palette.close() : Palette.open(); }
  if (e.key === "Escape") { Pop.close(); if (Palette.isOpen) Palette.close(); else if (Now.open) Now.toggle(false); return; }
  if (evEl(e).closest(".dialog")) return;
  if (typing || Palette.isOpen || $("app").hidden) return;
  if (e.key === " ") { e.preventDefault(); Player.toggle(); }
  else if (e.key === "ArrowRight" && e.shiftKey) Player.next();
  else if (e.key === "ArrowLeft" && e.shiftKey) Player.prev();
  else if (e.key === "ArrowRight") Player.seek(Player.position() + 10000);
  else if (e.key === "ArrowLeft") Player.seek(Player.position() - 10000);
  else if (e.key.toLowerCase() === "l") Player.toggleLike();
  else if (e.key.toLowerCase() === "f") Now.toggle();
  else if (e.key.toLowerCase() === "t" && Player.state?.track) Editor.open(Player.state.track, $("tagBtn"));
});

(async () => {
  Lite.init();
  let status;
  try { status = await api("/api/status"); } catch (e) { return toast("No se puede hablar con el servidor de myspoty.", true); }
  if (!status.loggedIn || !status.configured) return showGate(status);
  if (location.search.includes("login=")) history.replaceState({}, "", location.pathname);
  State.me = status.user;
  $("app").hidden = false;
  $("dock").hidden = false;
  $("avatar").src = status.user?.image || "";
  $("userBtn").onclick = e => userMenu(e.currentTarget);
  $("userBtn").setAttribute("data-pop", "");
  $("searchBtn").onclick = () => Palette.open();
  await loadTags().catch(() => {});
  Player.init();
  route();
})();

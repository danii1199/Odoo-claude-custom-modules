/* Utilidades compartidas: DOM, llamadas a tu servidor y a Spotify, formato, avisos y colores del aura. */
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fmtMs = ms => { const s = Math.max(0, Math.floor((ms || 0) / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
// Elemento que recibió un evento (a veces es el propio documento, que no tiene .closest).
const evEl = e => (e.target instanceof Element ? e.target : document.body);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const fmtMin = m => m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min` : `${m} min`;

const State = { me: null, tags: [] };  // usuario de Spotify y tus etiquetas

const ICON = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>',
  heart: '<svg viewBox="0 0 24 24"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>',
  tag: '<svg viewBox="0 0 24 24"><path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};

function toast(text, isError = false) {
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " err" : "");
  el.textContent = text;
  $("toasts").appendChild(el);
  setTimeout(() => el.remove(), isError ? 6000 : 3000);
}

/* Tu servidor (datos propios). */
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} :
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json().catch(() => null);
  if (!r.ok) throw new Error(data?.error || `Error ${r.status}`);
  return data;
}

/* Spotify Web API, directamente desde el navegador con el token que da tu servidor. */
const Token = (() => {
  let tok = null, exp = 0, pending = null;
  async function get() {
    if (tok && Date.now() / 1000 < exp - 60) return tok;
    pending = pending || api("/api/token").then(t => { tok = t.accessToken; exp = t.expiresAt; return tok; }).finally(() => pending = null);
    return pending;
  }
  return { get, reset() { tok = null; exp = 0; } };
})();

async function sp(path, { method = "GET", body, params, retry = 1 } = {}) {
  const url = new URL(path.startsWith("http") ? path : "https://api.spotify.com/v1" + path);
  Object.entries(params || {}).forEach(([k, v]) => v !== undefined && v !== null && url.searchParams.set(k, v));
  const r = await fetch(url, { method, headers: { Authorization: "Bearer " + await Token.get(), "Content-Type": "application/json" },
                               body: body === undefined ? undefined : JSON.stringify(body) });
  if (r.status === 401 && retry) { Token.reset(); return sp(path, { method, body, params, retry: 0 }); }
  if (r.status === 429) {  // exceso de peticiones: solo se espera si es poco (a veces Spotify pide horas)
    const wait = +r.headers.get("Retry-After") || 1;
    if (retry && wait <= 10) { await sleep(wait * 1000); return sp(path, { method, body, params, retry: 0 }); }
    const err = new Error(`Spotify ha limitado esta consulta por exceso de peticiones (${wait > 3600 ? Math.round(wait / 3600) + " h" : Math.ceil(wait / 60) + " min"}).`);
    err.status = 429;
    throw err;
  }
  if (r.status === 204) return null;
  const text = await r.text();
  const data = text ? (() => { try { return JSON.parse(text); } catch { return null; } })() : null;
  if (!r.ok) {
    const err = new Error(data?.error?.message || `Spotify respondió ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return data;
}

/* Spotify está migrando su API (2025): primero la dirección nueva y, si la rechaza, la antigua. */
async function spFirst(...calls) {
  let last;
  for (const [path, opts] of calls) {
    try { return await sp(path, opts); }
    catch (e) { last = e; if (![400, 403, 404, 405].includes(e.status)) throw e; }
  }
  throw last;
}
// ¿Están en "Tus me gusta"? (ids de canciones -> [true/false])
const likedContains = ids => spFirst(
  ["/me/library/contains", { params: { uris: ids.map(id => "spotify:track:" + id).join(",") } }],
  ["/me/tracks/contains", { params: { ids: ids.join(",") } }]);
// Guardar o quitar de "Tus me gusta".
const setLiked = (id, want) => spFirst(
  ["/me/library", { method: want ? "PUT" : "DELETE", params: { uris: "spotify:track:" + id } }],
  ["/me/tracks", { method: want ? "PUT" : "DELETE", params: { ids: id } }]);
// Añadir canciones a una playlist.
const addToPlaylist = (playlistId, uris) => spFirst(
  [`/playlists/${playlistId}/items`, { method: "POST", body: { uris } }],
  [`/playlists/${playlistId}/tracks`, { method: "POST", body: { uris } }]);

/* Canción de Spotify -> formato propio (el que guarda tu servidor). */
function pickImage(images, size = 300) {
  if (!images?.length) return null;
  return ([...images].sort((a, b) => (a.width || 0) - (b.width || 0)).find(i => (i.width || 0) >= size) || images[0]).url;
}
function trackFrom(t, album = null) {
  if (!t || !t.id) return null;
  const alb = t.album || album;  // las canciones de un álbum vienen sin su álbum: se pasa aparte
  return { id: t.id, uri: t.uri, name: t.name, artists: (t.artists || []).map(a => a.name),
           artistIds: (t.artists || []).map(a => a.id), album: alb?.name || null, albumId: alb?.id || null,
           image: pickImage(alb?.images), duration_ms: t.duration_ms || 0 };
}

/* Colores dominantes de una portada para el aura del fondo. */
const Aura = (() => {
  let last = null;
  function toHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
    if (max === min) return [0, 0, l];
    const d = max - min, s = l > .5 ? d / (2 - max - min) : d / (max + min);
    const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [h * 60, s, l];
  }
  async function set(url) {
    if (!url || url === last) return;
    last = url;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = url;
    try { await img.decode(); } catch { return; }
    const c = document.createElement("canvas");
    c.width = c.height = 28;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, 28, 28);
    let px;
    try { px = ctx.getImageData(0, 0, 28, 28).data; } catch { return; }  // portada sin CORS: se queda el aura anterior
    const buckets = {};
    for (let i = 0; i < px.length; i += 4) {
      const [h, s, l] = toHsl(px[i], px[i + 1], px[i + 2]);
      if (l < .12 || l > .92) continue;
      const k = Math.round(h / 30) % 12, w = .3 + s;
      const bk = buckets[k] || (buckets[k] = { w: 0, h: 0, s: 0 });
      bk.w += w; bk.h += h * w; bk.s += s * w;
    }
    const top = Object.values(buckets).sort((a, b) => b.w - a.w).slice(0, 3)
      .map(b => `hsl(${Math.round(b.h / b.w)} ${Math.round(Math.min(95, 35 + (b.s / b.w) * 70))}% 52%)`);
    while (top.length < 3) top.push(top[0] || "hsl(260 80% 55%)");
    ["--c1", "--c2", "--c3"].forEach((v, i) => document.documentElement.style.setProperty(v, top[i]));
  }
  return { set };
})();

/* Modo ligero: se activa solo si este equipo dibuja la web a menos de ~40 fps, o a mano desde tu cuenta.
   Se recuerda por navegador (cada PC decide el suyo). */
const Lite = (() => {
  const KEY = "myspoty-lite";
  const get = () => { try { return localStorage.getItem(KEY); } catch { return null; } };  // "1", "0" o null (automático)
  const set = v => { try { v === null ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, v); } catch {} };
  const apply = on => document.body.classList.toggle("lite", on);
  function measure() {
    let frames = 0; const start = performance.now();
    const step = t => {
      frames++;
      if (t - start < 2000) return requestAnimationFrame(step);
      const fps = frames * 1000 / (t - start);
      if (fps < 40 && get() === null) { apply(true); toast(`Modo ligero activado: este equipo iba a ${Math.round(fps)} fps. Puedes cambiarlo en tu cuenta.`); }
    };
    requestAnimationFrame(step);
  }
  function init() {
    const saved = get();
    if (saved !== null) return apply(saved === "1");
    setTimeout(measure, 1200);  // tras la carga, cuando ya está todo pintado
  }
  return { init, get on() { return document.body.classList.contains("lite"); },
           toggle() { const on = !this.on; apply(on); set(on ? "1" : "0"); return on; } };
})();

/* Enlaces internos sin recargar la página (/playlists, /tags…). */
function go(path) {
  if (location.pathname + location.search !== path) history.pushState({}, "", path);
  window.dispatchEvent(new Event("myspoty:navigate"));
}
document.addEventListener("click", e => {
  const a = e.target.closest("a[data-link]");
  if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
  e.preventDefault();
  go(a.getAttribute("href"));
});

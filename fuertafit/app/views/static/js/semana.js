/* Pestaña «Plan semanal»: plantillas y semana tipo. */
const Week = (() => {
  const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  const WEEK_GROUPS = ["Pierna y glúteo", "Torso", "Core", "Fullbody", "Cardio", "Cuerpo-Mente"];
  // Semanas tipo (0 = lunes). Cada grupo muscular 2 veces/semana y ≥48 h entre sesiones del mismo grupo.
  const TEMPLATES = [
    { name: "5 días · pierna / torso",
      desc: "Cada zona 2 veces por semana, cardio y core 2 días. Lo recomendado si entrenas 4-5 días.",
      week: { 0: ["Pierna y glúteo", "Core"], 1: ["Torso"], 2: ["Cardio"], 3: ["Pierna y glúteo", "Core"],
              4: ["Torso", "Cardio"], 5: [], 6: [] } },
    { name: "3 días · fullbody",
      desc: "Cuerpo completo en días alternos. Lo mejor para semanas con poco tiempo (2-3 días).",
      week: { 0: ["Fullbody", "Core"], 1: [], 2: ["Fullbody", "Cardio"], 3: [], 4: ["Fullbody", "Core"],
              5: [], 6: [] } },
  ];
  const sameWeek = (a, b) => [0, 1, 2, 3, 4, 5, 6].every(i => JSON.stringify(a[i] || []) === JSON.stringify(b[i] || []));

  function renderTemplates() {
    $("templates").innerHTML = TEMPLATES.map((t, i) => `
      <button class="tpl${sameWeek(s.week, t.week) ? " on" : ""}" onclick="Week.applyTemplate(${i})">
        <strong>${esc(t.name)}</strong><span class="muted">${esc(t.desc)}</span></button>`).join("");
  }

  async function applyTemplate(i) {
    s.week = JSON.parse(JSON.stringify(TEMPLATES[i].week));
    render();
    await save(true);
    msg(`Plantilla «${esc(TEMPLATES[i].name)}» aplicada y guardada. Los días ya planificados no cambian:
         usa «Generar…» con «sustituir» si quieres rehacerlos.`);
  }
  let s = null;

  function render() {
    renderTemplates();
    $("weekGrid").innerHTML = "";
    DAYS.forEach((name, i) => {
      const sel = s.week[i] || (s.week[i] = []);
      const row = document.createElement("div");
      row.className = "wday";
      row.innerHTML = `<div class="dn">${name}</div><div class="chips"></div>`;
      const chips = row.querySelector(".chips");
      const rest = chip("Descanso", !sel.length, () => {});
      rest.classList.add("rest");
      const groupChips = WEEK_GROUPS.map(g => chip(g, sel.includes(g), () => {
        toggle(sel, g); rest.classList.toggle("on", !sel.length); renderTemplates();
      }));
      rest.onclick = () => { sel.length = 0; groupChips.forEach(c => c.classList.remove("on")); rest.classList.add("on"); renderTemplates(); };
      [rest, ...groupChips].forEach(c => chips.appendChild(c));
      $("weekGrid").appendChild(row);
    });
    const mats = $("wMaterials");
    mats.querySelectorAll(".chip").forEach(c => c.remove());
    Object.keys(META.materials).forEach(m => mats.appendChild(chip(m, s.materials.includes(m), () => toggle(s.materials, m))));
    for (const [id, key] of [["wWarmup", "warmup"], ["wCooldown", "cooldown"], ["wAuto", "autoPlan"]]) {
      $(id).classList.toggle("on", !!s[key]);
      $(id).onclick = () => { s[key] = !s[key]; $(id).classList.toggle("on", s[key]); };
    }
  }

  async function save(quiet) {
    s.dailyMinutes = DEFAULT_MIN;
    s = await api("/api/settings", s);
    if (!quiet) msg("Guardado ✓");
  }

  function msg(text) { $("wMsg").innerHTML = text; }

  async function fill(offsetWeeks) {
    await save(true);
    const d = new Date(); d.setDate(d.getDate() + 7 * offsetWeeks);
    const created = await api("/api/plan/week", { start: iso(d), overwrite: $("wOverwrite").checked });
    const days = Object.keys(created);
    msg(days.length
      ? `Planificados ${days.length} días: ${days.map(k => `<a href="#/calendario" onclick="Cal.goTo('${k}')">${esc(fmtDay(k))}</a>`).join(", ")}.`
      : "No había días que rellenar (ya estaban planificados o ya han pasado). Marca «sustituir» para rehacerlos.");
  }

  $("wSave").onclick = () => save();
  $("wThis").onclick = () => fill(0);
  $("wNext").onclick = () => fill(1);

  return { async show() { s = await api("/api/settings"); render(); msg(""); }, applyTemplate };
})();

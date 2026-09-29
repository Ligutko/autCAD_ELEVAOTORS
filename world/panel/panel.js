// Control center panel: polls /state, colours the schematic by element id, sends commands to /cmd.
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const el = (id) => document.getElementById(id);
const WORD = { off: "СТОП", starting: "ПУСК", run: "РОБОТА", stopping: "ЗУПИНКА", fault: "АВАРІЯ" };
const CATS = { receive: "приймання", dry: "сушіння", transfer: "переміщення", unload: "відвантаження",
               recirculate: "рециркуляція", pass: "транзит" };
let G = null, S = null, sel = null, cat = "receive", toastT = 0;

const fmt = (v, d = 0) => v == null ? "—" : Number(v).toLocaleString("uk-UA", { minimumFractionDigits: d, maximumFractionDigits: d });
const hms = (t) => { const d = Math.floor(t / 86400) + 1, s = Math.floor(t % 86400);
  return `доба ${d} · ${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  return path.endsWith(".svg") ? r.text() : r.json();
}
function toast(text, bad) {
  const t = el("toast"); t.textContent = text; t.className = "show" + (bad ? " bad" : "");
  clearTimeout(toastT); toastT = setTimeout(() => (t.className = ""), bad ? 5000 : 1800);
}
async function cmd(c) {
  const r = await api("/cmd", c);
  if (!r.ok) toast("Відмова: " + r.reason, true); else if (r.reason) toast(r.reason);
  return r;
}

// ---------------------------------------------------------------- setup
async function init() {
  G = await api("/graph");
  G.byId = Object.fromEntries(G.nodes.map((n) => [n.id, n]));
  G.edgeById = Object.fromEntries(G.edges.map((e) => [e.id, e]));
  el("mnemo-host").innerHTML = await api("/mnemo.svg");
  const dry = el("n-DRYER"); if (dry) dry.classList.add("unit");
  for (const g of document.querySelectorAll("#mnemo .gate")) g.addEventListener("click", (e) => { e.stopPropagation(); gateClick(g.dataset.id); });
  for (const n of document.querySelectorAll("#mnemo .node")) n.addEventListener("click", (e) => { e.stopPropagation(); select(n.dataset.id); });
  const sp = el("speeds");
  for (const v of G.speed_presets) {
    const b = document.createElement("button"); b.textContent = "×" + v; b.dataset.v = v;
    b.onclick = () => cmd({ op: "speed", value: v }); sp.appendChild(b);
  }
  el("pause").onclick = () => cmd({ op: "pause", value: !(S && S.paused) });
  el("reset").onclick = () => cmd({ op: "reset" });
  const scs = await api("/scenarios"), sel_ = el("scenario");
  for (const s of scs) { const o = document.createElement("option"); o.value = s.id; o.textContent = s.title; o.title = s.description; sel_.appendChild(o); }
  el("load").onclick = async () => { await api("/scenario", { id: sel_.value || null }); toast(sel_.value ? "Сценарій запущено" : "Вільний режим"); };
  const cats = el("cats");
  for (const [k, v] of Object.entries(CATS)) {
    const b = document.createElement("button"); b.textContent = v; b.dataset.k = k;
    b.onclick = () => { cat = k; drawRoutes(); }; cats.appendChild(b);
  }
  drawRoutes();
  poll();
}

// ---------------------------------------------------------------- routes
// the route by the nodes that tell routes apart: trucks, scales, points and pipes stay implicit
const QUIET = new Set(["SCALES_IN", "SCALES_OUT", "NODE_1", "GRAVITY_PIPE", "TOWER_PIT", "TRUCK_EXIT"]);
const NAME = { TRUCK_IN: "авто", TRUCK_OUT: "авто", PIT: "яма", SEP5: "сеп.5", SH1: "Ш1", DRYER: "сушарка" };
function short(r) { return r.nodes.filter((n) => !QUIET.has(n)).map((n) => NAME[n] || n).join(" → "); }
function drawRoutes() {
  for (const b of el("cats").children) b.classList.toggle("on", b.dataset.k === cat);
  const ul = el("rlist"); ul.innerHTML = "";
  for (const r of G.routes.filter((r) => r.category === cat)) {
    const li = document.createElement("li");
    li.innerHTML = `<span title="${r.id}">${short(r)}</span><button class="small">Пуск</button>`;
    li.onmouseenter = () => highlight(r.nodes); li.onmouseleave = () => highlight(null);
    li.querySelector("button").onclick = () => cmd({ op: "route", id: r.id, action: "start" });
    ul.appendChild(li);
  }
}
function highlight(nodes) {
  for (const x of document.querySelectorAll("#mnemo .hl")) x.classList.remove("hl");
  if (!nodes) return;
  for (const n of nodes) el("n-" + n)?.classList.add("hl");
  for (let i = 0; i + 1 < nodes.length; i++) el(`e-${nodes[i]}->${nodes[i + 1]}`)?.classList.add("hl");
}

// ---------------------------------------------------------------- state
async function poll() {
  try { S = await api("/state"); paint(); } catch (e) { /* server restarting */ }
  setTimeout(poll, 250);
}
function setText(id, t) { const e = el(id); if (e && e.textContent !== t) e.textContent = t; }
function paint() {
  setText("clock", hms(S.t_s));
  for (const b of el("speeds").children) b.classList.toggle("on", Number(b.dataset.v) === S.speed);
  el("pause").classList.toggle("on", S.paused);
  const T = S.totals;
  el("totals").innerHTML = `<span>прийнято <b>${fmt(T.received_t, 1)}</b> т</span><span>відвантажено <b>${fmt(T.shipped_t, 1)}</b> т</span>`
    + `<span>випарувано <b>${fmt(T.evaporated_t, 2)}</b> т</span><span>у сховищах <b>${fmt(T.stored_t, 1)}</b> т</span>`
    + `<span>у дорозі <b>${fmt(T.transit_t, 2)}</b> т</span><span>двигуни <b>${fmt(S.power_kw, 1)}</b> кВт</span>`;
  for (const [m, v] of Object.entries(S.motors)) {
    const n = el("n-" + m); if (!n) continue;
    n.classList.remove("s-off", "s-starting", "s-run", "s-stopping", "s-fault"); n.classList.add("s-" + v.state);
    setText("st-" + m, WORD[v.state] + (v.backlog_t > 0.05 ? " · ЗАВАЛ" : ""));
    setText("val-" + m, v.load_t_h > 0.01 ? `${fmt(v.load_t_h, 1)} т/год` : "");
  }
  for (const [g, v] of Object.entries(S.gates)) {
    const e = el("g-" + g); if (!e) continue;
    e.classList.remove("open", "closed", "opening", "closing", "fault"); e.classList.add(v.state);
  }
  for (const p of document.querySelectorAll("#mnemo .flow.on")) p.classList.remove("on");
  for (const k of Object.keys(S.edges)) {
    const e = G.edgeById[k], open = (g) => S.gates[g] && S.gates[g].state === "open";
    if (e && e.alt_gates.length) {                  // silo outlet: centre line and side branch by their own gates
      if (e.gates.some(open)) el("e-" + k)?.classList.add("on");
      if (e.alt_gates.some(open)) { el("e-" + k + "~alt")?.classList.add("on"); el("e-" + k)?.classList.add("on"); }
    } else el("e-" + k)?.classList.add("on");
  }
  for (const [sid, v] of Object.entries(S.stores)) level(sid, v.fill, `${fmt(v.mass_t, v.mass_t < 100 ? 1 : 0)} т` + (v.moisture_pct != null ? ` · ${fmt(v.moisture_pct, 1)} %` : ""));
  const d = S.dryer;
  level("DRYER", S.dryer_bin_cap_t ? Math.min(1, d.bin_t / S.dryer_bin_cap_t) : 0, d.state === "run"
    ? `${fmt(d.in_t_h, 1)} → ${fmt(d.out_t_h, 1)} т/год` : "");
  el("n-DRYER")?.classList.toggle("s-run", d.state === "run");
  setText("st-DRYER", d.state === "run" ? `РОБОТА · ${fmt(d.w_in, 0)}→${fmt(d.w_out, 0)} %` : "СТОП");
  const tr = S.trucks;
  setText("val-TRUCK_IN", tr.in_queue || tr.in_now ? `черга ${tr.in_queue}` + (tr.in_now ? (tr.in_now.phase === "weigh" ? " · на вагах" : ` · вивантаж. ${fmt(tr.in_now.left_t, 1)} т`) : "") : "");
  setText("val-TRUCK_OUT", tr.out_now ? `${fmt(tr.out_now.load_t, 1)} / ${fmt(tr.out_now.cap_t)} т · черга ${tr.out_queue}` : (tr.out_queue ? `черга ${tr.out_queue}` : ""));
  alarms(); journal(); active(); if (sel) card(sel);
}
function level(id, fill, text) {
  const r = el("lvl-" + id);
  if (r) { const t = +r.dataset.top, b = +r.dataset.bot, h = Math.max(0, Math.min(1, fill)) * (b - t);
    r.setAttribute("y", (b - h).toFixed(1)); r.setAttribute("height", h.toFixed(1)); }
  setText("val-" + id, text);
}
function alarms() {
  const ul = $("#alarms ul"); const want = S.alarms.map((a) => `${a.level}|${a.text}`).join("\n");
  if (ul.dataset.k === want) return; ul.dataset.k = want; ul.innerHTML = "";
  for (const x of document.querySelectorAll("#mnemo .alarm-ind")) x.remove();
  for (const a of S.alarms) {
    const li = document.createElement("li"); li.className = a.level; li.textContent = `${hms(a.t_s).slice(-8)}  ${a.text}`; ul.appendChild(li);
    const owner = a.id.split(".")[0], n = el("n-" + owner);
    if (n) { const b = n.getBBox(), t = document.createElementNS("http://www.w3.org/2000/svg", "text");
      t.setAttribute("x", b.x + b.width + 4); t.setAttribute("y", b.y + 12); t.setAttribute("class", "alarm-ind");
      t.setAttribute("fill", a.level === "trip" ? "#E22028" : "#EC8629"); t.textContent = a.level === "trip" ? "◆1" : "▲2"; n.appendChild(t); }
  }
  if (!S.alarms.length) ul.innerHTML = '<li class="hint">немає</li>';
}
function journal() {
  const ul = $("#journal ul"), last = S.events.length ? S.events[S.events.length - 1] : null;
  const key = last ? `${S.events.length}|${last.t_s}|${last.text}` : "";
  if (ul.dataset.k === key) return; ul.dataset.k = key; ul.innerHTML = "";
  for (const e of [...S.events].reverse()) {
    const li = document.createElement("li"); li.className = e.kind;
    li.innerHTML = `<span class="t">${hms(e.t_s).slice(-8)}</span>`; li.appendChild(document.createTextNode(e.text)); ul.appendChild(li);
  }
}
function active() {
  const ul = el("active"), key = S.routes.map((r) => r.id + r.state).join("|");
  if (ul.dataset.k === key) return; ul.dataset.k = key; ul.innerHTML = "";
  const word = { starting: "пуск", run: "працює", stopping: "зупинка" };
  for (const r of S.routes) {
    const li = document.createElement("li");
    li.innerHTML = `<span title="${r.id}">${short(r)} · ${word[r.state]}</span><button class="small">Стоп</button>`;
    li.onmouseenter = () => highlight(r.nodes); li.onmouseleave = () => highlight(null);
    li.querySelector("button").onclick = () => cmd({ op: "route", id: r.id, action: "stop" });
    ul.appendChild(li);
  }
}

// ---------------------------------------------------------------- object card
function gateClick(g) { const v = S.gates[g]; cmd({ op: "gate", id: g, action: v && (v.state === "open" || v.state === "opening") ? "close" : "open" }); }
function select(id) {
  for (const x of document.querySelectorAll("#mnemo .sel")) x.classList.remove("sel");
  sel = id; el("n-" + id)?.classList.add("sel"); card(id);
}
function row(k, v) { return `<tr><td>${k}</td><td>${v}</td></tr>`; }
function capText(n) {
  if (n.t_h == null) return "—";
  if (n.t_h_basis === "SITE") return `${fmt(n.t_h)} т/год`;
  const e = G.t_h_estimates[n.id];
  return `<span class="estv" title="${e ? e.basis + ": " + e.src : ""}">${fmt(n.t_h)} т/год (${e ? e.basis : "оцінка"})</span>`;
}
function card(id) {
  const box = el("obj"), n = G.byId[id]; if (!n || !S) return;
  const key = id + "|" + JSON.stringify([S.motors[id], S.stores[id], id === "DRYER" ? S.dryer : 0, Object.entries(S.sensors).filter(([k]) => k.startsWith(id + "."))]);
  if (box.dataset.k === key) return; box.dataset.k = key;
  let h = `<h3>${id}${n.model ? " · " + n.model : ""}</h3><table>`;
  const m = S.motors[id], st = S.stores[id];
  h += row("тип", n.kind + (n.layer ? ` · шар ${n.layer}` : ""));
  if (m) {
    h += row("стан", `<b>${WORD[m.state]}</b>`) + row("продуктивність", capText(n)) + row("зараз", `${fmt(m.load_t_h, 1)} т/год`)
      + row("зерно на ньому", `${fmt(m.transit_t, 2)} т`) + (m.backlog_t > 0 ? row("не пішло далі", `<b>${fmt(m.backlog_t, 2)} т</b>`) : "")
      + row("двигун", m.kw ? `${fmt(m.kw, 1)} кВт` : "невідомо (існуюча частина)") + row("швидкість стрічки", `${fmt(n.v, 2)} м/с · шлях ${fmt(n.length_m, 1)} м`);
  }
  if (st) {
    h += row("маса", `<b>${fmt(st.mass_t, 1)}</b> / ${fmt(st.cap_t, 0)} т (${fmt(100 * st.fill, 1)} %)`) + row("вологість", st.moisture_pct == null ? "—" : `${fmt(st.moisture_pct, 1)} %`);
    if (st.temp_c != null) h += row("температура", `${fmt(st.temp_c, 1)} °C`);
    if (st.feed_t_h) h += row("подача обмежена", `${fmt(st.feed_t_h)} т/год`);
    if (st.sweep) h += row("зачисний шнек", st.sweep === "run" ? "працює" : "стоїть") + row("аерація", st.fans === "run" ? "працює" : "стоїть");
  }
  if (id === "DRYER") {
    const d = S.dryer;
    h += row("стан", d.state === "run" ? "<b>РОБОТА</b>" : "<b>СТОП</b>") + row("сире на вході", `${fmt(d.in_t_h, 1)} т/год`) + row("сухе на виході", `${fmt(d.out_t_h, 1)} т/год`)
      + row("вода", `${fmt(d.water_t_h, 2)} т/год`) + row("вологість", d.w_in != null ? `${fmt(d.w_in, 1)} → ${fmt(d.w_out, 1)} %` : "—")
      + row("у колоні / бункері", `${fmt(d.column_t, 1)} / ${fmt(d.bin_t, 1)} т`) + row("газ", d.gas_m3_h != null ? `<span class="estv" title="derived rec_83e4121b">${fmt(d.gas_m3_h, 0)} м³/год</span>` : "—");
  }
  const sens = Object.entries(S.sensors).filter(([k]) => k.startsWith(id + "."));
  if (sens.length) h += row("датчики", sens.map(([k, v]) => `${k.slice(id.length + 1)}: ${v === "ok" ? "норма" : "<b>" + v + "</b>"}`).join("<br>"));
  h += "</table><div class='btns'>";
  if (m) h += `<button data-c='{"op":"motor","id":"${id}","action":"start"}'>Пуск</button><button data-c='{"op":"motor","id":"${id}","action":"stop"}'>Стоп</button><button data-c='{"op":"trip","id":"${id}"}'>Аварійний стоп</button>`;
  if (id === "DRYER") h += `<button data-c='{"op":"dryer","action":"start"}'>Пуск сушарки</button><button data-c='{"op":"dryer","action":"stop"}'>Стоп</button>`;
  if (st && st.sweep) h += `<button data-c='{"op":"sweep","id":"${id}","action":"${st.sweep === "run" ? "stop" : "start"}"}'>Шнек ${st.sweep === "run" ? "стоп" : "пуск"}</button>`
    + `<button data-c='{"op":"fans","id":"${id}","action":"${st.fans === "run" ? "stop" : "start"}"}'>Аерація ${st.fans === "run" ? "стоп" : "пуск"}</button>`;
  if (st) h += `<span>подача <input id="feed" size="4" placeholder="т/год"> <button id="feedb">задати</button></span>`;
  if (id === "TRUCK_IN") h += `<button data-c='{"op":"truck_in","count":1,"mass":30,"moisture":14}'>+ авто 30 т, 14 %</button><button data-c='{"op":"truck_in","count":1,"mass":30,"moisture":20}'>+ авто 30 т, 20 %</button>`;
  if (id === "TRUCK_OUT") h += `<button data-c='{"op":"truck_out","count":5}'>+ 5 порожніх авто</button>`;
  h += "</div>";
  box.innerHTML = h;
  for (const b of box.querySelectorAll("button[data-c]")) b.onclick = () => cmd(JSON.parse(b.dataset.c));
  const fb = el("feedb"); if (fb) fb.onclick = () => { const v = el("feed").value.trim(); cmd({ op: "feed", id, t_h: v ? Number(v) : null }); };
}
document.addEventListener("click", (e) => { if (e.target.closest("#mnemo") && !e.target.closest(".node,.gate")) { sel = null; for (const x of document.querySelectorAll("#mnemo .sel")) x.classList.remove("sel"); } });
init();

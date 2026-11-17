// Robot dashboard client. Plain JavaScript, no build step, no libraries.
// Talks JSON over one WebSocket (/ws). See dashboard/server.py for the messages.
//
// Map view: screen right = map +x, screen up = map +y (REP-103 seen from above,
// the same picture RViz and Foxglove draw). Yaw is counter-clockwise from +x.
"use strict";

const $ = (id) => document.getElementById(id);
const cfg = { name: "robot", wheel_names: [], holonomic: false, footprint: [], laser: [0, 0], mock: false };
const st = { pose: null, odom: null, wheels: null, estop: false, mcu_ok: false, mapping: false,
             nav: false, nav_status: "", goal: null, rec: null };
let scanPts = [];
let mapImg = null;          // offscreen canvas
let mapInfo = null;         // {width, height, resolution, origin}
let ws = null;
let connected = false;

// ── WebSocket ───────────────────────────────────────────────────────────
function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
    return true;
  }
  return false;
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(proto + "://" + location.host + "/ws");
  ws.onopen = () => { connected = true; $("conn").classList.add("on"); log("info", "connected"); };
  ws.onclose = () => {
    connected = false;
    $("conn").classList.remove("on");
    setTimeout(connect, 1000);
  };
  ws.onerror = () => { try { ws.close(); } catch (e) { /* closing anyway */ } };
  ws.onmessage = (ev) => {
    let m;
    try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.type === "hello") applyConfig(m.config);
    else if (m.type === "state") { Object.assign(st, m); renderState(); }
    else if (m.type === "scan") scanPts = m.points;
    else if (m.type === "map") buildMap(m);
    else if (m.type === "log") log(m.level, m.text);
  };
}

function applyConfig(c) {
  Object.assign(cfg, c);
  $("name").textContent = cfg.name;
  $("mock").classList.toggle("hidden", !cfg.mock);
  $("turn-wrap").classList.toggle("hidden", !cfg.holonomic);
  const rows = $("wheel-rows");
  rows.innerHTML = "";
  cfg.wheel_names.forEach((n, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = "<td></td><td id=\"wt" + i + "\">-</td><td id=\"wa" + i + "\">-</td><td id=\"wp" + i + "\">-</td>";
    tr.firstChild.textContent = n;
    rows.appendChild(tr);
  });
}

// ── Log panel ───────────────────────────────────────────────────────────
function log(level, text) {
  const box = $("log");
  const line = document.createElement("div");
  line.className = level;
  line.textContent = new Date().toLocaleTimeString() + "  " + text;
  box.appendChild(line);
  while (box.childNodes.length > 200) box.removeChild(box.firstChild);
  box.scrollTop = box.scrollHeight;
}

// ── State -> page ───────────────────────────────────────────────────────
function chip(id, cls, label) {
  const el = $(id);
  el.className = "chip " + cls;
  if (label) el.textContent = label;
}

function renderState() {
  chip("chip-mcu", st.estop ? "bad" : (st.mcu_ok ? "on" : "warn"), st.estop ? "ESTOP" : "MCU");
  chip("chip-map", st.mapping ? "on" : "", "MAP");
  chip("chip-nav", st.nav ? "on" : "", st.nav_status ? "NAV " + st.nav_status : "NAV");
  chip("chip-rec", st.rec !== null ? "bad" : "", st.rec !== null ? "REC " + st.rec : "REC");
  const es = $("estop");
  es.textContent = st.estop ? "CLEAR" : "E-STOP";
  es.classList.toggle("latched", st.estop);
  $("map-toggle").textContent = st.mapping ? "MAP stop" : "MAP start";
  $("map-toggle").classList.toggle("on", st.mapping);
  $("nav-toggle").textContent = st.nav ? "NAV stop" : "NAV start";
  $("nav-toggle").classList.toggle("on", st.nav);
  $("rec-toggle").textContent = st.rec !== null ? "REC stop" : "REC start";
  $("rec-toggle").classList.toggle("on", st.rec !== null);
  if (st.wheels) {
    cfg.wheel_names.forEach((n, i) => {
      $("wt" + i).textContent = st.wheels.target[i].toFixed(2);
      $("wa" + i).textContent = st.wheels.actual[i].toFixed(2);
      $("wp" + i).textContent = st.wheels.pwm[i];
    });
  }
  const p = st.pose;
  const o = st.odom;
  let txt = p ? (p[3] + ": x " + p[0].toFixed(3) + "  y " + p[1].toFixed(3) + "  yaw " +
                (p[2] * 180 / Math.PI).toFixed(1) + "°") : "pose: no TF yet";
  if (o && p && p[3] !== "odom") txt += "\nodom: x " + o[0].toFixed(3) + "  y " + o[1].toFixed(3);
  $("pose").textContent = txt;
}

// ── Map view ────────────────────────────────────────────────────────────
const canvas = $("map");
const ctx = canvas.getContext("2d");
const view = { cx: 0, cy: 0, scale: 80, follow: true };   // scale in px per metre
let goalMode = false;
let goalDraft = null;      // {x, y, yaw}

function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

function resize() {
  const r = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(r.width * dpr));
  canvas.height = Math.max(1, Math.round(r.height * dpr));
}
window.addEventListener("resize", resize);

function w2s(x, y) {
  const dpr = window.devicePixelRatio || 1;
  return [canvas.width / 2 + (x - view.cx) * view.scale * dpr,
          canvas.height / 2 - (y - view.cy) * view.scale * dpr];
}
function s2w(px, py) {
  const dpr = window.devicePixelRatio || 1;
  return [view.cx + (px * dpr - canvas.width / 2) / (view.scale * dpr),
          view.cy - (py * dpr - canvas.height / 2) / (view.scale * dpr)];
}

function buildMap(m) {
  const raw = atob(m.data);
  const off = document.createElement("canvas");
  off.width = m.width;
  off.height = m.height;
  const c = off.getContext("2d");
  const img = c.createImageData(m.width, m.height);
  const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  const free = hex(cssVar("--map-free")), unk = hex(cssVar("--map-unknown")), occ = hex(cssVar("--map-occ"));
  for (let j = 0; j < m.height; j++) {
    for (let i = 0; i < m.width; i++) {
      const v = raw.charCodeAt(j * m.width + i);
      // Row j of the grid is world y = origin.y + j*res. Store it so that the
      // canvas transform below (negative y scale) puts row 0 at the bottom.
      const k = 4 * (j * m.width + i);
      let col = unk;
      if (v !== 255) col = v >= 65 ? occ : (v <= 25 ? free : unk);
      img.data[k] = col[0]; img.data[k + 1] = col[1]; img.data[k + 2] = col[2]; img.data[k + 3] = 255;
    }
  }
  c.putImageData(img, 0, 0);
  mapImg = off;
  mapInfo = m;
}

function drawArrow(x, y, yaw, len, color, width) {
  const [sx, sy] = w2s(x, y);
  const [ex, ey] = w2s(x + len * Math.cos(yaw), y + len * Math.sin(yaw));
  ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width;
  ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
  const a = Math.atan2(ey - sy, ex - sx);
  const h = 10 * (window.devicePixelRatio || 1);
  ctx.beginPath();
  ctx.moveTo(ex, ey);
  ctx.lineTo(ex - h * Math.cos(a - 0.4), ey - h * Math.sin(a - 0.4));
  ctx.lineTo(ex - h * Math.cos(a + 0.4), ey - h * Math.sin(a + 0.4));
  ctx.closePath(); ctx.fill();
}

function draw() {
  const dpr = window.devicePixelRatio || 1;
  if (view.follow && st.pose) { view.cx = st.pose[0]; view.cy = st.pose[1]; }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = cssVar("--map-unknown");
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (mapImg && mapInfo) {
    const [ox, oy] = w2s(mapInfo.origin[0], mapInfo.origin[1]);
    const s = mapInfo.resolution * view.scale * dpr;
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.setTransform(s, 0, 0, -s, ox, oy);
    ctx.drawImage(mapImg, 0, 0);
    ctx.restore();
  }

  // 1 m grid around the view centre, faint
  ctx.strokeStyle = cssVar("--line"); ctx.lineWidth = 1;
  const span = canvas.width / (view.scale * dpr);
  if (span < 40) {
    for (let g = Math.floor(view.cx - span); g <= view.cx + span; g++) {
      const [a] = w2s(g, 0); ctx.beginPath(); ctx.moveTo(a, 0); ctx.lineTo(a, canvas.height); ctx.stroke();
    }
    for (let g = Math.floor(view.cy - span); g <= view.cy + span; g++) {
      const [, b] = w2s(0, g); ctx.beginPath(); ctx.moveTo(0, b); ctx.lineTo(canvas.width, b); ctx.stroke();
    }
  }
  // origin axes: x red, y green
  drawArrow(0, 0, 0, 0.3, "#d23b2f", 2 * dpr);
  drawArrow(0, 0, Math.PI / 2, 0.3, "#1f9d55", 2 * dpr);

  // scan
  ctx.fillStyle = cssVar("--scan");
  const r = Math.max(1.5, 1.5 * dpr);
  for (const p of scanPts) {
    const [sx, sy] = w2s(p[0], p[1]);
    ctx.fillRect(sx - r, sy - r, 2 * r, 2 * r);
  }

  // goal
  if (st.goal) drawArrow(st.goal[0], st.goal[1], st.goal[2], 0.4, cssVar("--goal"), 3 * dpr);
  if (goalDraft) drawArrow(goalDraft.x, goalDraft.y, goalDraft.yaw, 0.4, cssVar("--goal"), 2 * dpr);

  // robot footprint + heading
  if (st.pose) {
    const [x, y, yaw] = st.pose;
    const c = Math.cos(yaw), s = Math.sin(yaw);
    const fp = cfg.footprint.length ? cfg.footprint : [[0.2, 0.15], [-0.2, 0.15], [-0.2, -0.15], [0.2, -0.15]];
    ctx.beginPath();
    fp.forEach((q, i) => {
      const [sx, sy] = w2s(x + c * q[0] - s * q[1], y + s * q[0] + c * q[1]);
      if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
    });
    ctx.closePath();
    ctx.fillStyle = cssVar("--robot") + "55";
    ctx.fill();
    ctx.strokeStyle = cssVar("--robot"); ctx.lineWidth = 2 * dpr; ctx.stroke();
    drawArrow(x, y, yaw, 0.35, cssVar("--robot"), 2 * dpr);
  }
  requestAnimationFrame(draw);
}

// pan, pinch, wheel zoom, goal taps
const pointers = new Map();
let pinch0 = null;
canvas.addEventListener("pointerdown", (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
  if (goalMode && pointers.size === 1) {
    const [x, y] = s2w(e.offsetX, e.offsetY);
    const yaw = st.pose ? Math.atan2(y - st.pose[1], x - st.pose[0]) : 0;
    goalDraft = { x: x, y: y, yaw: yaw, px: e.offsetX, py: e.offsetY, dragged: false };
  }
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinch0 = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), scale: view.scale };
  }
});
canvas.addEventListener("pointermove", (e) => {
  if (!pointers.has(e.pointerId)) return;
  const prev = pointers.get(e.pointerId);
  pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
  if (pointers.size === 2 && pinch0) {
    const [a, b] = [...pointers.values()];
    const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
    view.scale = Math.min(400, Math.max(10, pinch0.scale * d / Math.max(1, pinch0.d)));
    return;
  }
  if (goalDraft) {
    const dx = e.offsetX - goalDraft.px, dy = e.offsetY - goalDraft.py;
    if (Math.hypot(dx, dy) > 12) {
      goalDraft.dragged = true;
      goalDraft.yaw = Math.atan2(-dy, dx);     // screen y is down, map y is up
    }
    return;
  }
  view.follow = false;
  $("follow").classList.remove("on");
  view.cx -= (e.offsetX - prev[0]) / view.scale;
  view.cy += (e.offsetY - prev[1]) / view.scale;
});
function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinch0 = null;
  if (goalDraft && pointers.size === 0) {
    const g = goalDraft;
    goalDraft = null;
    setGoalMode(false);
    if (send({ type: "goal", x: g.x, y: g.y, yaw: g.yaw })) {
      log("info", "goal sent (" + g.x.toFixed(2) + ", " + g.y.toFixed(2) + ") " +
          (g.yaw * 180 / Math.PI).toFixed(0) + "°" + (g.dragged ? "" : " (heading: facing the goal)"));
    } else {
      log("error", "goal NOT sent: no connection");
    }
  }
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  view.scale = Math.min(400, Math.max(10, view.scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
}, { passive: false });
$("zoom-in").onclick = () => { view.scale = Math.min(400, view.scale * 1.3); };
$("zoom-out").onclick = () => { view.scale = Math.max(10, view.scale / 1.3); };
$("follow").onclick = () => { view.follow = !view.follow; $("follow").classList.toggle("on", view.follow); };
function setGoalMode(on) { goalMode = on; $("goal-mode").classList.toggle("on", on); }
$("goal-mode").onclick = () => setGoalMode(!goalMode);

// ── Joystick and turn slider ────────────────────────────────────────────
const drive = { x: 0, y: 0, r: 0, active: false };
function attachPad(el, knob, onMove, horizontalOnly) {
  let id = null;
  const move = (e) => {
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
    const rad = horizontalOnly ? rect.width / 2 - 23 : rect.width / 2 - 32;
    let dx = e.clientX - cx, dy = horizontalOnly ? 0 : e.clientY - cy;
    const d = Math.hypot(dx, dy);
    if (d > rad) { dx *= rad / d; dy *= rad / d; }
    knob.style.transform = "translate(" + dx + "px," + dy + "px)";
    onMove(dx / rad, -dy / rad);
  };
  const reset = () => { id = null; knob.style.transform = ""; onMove(0, 0); };
  el.addEventListener("pointerdown", (e) => { id = e.pointerId; el.setPointerCapture(id); move(e); });
  el.addEventListener("pointermove", (e) => { if (e.pointerId === id) move(e); });
  el.addEventListener("pointerup", (e) => { if (e.pointerId === id) reset(); });
  el.addEventListener("pointercancel", (e) => { if (e.pointerId === id) reset(); });
}
const dz = (v) => (Math.abs(v) < 0.08 ? 0 : v);
attachPad($("stick"), $("knob"), (x, y) => { drive.x = dz(x); drive.y = dz(y); }, false);
attachPad($("turn"), $("turn-knob"), (x) => { drive.r = dz(-x); }, true);   // slide left = turn left

let lastSentZero = true;
setInterval(() => {
  const moving = drive.x !== 0 || drive.y !== 0 || drive.r !== 0;
  if (moving) {
    send({ type: "drive", x: drive.x, y: drive.y, r: drive.r });
    lastSentZero = false;
  } else if (!lastSentZero) {
    send({ type: "drive", x: 0, y: 0, r: 0 });     // one explicit zero on release
    lastSentZero = true;
  }
}, 66);

// ── Buttons ─────────────────────────────────────────────────────────────
$("estop").onclick = () => send({ type: st.estop ? "estop_clear" : "estop" });
$("map-toggle").onclick = () => {
  if (st.mapping && !confirm("Stop mapping? The map is saved first.")) return;
  send({ type: st.mapping ? "map_stop" : "map_start" });
};
$("map-save").onclick = () => send({ type: "map_save" });
$("nav-toggle").onclick = () => send({ type: st.nav ? "nav_stop" : "nav_start" });
$("goal-cancel").onclick = () => send({ type: "goal_cancel" });
$("rezero").onclick = () => {
  if (confirm("Make the robot's current spot odometry (0, 0, 0)?")) send({ type: "rezero" });
};
$("rec-toggle").onclick = () => send({ type: st.rec !== null ? "rec_stop" : "rec_start" });
$("mcu-form").onsubmit = (e) => {
  e.preventDefault();
  const v = $("mcu-cmd").value.trim();
  if (v) { send({ type: "mcu", cmd: v }); $("mcu-cmd").value = ""; }
};
// Space bar = E-STOP when typing is not in progress (laptop use).
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && document.activeElement !== $("mcu-cmd")) {
    e.preventDefault();
    send({ type: "estop" });
  }
});

resize();
connect();
requestAnimationFrame(draw);

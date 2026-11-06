/* Human-annotation UI for the B5 protocol. */

const GROUP_INFO = {
  scm_node: { label: "节点区域", color: "#2f6fed" },
  chain_step: { label: "推理链区域", color: "#ee8b23" },
  effect: { label: "后效区域", color: "#12a594" },
  preserved: { label: "保持区域", color: "#8a5cf6" },
};

const state = {
  annotator: null,
  queue: [],
  idx: 0,
  payload: null,
  decisions: null,
  visible: { scm_node: true, chain_step: true, effect: true, preserved: true },
  drawKey: null,
  drag: null,
  zoom: 1,
  started: 0,
  dirty: false,
  focused: null,
};

const $ = (sel) => document.querySelector(sel);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function post(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/* ------------------------------------------------------------------ login -- */

async function boot() {
  const info = await api("/api/state");
  const proto = info.protocol;
  $("#login-proto").textContent =
    `协议：${proto.n_items} 条样本 × 每条 ${proto.raters_per_item} 名标注者独立校验`
    + `（共 ${info.annotators.length} 名标注者，seed=${proto.seed}）。`;
  const box = $("#roster");
  box.innerHTML = "";
  for (const ann of info.annotators) {
    const btn = el("button");
    btn.innerHTML = `<b>${ann.name}</b><span class="id">${ann.id}</span>`;
    btn.onclick = () => login(ann.id);
    box.appendChild(btn);
  }
  const saved = localStorage.getItem("anno.annotator");
  if (saved && info.annotators.some((a) => a.id === saved)) {
    // resume the previous session on this browser without a second click
    login(saved);
  }
}

async function login(annotator) {
  localStorage.setItem("anno.annotator", annotator);
  const info = await api(`/api/state?annotator=${encodeURIComponent(annotator)}`);
  state.annotator = annotator;
  state.queue = info.queue;
  $("#who").textContent = annotator;
  $("#login").classList.add("hidden");
  $("#topbar").classList.remove("hidden");
  $("#main").classList.remove("hidden");
  $("#footer").classList.remove("hidden");
  updateProgress(info.progress);
  const firstOpen = state.queue.findIndex((q) => !q.done);
  state.idx = firstOpen < 0 ? 0 : firstOpen;
  await loadIndex(state.idx);
}

function updateProgress(progress) {
  const p = progress || {
    done: state.queue.filter((q) => q.done).length,
    total: state.queue.length,
  };
  const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
  $("#progress").textContent = `进度 ${p.done}/${p.total}（${pct}%）`;
}

/* ------------------------------------------------------------------- load -- */

function draftKey(itemId) {
  return `anno.draft.${state.annotator}.${itemId}`;
}

function initDecisions(payload) {
  const sub = payload.submission;
  const d = {
    scm: { nodes: {}, edges: {}, intervention: "yes", verdict: null, note: "" },
    chain: { steps: {}, verdict: null, note: "" },
    regions: {},
    region_verdict: null,
    notes: "",
  };
  payload.nodes.forEach((n) => (d.scm.nodes[n.key] = "yes"));
  payload.edges.forEach((e) => (d.scm.edges[e.key] = "yes"));
  payload.item.reasoning_chain.forEach((s) => (d.chain.steps[String(s.step)] = "yes"));
  payload.regions.forEach((u) => {
    d.regions[u.key] = { decision: "accept", box: u.ref.slice(), iou: 1 };
  });
  const merge = (src) => {
    if (!src) return false;
    d.scm.nodes = { ...d.scm.nodes, ...(src.scm?.nodes || {}) };
    d.scm.edges = { ...d.scm.edges, ...(src.scm?.edges || {}) };
    d.scm.intervention = src.scm?.intervention || "yes";
    d.scm.verdict = src.scm?.verdict ?? null;
    d.scm.note = src.scm?.note || "";
    d.chain.steps = { ...d.chain.steps, ...(src.chain?.steps || {}) };
    d.chain.verdict = src.chain?.verdict ?? null;
    d.chain.note = src.chain?.note || "";
    d.region_verdict = src.region_verdict ?? null;
    d.notes = src.notes || "";
    payload.regions.forEach((u) => {
      const e = src.regions?.[u.key];
      if (e) {
        d.regions[u.key] = {
          decision: e.decision,
          box: (e.box || u.ref).slice(),
          iou: e.iou === undefined || e.iou === null ? 1 : e.iou,
        };
      }
    });
    return true;
  };
  if (!merge(sub)) {
    const raw = localStorage.getItem(draftKey(payload.item.id));
    if (raw) {
      try { merge(JSON.parse(raw).decisions); } catch (err) { /* ignore */ }
    }
  }
  return d;
}

async function loadIndex(i) {
  if (i < 0 || i >= state.queue.length) return;
  state.idx = i;
  const itemId = state.queue[i].item_id;
  const payload = await api(
    `/api/item/${encodeURIComponent(itemId)}?annotator=${encodeURIComponent(state.annotator)}`
  );
  state.payload = payload;
  state.decisions = initDecisions(payload);
  state.drawKey = null;
  state.focused = null;
  state.started = Date.now();
  setSaveState(payload.submission ? "saved" : "dirty");
  render();
}

/* --------------------------------------------------------------- rendering -- */

function render() {
  const p = state.payload;
  const it = p.item;
  $("#item-id").textContent = `${it.id}  (#${p.index + 1}/${p.total})`;
  $("#item-meta").textContent =
    `${it.pool} · ${it.domain} / ${it.type} · ${it.difficulty} · 链长 ${it.meta.chain_length}`;
  $("#img").src = `/api/image/${it.image_id}`;
  $("#instruction").textContent = `指令：${it.instruction}`;
  const cf = it.counterfactual;
  $("#cf-body").textContent = cf
    ? `违规指令：${cf.instruction}${cf.violated_edge ? `（违反边 ${cf.violated_edge}）` : ""}${cf.reason ? ` — ${cf.reason}` : ""}`
    : "（本条没有反事实字段）";
  $("#jump").value = p.index + 1;
  applyZoom();

  renderToggles();
  renderOverlay();
  renderScm();
  renderChain();
  renderRegions();
  $("#notes").value = state.decisions.notes;
  $("#scm-note").value = state.decisions.scm.note;
  $("#chain-note").value = state.decisions.chain.note;
}

function setZoom(value) {
  state.zoom = clamp(value, 1, 4);
  applyZoom();
}

function applyZoom() {
  // the stage is an inline-block of the viewer; scaling its width scrolls the
  // viewer, and every box keeps its percentage position, so the overlay and the
  // pointer->region conversion stay exact at any zoom.
  $("#stage").style.width = state.zoom === 1 ? "100%" : `${state.zoom * 100}%`;
  $("#zoom-label").textContent = `${Math.round(state.zoom * 100)}%`;
}

function renderToggles() {
  const box = $("#toggles");
  box.innerHTML = "";
  const groups = [...new Set(state.payload.regions.map((u) => u.group))];
  for (const g of groups) {
    const info = GROUP_INFO[g] || { label: g, color: "#888" };
    const lab = el("label");
    const cb = el("input");
    cb.type = "checkbox";
    cb.checked = state.visible[g] !== false;
    cb.onchange = () => { state.visible[g] = cb.checked; renderOverlay(); };
    const dot = el("span", "dot");
    dot.style.background = info.color;
    lab.append(cb, dot, el("span", null, info.label));
    box.appendChild(lab);
  }
}

function renderOverlay() {
  const svg = $("#svg");
  const labels = $("#labels");
  svg.innerHTML = "";
  labels.innerHTML = "";
  const p = state.payload;
  const activeKey = state.focused && state.focused.kind === "region" ? state.focused.key : null;
  for (const u of p.regions) {
    if (state.visible[u.group] === false) continue;
    const d = state.decisions.regions[u.key];
    const box = d.decision === "correct" && d.box ? d.box : u.ref;
    let cls = `g-${u.group}`;
    if (activeKey && activeKey !== u.key) cls += " dim";
    if (activeKey === u.key) cls += " active";
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", box[0]);
    rect.setAttribute("y", box[1]);
    rect.setAttribute("width", Math.max(0, box[2] - box[0]));
    rect.setAttribute("height", Math.max(0, box[3] - box[1]));
    rect.setAttribute("class", cls);
    svg.appendChild(rect);
    const sp = el("span", `g-${u.group} pick`);
    sp.textContent = u.label;
    const top = box[1] / 10;
    sp.style.left = `${clamp(box[0] / 10, 0.5, 88)}%`;
    sp.style.top = `${clamp(top, 0.5, 99)}%`;
    // keep the caption inside the picture when the box touches the top edge
    if (top < 3) sp.classList.add("below");
    if (activeKey && activeKey !== u.key) sp.classList.add("dim");
    sp.onclick = () => { focusRow("region", u.key); };
    labels.appendChild(sp);
  }
  if (state.drag && state.drag.box) {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const [x1, y1, x2, y2] = state.drag.box;
    rect.setAttribute("x", x1);
    rect.setAttribute("y", y1);
    rect.setAttribute("width", Math.max(0, x2 - x1));
    rect.setAttribute("height", Math.max(0, y2 - y1));
    rect.setAttribute("class", "preview");
    svg.appendChild(rect);
  }
}

function chipRow(values, current, onPick, attrs) {
  const wrap = el("div", "chips");
  for (const [value, text] of values) {
    const b = el("button", "chip" + (current === value ? " on" : ""), text);
    b.dataset.v = value;
    Object.entries(attrs || {}).forEach(([k, v]) => (b.dataset[k] = v));
    b.onclick = (ev) => { ev.stopPropagation(); onPick(value); };
    wrap.appendChild(b);
  }
  return wrap;
}

const YESNO = [["yes", "是"], ["no", "否"], ["unsure", "不确定"]];
const VERDICTS = [["valid", "有效 / 正确"], ["minor", "部分需修正"], ["invalid", "无效 / 错误"]];
const REGION_VERDICTS = [["valid", "准确"], ["minor", "部分需修正"], ["invalid", "偏差大"]];

function markDirty() {
  state.dirty = true;
  setSaveState("dirty");
  clearTimeout(markDirty._t);
  markDirty._t = setTimeout(saveDraft, 700);
}

function saveDraft() {
  if (!state.payload) return;
  const key = draftKey(state.payload.item.id);
  localStorage.setItem(key, JSON.stringify({ decisions: state.decisions, at: Date.now() }));
  if (!state.dirty) return;
  setSaveState("draft");
}

function setSaveState(kind) {
  const node = $("#savestate");
  node.className = "pill " + (kind === "dirty" ? "dirty" : kind === "draft" ? "ghost" : "saved");
  node.textContent =
    kind === "saved" ? "已提交" : kind === "draft" ? "草稿已存本地" : "未保存";
  state.dirty = kind === "dirty";
}

function focusRow(kind, key) {
  state.focused = { kind, key };
  renderOverlay();
  document.querySelectorAll(".row.focused").forEach((r) => r.classList.remove("focused"));
  const row = document.querySelector(`.row[data-kind="${kind}"][data-key="${CSS.escape(key)}"]`);
  if (row) row.classList.add("focused");
}

function rowBase(kind, key, labelNode, chips) {
  const row = el("div", "row");
  row.dataset.kind = kind;
  row.dataset.key = key;
  const left = el("div");
  left.appendChild(labelNode);
  row.appendChild(left);
  row.appendChild(chips);
  row.onclick = () => focusRow(kind, key);
  return row;
}

/* ------------------------------------------------------------------- SCM --- */

function renderScm() {
  const p = state.payload;
  const d = state.decisions;
  const nodesBox = $("#scm-nodes");
  const edgesBox = $("#scm-edges");
  const interBox = $("#scm-intervention");
  nodesBox.innerHTML = "";
  edgesBox.innerHTML = "";
  interBox.innerHTML = "";

  nodesBox.appendChild(el("div", "group-title", `节点（${p.nodes.length}）与状态`));
  for (const n of p.nodes) {
    const lab = el("div");
    const t = el("div", "label", `${n.key} · ${n.label}  [${n.kind}]`);
    const s = el("div", "sub", `编辑前状态：${n.state_before ?? "—"}` +
      (n.region ? ` · 区域 [${n.region.join(", ")}]` : " · 无区域框"));
    lab.append(t, s);
    nodesBox.appendChild(rowBase("node", n.key, lab,
      chipRow(YESNO, d.scm.nodes[n.key], (v) => {
        d.scm.nodes[n.key] = v; markDirty(); renderScm(); renderOverlay();
      })));
  }

  const iv = p.item.scm.intervention || {};
  const lab = el("div");
  lab.append(
    el("div", "label", `干预变量：节点 ${iv.node ?? "?"} · ${iv.variable ?? "?"}`),
    el("div", "sub", `${iv.from ?? "?"} → ${iv.to ?? "?"}（该状态变化是否与指令一致？）`)
  );
  interBox.appendChild(el("div", "group-title", "干预"));
  interBox.appendChild(rowBase("intervention", "iv", lab,
    chipRow(YESNO, d.scm.intervention, (v) => {
      d.scm.intervention = v; markDirty(); renderScm();
    })));

  edgesBox.appendChild(el("div", "group-title", `因果边（${p.edges.length}）`));
  if (!p.edges.length) {
    edgesBox.appendChild(el("div", "hint", "本条无可校验的因果边（表层对照样本）。"));
  }
  for (const e of p.edges) {
    const box = el("div");
    box.append(
      el("div", "label", `${e.src} → ${e.dst}   [${e.relation ?? "?"}]`),
      el("div", "sub", e.mechanism || "")
    );
    edgesBox.appendChild(rowBase("edge", e.key, box,
      chipRow(YESNO, d.scm.edges[e.key], (v) => {
        d.scm.edges[e.key] = v; markDirty(); renderScm();
      })));
  }

  const vb = $("#scm-verdict");
  vb.innerHTML = "";
  vb.appendChild(el("span", "q", "整体 SCM 判定："));
  vb.appendChild(chipRow(VERDICTS, d.scm.verdict, (v) => {
    d.scm.verdict = v; markDirty(); renderScm();
  }));
}

/* ----------------------------------------------------------------- chain --- */

function renderChain() {
  const p = state.payload;
  const d = state.decisions;
  const box = $("#chain-steps");
  box.innerHTML = "";
  for (const s of p.item.reasoning_chain) {
    const left = el("div");
    left.append(
      el("div", "label", `步骤 ${s.step}：${s.thought}`),
      el("div", "sub", s.region ? `区域 [${s.region.join(", ")}]` : "无区域框")
    );
    box.appendChild(rowBase("step", String(s.step), left,
      chipRow(YESNO, d.chain.steps[String(s.step)], (v) => {
        d.chain.steps[String(s.step)] = v; markDirty(); renderChain();
      })));
  }
  const vb = $("#chain-verdict");
  vb.innerHTML = "";
  vb.appendChild(el("span", "q", "整体推理链判定："));
  vb.appendChild(chipRow(VERDICTS, d.chain.verdict, (v) => {
    d.chain.verdict = v; markDirty(); renderChain();
  }));
}

/* --------------------------------------------------------------- regions --- */

function boxesIoU(a, b) {
  const ix1 = Math.max(a[0], b[0]), iy1 = Math.max(a[1], b[1]);
  const ix2 = Math.min(a[2], b[2]), iy2 = Math.min(a[3], b[3]);
  const inter = Math.max(0, ix2 - ix1) * Math.max(0, iy2 - iy1);
  const areaA = Math.max(0, a[2] - a[0]) * Math.max(0, a[3] - a[1]);
  const areaB = Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
  const union = areaA + areaB - inter;
  return union > 0 ? inter / union : 0;
}

function renderRegions() {
  const p = state.payload;
  const d = state.decisions;
  const box = $("#regions");
  box.innerHTML = "";
  for (const u of p.regions) {
    const entry = d.regions[u.key];
    const left = el("div");
    const info = GROUP_INFO[u.group] || { label: u.group, color: "#888" };
    left.append(
      el("div", "label", `${u.label}  ·  ${info.label}`),
      el("div", "mono", `参考框 [${u.ref.join(", ")}]` +
        (entry.decision === "correct" ? ` → 你画的框 [${entry.box.map((v) => Math.round(v)).join(", ")}]` : ""))
    );
    const chips = el("div", "chips");
    const iou = entry.decision === "correct" ? entry.iou : 1;
    const badge = el("span", "iou " + (iou >= 0.5 ? "good" : "bad"),
      `IoU ${iq(iou)}`);
    const bAccept = el("button", "chip" + (entry.decision === "accept" ? " on" : ""), "接受");
    bAccept.dataset.v = "accept";
    bAccept.onclick = (ev) => {
      ev.stopPropagation();
      d.regions[u.key] = { decision: "accept", box: u.ref.slice(), iou: 1 };
      markDirty(); renderRegions(); renderOverlay();
    };
    const bRedraw = el("button", "chip" + (entry.decision === "correct" ? " on" : ""), "重画");
    bRedraw.dataset.v = "correct";
    bRedraw.onclick = (ev) => {
      ev.stopPropagation();
      startDraw(u.key);
    };
    chips.append(badge, bAccept, bRedraw);
    box.appendChild(rowBase("region", u.key, left, chips));
  }
  const vb = $("#region-verdict");
  vb.innerHTML = "";
  vb.appendChild(el("span", "q", "整体区域质量："));
  vb.appendChild(chipRow(REGION_VERDICTS, d.region_verdict, (v) => {
    d.region_verdict = v; markDirty(); renderRegions();
  }));
}

function iq(v) {
  return (v === undefined || v === null) ? "—" : v.toFixed(2);
}

/* ---------------------------------------------------------------- drawing -- */

function startDraw(key) {
  state.drawKey = key;
  const stage = $("#stage");
  stage.classList.add("drawing");
  $("#drawhint").classList.remove("hidden");
  focusRow("region", key);
}

function stopDraw() {
  state.drawKey = null;
  state.drag = null;
  $("#stage").classList.remove("drawing");
  $("#drawhint").classList.add("hidden");
  renderOverlay();
}

function pointerPos(ev) {
  const rect = $("#stage").getBoundingClientRect();
  return [
    clamp(((ev.clientX - rect.left) / rect.width) * 1000, 0, 1000),
    clamp(((ev.clientY - rect.top) / rect.height) * 1000, 0, 1000),
  ];
}

function bindDrawing() {
  const stage = $("#stage");
  stage.addEventListener("pointerdown", (ev) => {
    if (!state.drawKey) return;
    ev.preventDefault();
    const p = pointerPos(ev);
    state.drag = { start: p, box: [p[0], p[1], p[0], p[1]] };
    renderOverlay();
  });
  window.addEventListener("pointermove", (ev) => {
    if (!state.drawKey || !state.drag) return;
    const p = pointerPos(ev);
    const [x0, y0] = state.drag.start;
    state.drag.box = [Math.min(x0, p[0]), Math.min(y0, p[1]),
                      Math.max(x0, p[0]), Math.max(y0, p[1])];
    renderOverlay();
  });
  window.addEventListener("pointerup", () => {
    if (!state.drawKey || !state.drag) return;
    const [x1, y1, x2, y2] = state.drag.box;
    const key = state.drawKey;
    const unit = state.payload.regions.find((u) => u.key === key);
    state.drag = null;
    if (x2 - x1 < 12 || y2 - y1 < 12) { stopDraw(); return; }
    const box = [x1, y1, x2, y2].map((v) => Math.round(v * 10) / 10);
    const iou = boxesIoU(box, unit.ref);
    state.decisions.regions[key] = { decision: "correct", box, iou };
    markDirty();
    stopDraw();
    renderRegions();
  });
}

/* ----------------------------------------------------------------- saving -- */

function complete() {
  const d = state.decisions;
  return !!(d.scm.verdict && d.chain.verdict);
}

async function submit() {
  if (!state.payload) return false;
  if (!complete()) {
    alert("请先完成第 1 节与第 2 节的“整体判定”（SCM 与推理链）。");
    return false;
  }
  const d = state.decisions;
  const record = {
    annotator: state.annotator,
    item_id: state.payload.item.id,
    started: new Date(state.started).toISOString(),
    duration_s: Math.round((Date.now() - state.started) / 1000),
    scm: { ...d.scm },
    chain: { ...d.chain },
    regions: d.regions,
    region_verdict: d.region_verdict,
    notes: d.notes,
  };
  const res = await post("/api/submit", record);
  if (!res.ok) return false;
  const entry = state.queue[state.idx];
  if (entry) entry.done = true;
  localStorage.removeItem(draftKey(state.payload.item.id));
  setSaveState("saved");
  updateProgress();
  return true;
}

async function saveAndAdvance() {
  const btn = $("#btn-save");
  btn.disabled = true;
  try {
    const ok = await submit();
    if (ok) await advance(1);
  } catch (err) {
    alert("保存失败：" + err.message + "\n（草稿仍保存在本地浏览器中）");
  } finally {
    btn.disabled = false;
  }
}

async function advance(delta) {
  if (complete() && !state.payload.submission) {
    try { await submit(); } catch (err) { /* keep the draft */ }
  }
  await loadIndex(clamp(state.idx + delta, 0, state.queue.length - 1));
}

/* ------------------------------------------------------------------ events -- */

function bindEvents() {
  bindDrawing();
  $("#btn-save").onclick = saveAndAdvance;
  $("#btn-next").onclick = () => advance(1);
  $("#btn-prev").onclick = () => advance(-1);
  $("#jump").addEventListener("change", () => {
    const n = parseInt($("#jump").value, 10);
    if (n >= 1 && n <= state.queue.length) loadIndex(n - 1);
  });
  $("#btn-skip").onclick = () => loadIndex(clamp(state.idx + 1, 0, state.queue.length - 1));
  $("#zoom-in").onclick = () => setZoom(state.zoom * 1.5);
  $("#zoom-out").onclick = () => setZoom(state.zoom / 1.5);
  $("#zoom-fit").onclick = () => setZoom(1);
  $("#stage").addEventListener("wheel", (ev) => {
    if (!ev.ctrlKey && !ev.metaKey) return;
    ev.preventDefault();
    setZoom(state.zoom * (ev.deltaY < 0 ? 1.2 : 1 / 1.2));
  }, { passive: false });
  $("#btn-switch").onclick = () => {
    saveDraft();
    localStorage.removeItem("anno.annotator");
    location.reload();
  };
  $("#btn-clear").onclick = () => {
    if (!confirm("清除本题的本地标注（服务器上已提交的记录不受影响）？")) return;
    localStorage.removeItem(draftKey(state.payload.item.id));
    state.decisions = initDecisions({ ...state.payload, submission: null });
    render();
    setSaveState("dirty");
  };
  document.querySelectorAll("[data-quick]").forEach((btn) => {
    btn.onclick = () => applyQuick(btn.dataset.quick);
  });
  $("#notes").addEventListener("input", (ev) => {
    state.decisions.notes = ev.target.value; markDirty();
  });
  $("#scm-note").addEventListener("input", (ev) => {
    state.decisions.scm.note = ev.target.value; markDirty();
  });
  $("#chain-note").addEventListener("input", (ev) => {
    state.decisions.chain.note = ev.target.value; markDirty();
  });
  document.addEventListener("keydown", (ev) => {
    const tag = (ev.target.tagName || "").toLowerCase();
    if (tag === "textarea" || tag === "input") {
      if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) saveAndAdvance();
      return;
    }
    if (ev.key === "Enter") { ev.preventDefault(); saveAndAdvance(); }
    else if (ev.key === "ArrowRight") advance(1);
    else if (ev.key === "ArrowLeft") advance(-1);
    else if (ev.key === "Escape") stopDraw();
    else if (ev.key === "+" || ev.key === "=") setZoom(state.zoom * 1.5);
    else if (ev.key === "-" || ev.key === "_") setZoom(state.zoom / 1.5);
    else if (ev.key.toLowerCase() === "a") applyQuick("region-accept-all");
    else if (ev.key.toLowerCase() === "e") applyQuick("scm-all-yes");
    else if (["1", "2", "3"].includes(ev.key)) applyNumber(parseInt(ev.key, 10));
  });
}

function applyNumber(n) {
  const f = state.focused;
  if (!f) return;
  const d = state.decisions;
  if (f.kind === "edge") d.scm.edges[f.key] = YESNO[n - 1][0];
  else if (f.kind === "node") d.scm.nodes[f.key] = YESNO[n - 1][0];
  else if (f.kind === "intervention") d.scm.intervention = YESNO[n - 1][0];
  else if (f.kind === "step") d.chain.steps[f.key] = YESNO[n - 1][0];
  else if (f.kind === "region") {
    if (n === 1) {
      const unit = state.payload.regions.find((u) => u.key === f.key);
      d.regions[f.key] = { decision: "accept", box: unit.ref.slice(), iou: 1 };
    } else if (n === 2) { startDraw(f.key); return; }
  } else return;
  markDirty();
  renderScm(); renderChain(); renderRegions(); renderOverlay();
}

function applyQuick(what) {
  const d = state.decisions;
  if (what === "scm-all-yes") {
    Object.keys(d.scm.edges).forEach((k) => (d.scm.edges[k] = "yes"));
    Object.keys(d.scm.nodes).forEach((k) => (d.scm.nodes[k] = "yes"));
    d.scm.intervention = "yes";
  } else if (what === "chain-all-yes") {
    Object.keys(d.chain.steps).forEach((k) => (d.chain.steps[k] = "yes"));
  } else if (what === "region-accept-all") {
    state.payload.regions.forEach((u) => {
      d.regions[u.key] = { decision: "accept", box: u.ref.slice(), iou: 1 };
    });
  }
  markDirty();
  renderScm(); renderChain(); renderRegions(); renderOverlay();
}

window.addEventListener("beforeunload", () => saveDraft());

bindEvents();

boot().catch((err) => {
  document.body.innerHTML =
    `<div class="overlay"><div class="login-card"><h1>无法连接标注服务器</h1>` +
    `<p class="hint">${err.message}</p>` +
    `<p class="hint">请确认服务器已启动、Xshell 隧道（localhost:9001 → localhost:9001）已建立。</p>` +
    `</div></div>`;
});

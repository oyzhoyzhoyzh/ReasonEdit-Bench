/* ReasonEdit-Bench human preference study - vanilla JS, no build step. */
"use strict";

const api = (p, opt) => fetch(p, opt).then(r => r.json());
const $ = id => document.getElementById(id);

const OBL = [
  ["change", "被要求的改变发生了吗？"],
  ["propagate", "随之而来的后果（连带影响）出现了吗？"],
  ["preserve", "不该被改动的内容保持住了吗？"],
];
const OBL_OPTS = [["yes", "是"], ["no", "否"], ["unsure", "不确定"]];

const state = {
  rater: null,
  meta: null,
  queue: [],
  idx: 0,
  trial: null,
  answer: null,       // {choice, confidence, obligations, comment}
  t0: Date.now(),
};

/* ------------------------------------------------------------------ store -- */
const LS = {
  raterKey: "pref.rater",
  draftKey: (rater, tid) => `pref.draft.${rater}.${tid}`,
  get(rater, tid) {
    try { return JSON.parse(localStorage.getItem(this.draftKey(rater, tid)) || "null"); }
    catch { return null; }
  },
  set(rater, tid, val) {
    try { localStorage.setItem(this.draftKey(rater, tid), JSON.stringify(val)); } catch {}
  },
};

function blank() {
  return { choice: null, confidence: 0,
           obligations: { left: {}, right: {} }, comment: "" };
}

function toast(msg, ms = 1600) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), ms);
}

function setSaveState(text, cls) {
  const el = $("savestate");
  el.textContent = text;
  el.className = "pill " + (cls || "ghost");
}

/* ------------------------------------------------------------------- boot -- */
async function boot() {
  state.meta = await api("/api/meta");
  if (!state.meta || !state.meta.annotators || !state.meta.n_trials) {
    $("roster").innerHTML =
      "<p class='warnbox'>服务器还没有抽题：请先运行 <code>python -m reasondata.pref_app sample</code>。</p>";
    return;
  }
  const saved = localStorage.getItem(LS.raterKey);
  renderRoster(saved);
  // a direct link (?rater=p3) lets the organiser hand each rater their own URL
  const fromUrl = new URLSearchParams(location.search).get("rater");
  const pick = [fromUrl, saved].find(id => id && state.meta.annotators.some(a => a.id === id));
  if (pick) start(pick);
}

function renderRoster(saved) {
  const box = $("roster");
  box.innerHTML = "";
  for (const a of state.meta.annotators) {
    const p = state.meta.progress[a.id] || { assigned: 0, submitted: 0 };
    const b = document.createElement("button");
    b.className = "rosterbtn" + (a.id === saved ? " active" : "");
    b.innerHTML = `<b>${a.name}</b><span class="hint small">${a.id} ·
      ${p.submitted}/${p.assigned} 已完成</span>`;
    b.onclick = () => start(a.id);
    box.appendChild(b);
  }
  const tot = state.meta.n_trials, gold = state.meta.n_gold;
  $("login-proto").textContent =
    `题目池：${tot} 个配对（含 ${gold} 个质量校验题），每条约 ${state.meta.raters_per_item} 人独立判定。`;
}

async function start(rater) {
  state.rater = rater;
  localStorage.setItem(LS.raterKey, rater);
  const a = state.meta.annotators.find(x => x.id === rater);
  $("who").textContent = a ? a.name : rater;
  $("login").classList.add("hidden");
  $("topbar").classList.remove("hidden");
  $("main").classList.remove("hidden");
  await loadQueue();
  await goto(0);
}

async function loadQueue() {
  state.meta = await api(`/api/meta?rater=${encodeURIComponent(state.rater)}`);
  state.queue = state.meta.queue || [];
}

const getTrial = (tid) => api(`/api/trial/${tid}?rater=${state.rater}`);

/* ------------------------------------------------------------------ render -- */
async function goto(i) {
  if (!state.queue) await loadQueue();
  if (!state.queue || !state.queue.length) { toast("该评价者没有分配题目", 2600); return; }
  state.idx = Math.max(0, Math.min(i, state.queue.length - 1));
  const tid = state.queue[state.idx];
  state.trial = await getTrial(tid);
  state.answer = state.trial.submission
    ? normaliseServer(state.trial.submission)
    : (LS.get(state.rater, tid) || blank());
  render();
}

function normaliseServer(s) {
  return { choice: s.choice, confidence: s.confidence || 0,
           obligations: s.obligations || { left: {}, right: {} },
           comment: s.comment || "" };
}

function render() {
  const t = state.trial;
  const a = state.answer;
  $("instruction").textContent = t.instruction;
  $("item-meta").textContent = `#${t.index + 1} / ${t.total} · 题号 ${t.id}`;
  $("progress").textContent = `${t.index + 1}/${t.total}`;
  $("jump").value = t.index + 1;

  setImg("img-src", t.source_url);
  setImg("img-a", t.left_url);
  setImg("img-b", t.right_url);
  zoomApply();

  document.querySelectorAll("#choices .choice").forEach(b =>
    b.classList.toggle("sel", b.dataset.choice === a.choice));
  document.querySelectorAll("#confidence .scale").forEach(b =>
    b.classList.toggle("sel", Number(b.dataset.c) === a.confidence));

  buildObligations();
  $("comment").value = a.comment || "";
  $("obl-box").open = Boolean(
    a.obligations.left.change || a.obligations.right.change || a.obligations.left.propagate);
  setSaveState(a.choice ? "已作答" : "未作答", a.choice ? "" : "ghost");
  $("btn-prev").disabled = !t.prev_id;
  $("btn-next").disabled = !t.next_id;
  state.t0 = Date.now();
}

function setImg(id, url) {
  const el = $(id);
  if (!url) { el.removeAttribute("src"); return; }
  if (el.dataset.url !== url) { el.dataset.url = url; el.src = url; }
}

function buildObligations() {
  const box = $("obligations");
  box.innerHTML = "";
  for (const side of ["left", "right"]) {
    const label = side === "left" ? "A" : "B";
    const col = document.createElement("div");
    col.className = "oblcol";
    col.innerHTML = `<h4><span class="sidebadge ${label.toLowerCase()}">${label}</span></h4>`;
    for (const [key, text] of OBL) {
      const row = document.createElement("div");
      row.className = "oblrow";
      row.innerHTML = `<span class="obltext">${text}</span>`;
      const grp = document.createElement("span");
      grp.className = "oblbtns";
      for (const [val, lab] of OBL_OPTS) {
        const b = document.createElement("button");
        b.className = "oblb" + (state.answer.obligations[side][key] === val ? " sel" : "");
        b.textContent = lab;
        b.onclick = () => {
          state.answer.obligations[side][key] = val;
          buildObligations();
          saveDraft();
        };
        grp.appendChild(b);
      }
      row.appendChild(grp);
      col.appendChild(row);
    }
    box.appendChild(col);
  }
}

/* ------------------------------------------------------------------- zoom -- */
let zoom = 1;
function zoomApply() {
  document.querySelectorAll(".imgwrap img").forEach(el =>
    el.style.width = `${Math.round(zoom * 100)}%`);
  $("zoom-label").textContent = `${Math.round(zoom * 100)}%`;
}
function zoomFit() {
  zoom = 1; zoomApply();
}

/* ----------------------------------------------------------------- actions -- */
function pick(choice) {
  state.answer.choice = choice;
  document.querySelectorAll("#choices .choice").forEach(b =>
    b.classList.toggle("sel", b.dataset.choice === choice));
  setSaveState("已作答（未提交）", "warn");
  saveDraft();
}

function pickConf(c) {
  state.answer.confidence = c;
  document.querySelectorAll("#confidence .scale").forEach(b =>
    b.classList.toggle("sel", Number(b.dataset.c) === c));
  saveDraft();
}

function saveDraft() {
  state.answer.comment = $("comment").value;
  LS.set(state.rater, state.trial.id, state.answer);
  setSaveState("草稿已本地保存", "warn");
}

async function submit(advance = true) {
  const a = state.answer;
  if (!a.choice) { toast("请先选择「哪一份更好」"); return; }
  if (!a.confidence) { toast("请选择确信程度（1–5）"); return; }
  a.comment = $("comment").value;
  const body = {
    rater: state.rater, trial_id: state.trial.id, choice: a.choice,
    confidence: a.confidence, obligations: a.obligations, comment: a.comment,
    seconds: (Date.now() - state.t0) / 1000,
  };
  const res = await api("/api/submit", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) { toast("提交失败：" + (res.error || "未知错误"), 2600); return; }
  localStorage.removeItem(LS.draftKey(state.rater, state.trial.id));
  setSaveState("已提交", "");
  const p = state.meta.progress[state.rater];
  if (p) { p.submitted = Math.max(p.submitted, state.trial.index + 1); }
  if (advance) {
    if (state.trial.next_id) await goto(state.idx + 1);
    else {
      const left = state.queue.length - state.idx - 1;
      toast(left > 0 ? "已提交，队列结束（请回看上一题）" : "全部完成，感谢！", 2400);
    }
  }
}

/* ------------------------------------------------------------------ events -- */
$("choices").addEventListener("click", e => {
  const b = e.target.closest(".choice");
  if (b) { pick(b.dataset.choice); }
});
$("confidence").addEventListener("click", e => {
  const b = e.target.closest(".scale");
  if (b) pickConf(Number(b.dataset.c));
});
$("btn-save").onclick = () => submit(true);
$("btn-next").onclick = () => goto(state.idx + 1);
$("btn-prev").onclick = () => goto(state.idx - 1);
$("btn-switch").onclick = () => {
  $("login").classList.remove("hidden");
  $("topbar").classList.add("hidden");
  $("main").classList.add("hidden");
  localStorage.removeItem(LS.raterKey);
  renderRoster(null);
};
$("jump").addEventListener("keydown", e => {
  if (e.key === "Enter") goto(Number(e.target.value) - 1);
});
$("comment").addEventListener("input", saveDraft);
$("zoom-in").onclick = () => { zoom = Math.min(3, zoom + 0.2); zoomApply(); };
$("zoom-out").onclick = () => { zoom = Math.max(0.4, zoom - 0.2); zoomApply(); };
$("zoom-fit").onclick = zoomFit;
$("show-source").onchange = e =>
  $("srcbox").classList.toggle("hidden", !e.target.checked);

document.addEventListener("keydown", e => {
  if ($("main").classList.contains("hidden")) return;
  const tag = (e.target.tagName || "").toLowerCase();
  if (tag === "textarea" || tag === "input") return;
  if (e.key === "1") pick("A");
  else if (e.key === "2") pick("B");
  else if (e.key === "3") pick("tie");
  else if (e.key === "4") pick("both_fail");
  else if (e.key === "Enter") { e.preventDefault(); submit(true); }
  else if (e.key === "ArrowRight") goto(state.idx + 1);
  else if (e.key === "ArrowLeft") goto(state.idx - 1);
});
window.addEventListener("beforeunload", () => { try { saveDraft(); } catch {} });

boot();

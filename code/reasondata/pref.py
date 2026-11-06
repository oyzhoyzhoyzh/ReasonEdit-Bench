"""Human preference study for ReasonEdit-Bench.

Design
------
A *trial* shows two edited results of the same instruction (and the same source
photograph) side by side, with the system identity hidden and the left/right order
randomised at sampling time.  The rater answers a forced choice -- which side
better fulfils the instruction -- plus a confidence, and may optionally fill in a
per-side check of the three obligations the contract measures (did the requested
change happen, did its consequences follow, was unrelated content preserved).

Two things make the study informative rather than decorative:

* **Gold trials.**  A tenth of the trials pair a real edit with a heavily degraded
  copy of itself.  The degraded side is objectively worse, so the pass rate
  measures whether a rater is paying attention, and lets the report drop
  (or flag) raters who are not.
* **The analysis compares the human choice with the automated metrics** on exactly
  the same pairs, so the claim "the causal contract tracks human judgement better
  than CLIP" becomes a measurement instead of an assertion.

The sample is frozen once (``sample``) so every rater sees the same trials and the
assignment is reproducible from the seed.
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import anno, config
from .bench import read_jsonl
from .runs import list_runs, label_short

#: the contrasts the study is built from: (pairing id, left system, right system)
#: before the per-trial left/right randomisation
PAIRINGS: list[tuple[str, str, str]] = [
    ("base_vs_cot", "qwen_image_edit", "qwen_image_edit__cot"),
    ("base_vs_scaffold", "qwen_image_edit", "qwen_image_edit__scaffold_full"),
    ("base_vs_oracle", "qwen_image_edit", "qwen_image_edit__oracle"),
    ("base_vs_sdxl", "qwen_image_edit", "sdxl_inpaint"),
    ("base_vs_classic", "qwen_image_edit", "instructpix2pix"),
    ("classic_vs_sdxl", "instructpix2pix", "sdxl_inpaint"),
]

CHOICES = ["A", "B", "tie", "both_fail"]

DEFAULT_ANNOTATORS = [
    {"id": "p1", "name": "评价者 1"},
    {"id": "p2", "name": "评价者 2"},
    {"id": "p3", "name": "评价者 3"},
    {"id": "p4", "name": "评价者 4"},
    {"id": "p5", "name": "评价者 5"},
]


# --------------------------------------------------------------------- paths --
def study_dir(data_dir: str | Path | None = None) -> Path:
    root = Path(data_dir) if data_dir else (config.RESULTS / "preference")
    root.mkdir(parents=True, exist_ok=True)
    return root


def study_path(data_dir: str | Path | None = None) -> Path:
    return study_dir(data_dir) / "study.json"


def submissions_dir(data_dir: str | Path | None = None) -> Path:
    p = study_dir(data_dir) / "submissions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def submission_file(rater: str, data_dir: str | Path | None = None) -> Path:
    return submissions_dir(data_dir) / f"{rater}.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ------------------------------------------------------------------- images --
def image_for(system: str, item_id: str, runs: dict[str, Path] | None = None) -> Path | None:
    """Locate a generated image without trusting the (possibly stale) manifest."""
    runs = runs if runs is not None else list_runs()
    run_dir = runs.get(system)
    if run_dir is None:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = run_dir / f"{item_id}{ext}"
        if p.exists():
            return p
    return None


def _degrade(path: Path, dst: Path, seed: int) -> Path:
    """A visibly worse copy of the same edit: blur, noise and hard JPEG."""
    import io

    from PIL import Image, ImageFilter

    rng = random.Random(seed)
    img = Image.open(path).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=3.2))
    px = img.load()
    w, h = img.size
    step = max(1, (w * h) // 60000)          # sprinkle noise without a full pass
    for i in range(0, w * h, step):
        x, y = (i * 7919) % w, (i // w) % h
        r, g, b = px[x, y]
        d = rng.randint(-48, 48)
        px[x, y] = (min(255, max(0, r + d)), min(255, max(0, g + d)),
                    min(255, max(0, b + d)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=38)
    buf.seek(0)
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.open(buf).convert("RGB").save(dst, quality=88)
    return dst


# -------------------------------------------------------------------- sample --
def build_study(items: list[dict], n_per_pairing: int = 40, raters_per_item: int = 3,
                annotators: list[dict] | None = None, seed: int = 20261010,
                gold_frac: float = 0.1, data_dir: str | Path | None = None) -> dict:
    annotators = annotators or DEFAULT_ANNOTATORS
    runs = list_runs()
    by_id = {it["id"]: it for it in items}
    rng = random.Random(seed)
    root = study_dir(data_dir)

    trials: list[dict] = []
    missing: Counter = Counter()
    for pairing, left_sys, right_sys in PAIRINGS:
        pool = []
        for item_id in sorted(by_id):
            lp = image_for(left_sys, item_id, runs)
            rp = image_for(right_sys, item_id, runs)
            if lp and rp:
                pool.append((item_id, lp, rp))
        if not pool:
            missing[pairing] += n_per_pairing
            continue
        rng.shuffle(pool)
        take = pool[:n_per_pairing]
        missing[pairing] += max(0, n_per_pairing - len(take))
        for item_id, lp, rp in take:
            item = by_id[item_id]
            # randomise which system is shown on the left
            if rng.random() < 0.5:
                (lsys, lpath), (rsys, rpath) = ((left_sys, lp), (right_sys, rp))
            else:
                (lsys, lpath), (rsys, rpath) = ((right_sys, rp), (left_sys, lp))
            src = config.BENCH_IMAGES / f"{item['image_id']}.jpg"
            trials.append({
                "id": f"t{len(trials) + 1:04d}",
                "pairing": pairing,
                "item_id": item_id,
                "instruction": item["instruction"],
                "source": str(src) if src.exists() else None,
                "left": {"system": lsys, "path": str(lpath)},
                "right": {"system": rsys, "path": str(rpath)},
                "gold": False,
            })

    # ---- gold/attention trials: a real edit against a degraded copy of itself --
    n_gold = int(round(len(trials) * gold_frac))
    gold_srcs = rng.sample(trials, min(n_gold, len(trials))) if trials else []
    for g in gold_srcs:
        tid = f"t{len(trials) + 1:04d}"
        good, bad = g["left"], g["right"]
        clean_first = rng.random() < 0.5
        clean_side, dirty_src = (good, bad) if clean_first else (bad, good)
        dst = root / "gold" / f"{tid}.jpg"
        _degrade(Path(dirty_src["path"]), dst, seed + len(trials))
        dirty = {"system": dirty_src["system"] + "__degraded", "path": str(dst),
                 "degraded_of": dirty_src["system"]}
        left, right = (clean_side, dirty) if clean_first else (dirty, clean_side)
        trials.append({
            "id": tid,
            "pairing": "gold_degradation",
            "item_id": g["item_id"],
            "instruction": g["instruction"],
            "source": g["source"],
            "left": {**left, "gold_role": "clean" if clean_first else "degraded"},
            "right": {**right, "gold_role": "degraded" if clean_first else "clean"},
            "gold": True,
        })

    rng.shuffle(trials)
    for i, t in enumerate(trials, 1):
        t["order"] = i

    ann_ids = [a["id"] for a in annotators]
    assign = anno.assign_raters(len(trials), ann_ids, raters_per_item, seed)
    assignment = {a: [trials[i]["id"] for i in idx] for a, idx in assign.items()}

    return {
        "created": now_iso(),
        "seed": seed,
        "n_trials": len(trials),
        "n_gold": sum(1 for t in trials if t["gold"]),
        "raters_per_item": min(raters_per_item, len(ann_ids)),
        "annotators": annotators,
        "pairings": {p: sum(1 for t in trials if t["pairing"] == p) for p, _, _ in PAIRINGS}
                     | {"gold_degradation": sum(1 for t in trials if t["pairing"] == "gold_degradation")},
        "shortfall": {k: v for k, v in missing.items() if v},
        "trials": trials,
        "assignment": assignment,
    }


def write_study(study: dict, data_dir: str | Path | None = None) -> Path:
    path = study_path(data_dir)
    path.write_text(json.dumps(study, ensure_ascii=False, indent=1))
    return path


def load_study(data_dir: str | Path | None = None) -> dict:
    path = study_path(data_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


# --------------------------------------------------------------- submissions --
def load_submissions(data_dir: str | Path | None = None) -> dict[str, dict[str, dict]]:
    """rater -> trial_id -> record (last write wins)."""
    out: dict[str, dict[str, dict]] = {}
    for path in sorted(submissions_dir(data_dir).glob("*.jsonl")):
        per: dict[str, dict] = {}
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            per[rec["trial_id"]] = rec
        out[path.stem] = per
    return out


def append_submission(record: dict, data_dir: str | Path | None = None) -> None:
    path = submission_file(record["rater"], data_dir)
    with path.open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalise_submission(payload: dict, study: dict) -> dict:
    trials = {t["id"]: t for t in study["trials"]}
    tid = str(payload.get("trial_id") or "")
    if tid not in trials:
        raise ValueError(f"unknown trial {tid!r}")
    rater = str(payload.get("rater") or "").strip()
    if not rater:
        raise ValueError("missing rater")
    choice = str(payload.get("choice") or "").strip()
    if choice not in CHOICES:
        raise ValueError(f"choice must be one of {CHOICES}, got {choice!r}")

    def tri(v):
        v = str(v or "").strip().lower()
        return v if v in ("yes", "no", "unsure") else None

    oblig = payload.get("obligations") or {}
    return {
        "trial_id": tid,
        "rater": rater,
        "choice": choice,
        "confidence": int(payload.get("confidence") or 0),
        "obligations": {
            "left": {k: tri(oblig.get("left", {}).get(k))
                     for k in ("change", "propagate", "preserve")},
            "right": {k: tri(oblig.get("right", {}).get(k))
                      for k in ("change", "propagate", "preserve")},
        },
        "comment": str(payload.get("comment") or "")[:1000],
        "seconds": float(payload.get("seconds") or 0.0),
        "submitted": now_iso(),
    }


# ------------------------------------------------------------------- report ---
def _scores_index(scores_path: Path) -> dict[tuple[str, str], dict]:
    out = {}
    if scores_path.exists():
        for r in read_jsonl(scores_path):
            out[(r["item_id"], r["system"])] = r
    return out


def compute_report(data_dir: str | Path | None = None,
                   scores_path: str | Path | None = None) -> dict:
    study = load_study(data_dir)
    if not study:
        return {"ready": False, "reason": "no study sampled yet"}
    trials = {t["id"]: t for t in study["trials"]}
    subs = load_submissions(data_dir)
    scores = _scores_index(Path(scores_path) if scores_path
                           else config.RESULTS / "analysis" / "scores.jsonl")

    per_rater: dict[str, dict] = {}
    by_trial: dict[str, list[dict]] = defaultdict(list)
    for rater, recs in subs.items():
        gold = [(tid, r) for tid, r in recs.items() if trials.get(tid, {}).get("gold")]
        # a choice is recorded as "A"/"B", so the clean side has to be mapped to its
        # letter before it can be compared with the answer
        passed = 0
        for tid, r in gold:
            clean = "A" if trials[tid]["left"].get("gold_role") == "clean" else "B"
            if r["choice"] == clean:
                passed += 1
        per_rater[rater] = {
            "submitted": len(recs),
            "assigned": len(study["assignment"].get(rater, [])),
            "gold_seen": len(gold),
            "gold_pass": passed,
            "gold_pass_rate": round(passed / len(gold), 3) if gold else None,
            "mean_confidence": round(sum(r["confidence"] for r in recs.values()) / len(recs), 2)
                               if recs else None,
            "mean_seconds": round(sum(r["seconds"] for r in recs.values()) / len(recs), 1)
                            if recs else None,
        }
        for tid, r in recs.items():
            by_trial[tid].append(r)

    expected = study["n_trials"] * study["raters_per_item"]
    done_trials = sum(1 for tid, recs in by_trial.items() if len(recs) >= study["raters_per_item"])
    coverage = {
        "trials_complete": done_trials,
        "trials_total": study["n_trials"],
        "submissions": sum(len(v) for v in subs.values()),
        "submissions_expected": expected,
        "per_rater": per_rater,
    }

    # ---- head to head win rates -------------------------------------------------
    wins: Counter = Counter()
    h2h: dict[tuple, Counter] = defaultdict(Counter)
    for tid, recs in by_trial.items():
        t = trials[tid]
        if t["gold"]:
            continue
        ls, rs = t["left"]["system"], t["right"]["system"]
        for r in recs:
            h2h[(ls, rs)][r["choice"]] += 1
            if r["choice"] == "A":
                wins[ls] += 1
            elif r["choice"] == "B":
                wins[rs] += 1
    head_to_head = [
        {"left": ls, "right": rs, "A": c["A"], "B": c["B"], "tie": c["tie"],
         "both_fail": c["both_fail"], "n": sum(c.values()),
         "left_win_rate": round(c["A"] / sum(c.values()), 3) if sum(c.values()) else None}
        for (ls, rs), c in sorted(h2h.items())
    ]

    # ---- does the human choice follow the automated metrics? --------------------
    metrics = ("ccs", "clipscore", "dino_i")
    agree: dict[str, list[float]] = {m: [] for m in metrics}
    decisive: dict[str, list[float]] = {m: [] for m in metrics}
    n_pairs = 0
    for tid, recs in by_trial.items():
        t = trials[tid]
        if t["gold"]:
            continue
        ls, rs = t["left"]["system"], t["right"]["system"]
        a = scores.get((t["item_id"], ls))
        b = scores.get((t["item_id"], rs))
        if not a or not b:
            continue
        for r in recs:
            if r["choice"] not in ("A", "B"):
                continue
            # "A" is the left side; a higher value means a better result for every
            # metric used here (CCS, CLIPScore, DINO-I)
            chosen = a if r["choice"] == "A" else b
            other = b if chosen is a else a
            n_pairs += 1
            for m in metrics:
                if chosen.get(m) is None or other.get(m) is None:
                    continue
                agree[m].append(1.0 if chosen[m] >= other[m] else 0.0)
                if abs(chosen[m] - other[m]) > 0.05:
                    decisive[m].append(1.0 if chosen[m] > other[m] else 0.0)

    metric_agreement = {
        m: {
            "n": len(agree[m]),
            "agreement": round(sum(agree[m]) / len(agree[m]), 3) if agree[m] else None,
            "decisive_n": len(decisive[m]),
            "decisive_agreement": round(sum(decisive[m]) / len(decisive[m]), 3)
                                  if decisive[m] else None,
        }
        for m in metrics
    }

    # ---- inter-rater agreement on the forced choice -----------------------------
    labels = [sorted([r["choice"] for r in recs]) for tid, recs in sorted(by_trial.items())
              if len(recs) >= 2]
    kappa = anno.fleiss_kappa(labels, CHOICES)
    choice_mix = Counter(r["choice"] for recs in by_trial.values() for r in recs)

    return {
        "ready": True,
        "generated": now_iso(),
        "protocol": {k: study[k] for k in
                     ("created", "seed", "n_trials", "n_gold", "raters_per_item",
                      "annotators", "pairings")},
        "coverage": coverage,
        "choice_mix": dict(choice_mix),
        "head_to_head": head_to_head,
        "metric_agreement": metric_agreement,
        "n_decisive_annotations": n_pairs,
        "kappa_choice": kappa,
    }


def report_markdown(rep: dict) -> str:
    if not rep.get("ready"):
        return "# 人工偏好研究报告\n\n尚未抽题（先运行 `sample`）。\n"
    p, c = rep["protocol"], rep["coverage"]
    lines = [
        "# 人工偏好研究报告",
        "",
        f"- 生成时间：{rep['generated']}",
        f"- 样本：{p['n_trials']} 个配对（其中注意力校验 {p['n_gold']} 个），"
        f"每条由 {p['raters_per_item']} 名评价者独立判定，共 {len(p['annotators'])} 名评价者",
        f"- 抽样种子：{p['seed']}",
        f"- 进度：{c['trials_complete']}/{c['trials_total']} 条满员；"
        f"已收 {c['submissions']}/{c['submissions_expected']} 份判定",
        "",
        "## 逐评价者",
        "",
        "| 评价者 | 已判定/分配 | 注意力校验通过率 | 平均置信度 | 平均耗时(s) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rater, st in c["per_rater"].items():
        g = "—" if st["gold_pass_rate"] is None else f"{100*st['gold_pass_rate']:.0f}%"
        lines.append(f"| {rater} | {st['submitted']}/{st['assigned']} | {g} | "
                     f"{st['mean_confidence']} | {st['mean_seconds']} |")

    lines += ["", "## 两两偏好（A 列为左位胜率）", "",
              "| 系统 A | 系统 B | A 胜 | B 胜 | 平 | 都失败 | n | A 胜率 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for h in rep["head_to_head"]:
        lines.append(f"| {label_short(h['left'])} | {label_short(h['right'])} | {h['A']} | "
                     f"{h['B']} | {h['tie']} | {h['both_fail']} | {h['n']} | "
                     f"{h['left_win_rate']} |")

    lines += ["", "## 人类选择与自动指标的一致性（同一批配对）", "",
              "| 指标 | n | 一致率 | 显著配对 n | 显著配对一致率 |",
              "| --- | --- | --- | --- | --- |"]
    for m, v in rep["metric_agreement"].items():
        lines.append(f"| {m} | {v['n']} | {v['agreement']} | {v['decisive_n']} | "
                     f"{v['decisive_agreement']} |")

    k = rep.get("kappa_choice")
    lines += ["", "## 评价者间一致性（强制选择）", ""]
    if k:
        lines.append(
            f"- Fleiss κ = {k['kappa']}，Gwet AC1 = {k['ac1']}，"
            f"观测一致率 = {k['observed_agreement']}（n = {k['n_units']} 个配对）")
    else:
        lines.append("- 数据不足（需要每个配对至少 2 名评价者），尚无法计算。")
    lines += [f"- 选择分布：{rep['choice_mix']}", "",
              "> 注意力校验为「真实编辑 vs 同一编辑的强退化副本」，正确选择为清晰一侧；"
              "通过率明显偏低的评价者应在汇总前剔除或复核。"]
    return "\n".join(lines) + "\n"

"""Human annotation protocol (review item B5).

The proposal promises a human study in which 300-500 benchmark items are drawn
and 3-5 annotators independently verify

    (a) the object-level SCM (nodes, edges, intervention),
    (b) the grounded reasoning chain (step-by-step),
    (c) the region boxes (bounding-box IoU),

and three inter-annotator kappas are reported.

This module holds the protocol itself -- frozen stratified sampling, balanced
rater assignment, submission storage, and the agreement statistics -- so that
both the web interface (``anno_app``) and the offline report (``anno_report``)
share exactly one implementation.
"""

from __future__ import annotations

import json
import math
import os
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .bench import read_jsonl

# --------------------------------------------------------------------- paths --

ANNO_DIR = Path(os.environ.get("RIE_ANNO_DIR", config.RESULTS / "annotation"))

POOL_FILES = ("bench.jsonl", "surface.jsonl")

DEFAULT_ANNOTATORS = [
    {"id": "a1", "name": "标注者 1"},
    {"id": "a2", "name": "标注者 2"},
    {"id": "a3", "name": "标注者 3"},
    {"id": "a4", "name": "标注者 4"},
    {"id": "a5", "name": "标注者 5"},
]

SCM_LABELS = ["yes", "no", "unsure"]
VERDICT_LABELS = ["valid", "minor", "invalid"]
REGION_LABELS = ["accept", "correct"]


def anno_dir(data_dir: str | Path | None = None) -> Path:
    d = Path(data_dir) if data_dir else ANNO_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "submissions").mkdir(parents=True, exist_ok=True)
    return d


def sample_path(data_dir: str | Path | None = None) -> Path:
    return anno_dir(data_dir) / "sample.json"


def submissions_dir(data_dir: str | Path | None = None) -> Path:
    return anno_dir(data_dir) / "submissions"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# -------------------------------------------------------------------- pool ----


def load_pool(pools: tuple[str, ...] = POOL_FILES, bench_dir: Path | None = None) -> list[dict]:
    """Load and de-duplicate the candidate items of the annotation pool."""
    bench_dir = Path(bench_dir or config.BENCH_DIR)
    items: list[dict] = []
    seen: set[str] = set()
    for name in pools:
        path = bench_dir / name
        if not path.exists():
            continue
        for it in read_jsonl(path):
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            rec = dict(it)
            rec["_pool"] = name[: -len(".jsonl")]
            items.append(rec)
    return items


# ------------------------------------------------------------------ sample ----


def _largest_remainder(counts: dict, total: int) -> dict:
    """Allocate ``total`` slots over strata proportionally, largest remainder."""
    grand = sum(counts.values())
    if grand == 0:
        return {k: 0 for k in counts}
    base, frac = {}, {}
    for k, c in counts.items():
        exact = total * c / grand
        base[k] = min(c, int(math.floor(exact)))
        frac[k] = exact - math.floor(exact)
    remaining = total - sum(base.values())
    for k in sorted(frac, key=lambda x: (-frac[x], x)):
        if remaining <= 0:
            break
        if base[k] < counts[k]:
            base[k] += 1
            remaining -= 1
    return base


def assign_raters(n_items: int, annotator_ids: list[str], raters_per_item: int,
                  seed: int) -> dict[str, list[int]]:
    """Balanced assignment: every item gets ``raters_per_item`` annotators and
    every annotator gets (almost) the same number of items."""
    n_ann = len(annotator_ids)
    if n_ann < 2:
        raise ValueError("need at least two annotators")
    k = max(1, min(raters_per_item, n_ann))
    order = list(range(n_items))
    random.Random(seed + 1).shuffle(order)
    assigns: dict[str, list[int]] = {a: [] for a in annotator_ids}
    for pos, idx in enumerate(order):
        start = pos % n_ann
        for j in range(k):
            assigns[annotator_ids[(start + j) % n_ann]].append(idx)
    for a in assigns:
        assigns[a].sort()
    return assigns


def build_sample(items: list[dict], n: int = 360, seed: int = 20260926,
                 raters_per_item: int = 3,
                 annotators: list[dict] | None = None) -> dict:
    """Frozen, stratified, reproducible sample + rater assignment."""
    annotators = annotators or DEFAULT_ANNOTATORS
    rng = random.Random(seed)
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for it in items:
        strata[(it.get("_pool", "bench"), it["type"], it["meta"]["difficulty"])].append(it)
    for v in strata.values():
        rng.shuffle(v)
    alloc = _largest_remainder({k: len(v) for k, v in strata.items()}, min(n, len(items)))

    chosen: list[dict] = []
    for key in sorted(strata):
        chosen.extend(strata[key][: alloc.get(key, 0)])
    rng.shuffle(chosen)
    chosen = chosen[:n]

    ids = [it["id"] for it in chosen]
    assigns = assign_raters(len(chosen), [a["id"] for a in annotators],
                            raters_per_item, seed)
    sample = {
        "created": now_iso(),
        "seed": seed,
        "n_items": len(chosen),
        "raters_per_item": max(1, min(raters_per_item, len(annotators))),
        "pool_size": len(items),
        "pools": sorted({it.get("_pool", "bench") for it in items}),
        "annotators": annotators,
        "design": "balanced rotation (each item verified by k annotators)",
        "by_type": dict(Counter(it["type"] for it in chosen)),
        "by_domain": dict(Counter(it["domain"] for it in chosen)),
        "by_difficulty": dict(Counter(it["meta"]["difficulty"] for it in chosen)),
        "by_pool": dict(Counter(it.get("_pool", "bench") for it in chosen)),
        "items": [
            {
                "item_id": it["id"],
                "pool": it.get("_pool", "bench"),
                "image_id": it["image_id"],
                "type": it["type"],
                "domain": it["domain"],
                "difficulty": it["meta"]["difficulty"],
            }
            for it in chosen
        ],
        "assignment": {a: [ids[i] for i in idx] for a, idx in assigns.items()},
    }
    return sample


def write_sample(sample: dict, data_dir: str | Path | None = None) -> Path:
    path = sample_path(data_dir)
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=1))
    return path


def load_sample(data_dir: str | Path | None = None) -> dict:
    path = sample_path(data_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"no annotation sample at {path}; run `python -m reasondata.anno_app sample` first"
        )
    return json.loads(path.read_text())


def annotators_of(sample: dict) -> list[dict]:
    return sample.get("annotators", DEFAULT_ANNOTATORS)


# ------------------------------------------------------------- item units -----


def iou(a: list, b: list) -> float:
    """IoU of two [x1, y1, x2, y2] boxes in the 0-1000 image space."""
    if not a or not b:
        return 0.0
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def region_units(item: dict) -> list[dict]:
    """Every region box the annotator has to confirm (or redraw)."""
    units: list[dict] = []
    for node in item["scm"]["nodes"]:
        if node.get("region"):
            units.append({
                "key": f"node:{node['id']}",
                "group": "scm_node",
                "label": f"{node['id']} · {node['label']}",
                "ref": list(node["region"]),
            })
    for step in item["reasoning_chain"]:
        if step.get("region"):
            units.append({
                "key": f"step:{step['step']}",
                "group": "chain_step",
                "label": f"推理步骤 {step['step']}",
                "ref": list(step["region"]),
            })
    for eff in item["effects"]:
        if eff.get("region"):
            units.append({
                "key": f"effect:{eff['id']}",
                "group": "effect",
                "label": f"{eff['id']} · 后效区域",
                "ref": list(eff["region"]),
            })
    for pre in item["preserved"]:
        if pre.get("region"):
            units.append({
                "key": f"preserved:{pre['id']}",
                "group": "preserved",
                "label": f"{pre['id']} · 保持区域",
                "ref": list(pre["region"]),
            })
    return units


def scm_units(item: dict) -> tuple[list[dict], list[dict]]:
    nodes = [
        {
            "key": n["id"],
            "label": n["label"],
            "kind": n["kind"],
            "state_before": n.get("state_before"),
            "region": n.get("region"),
        }
        for n in item["scm"]["nodes"]
    ]
    edges = [
        {
            "key": f"{e['src']}->{e['dst']}",
            "src": e["src"],
            "dst": e["dst"],
            "relation": e.get("relation"),
            "mechanism": e.get("mechanism"),
        }
        for e in item["scm"]["edges"]
    ]
    return nodes, edges


def public_item(item: dict, index: int, total: int, prev_id: str | None,
                next_id: str | None, submission: dict | None) -> dict:
    """The payload the browser needs for one item."""
    nodes, edges = scm_units(item)
    return {
        "index": index,
        "total": total,
        "prev": prev_id,
        "next": next_id,
        "item": {
            "id": item["id"],
            "pool": item.get("_pool", "bench"),
            "image_id": item["image_id"],
            "type": item["type"],
            "domain": item["domain"],
            "difficulty": item["meta"]["difficulty"],
            "instruction": item["instruction"],
            "scm": item["scm"],
            "reasoning_chain": item["reasoning_chain"],
            "effects": item["effects"],
            "preserved": item["preserved"],
            "counterfactual": item.get("counterfactual"),
            "meta": item["meta"],
        },
        "nodes": nodes,
        "edges": edges,
        "regions": region_units(item),
        "submission": submission,
        "labels": {
            "scm": SCM_LABELS,
            "verdict": VERDICT_LABELS,
            "region": REGION_LABELS,
        },
    }


# ----------------------------------------------------------- submissions ------


def submission_file(annotator: str, data_dir: str | Path | None = None) -> Path:
    safe = "".join(c for c in annotator if c.isalnum() or c in "-_.") or "anon"
    return submissions_dir(data_dir) / f"{safe}.jsonl"


def load_submissions(data_dir: str | Path | None = None) -> dict[str, dict[str, dict]]:
    """annotator -> item_id -> latest record."""
    out: dict[str, dict[str, dict]] = {}
    for path in sorted(submissions_dir(data_dir).glob("*.jsonl")):
        per_item: dict[str, dict] = {}
        for rec in read_jsonl(path):
            per_item[rec["item_id"]] = rec
        out[path.stem] = per_item
    return out


def append_submission(record: dict, data_dir: str | Path | None = None) -> None:
    """Append-only storage: the newest record for an item wins."""
    path = submission_file(record["annotator"], data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalise_submission(rec: dict, sample: dict, item: dict) -> dict:
    """Keep only the fields the report reads, and derive the region IoUs."""
    regions_in: dict = rec.get("regions") or {}
    regions_out: dict[str, dict] = {}
    for unit in region_units(item):
        raw = regions_in.get(unit["key"]) or {}
        decision = raw.get("decision") or "accept"
        box = raw.get("box")
        entry: dict = {"decision": "correct" if decision == "correct" else "accept",
                       "group": unit["group"], "ref": unit["ref"]}
        if entry["decision"] == "correct" and box:
            box = [round(float(v), 1) for v in box]
            entry["box"] = box
            entry["iou"] = round(iou(box, unit["ref"]), 4)
        else:
            entry["decision"] = "accept"
            entry["box"] = list(unit["ref"])
            entry["iou"] = 1.0
        regions_out[unit["key"]] = entry

    nodes, edges = scm_units(item)
    scm_in = rec.get("scm") or {}
    scm = {
        "verdict": scm_in.get("verdict"),
        "note": (scm_in.get("note") or "").strip()[:2000],
        "nodes": {n["key"]: (scm_in.get("nodes") or {}).get(n["key"], "yes") for n in nodes},
        "edges": {e["key"]: (scm_in.get("edges") or {}).get(e["key"], "yes") for e in edges},
        "intervention": scm_in.get("intervention") or "yes",
    }
    chain_in = rec.get("chain") or {}
    chain = {
        "verdict": chain_in.get("verdict"),
        "note": (chain_in.get("note") or "").strip()[:2000],
        "steps": {
            str(s["step"]): (chain_in.get("steps") or {}).get(str(s["step"]), "yes")
            for s in item["reasoning_chain"]
        },
    }
    return {
        "annotator": rec.get("annotator"),
        "item_id": item["id"],
        "item_type": item["type"],
        "pool": item.get("_pool", "bench"),
        "submitted": rec.get("submitted") or now_iso(),
        "started": rec.get("started"),
        "duration_s": rec.get("duration_s"),
        "scm": scm,
        "chain": chain,
        "regions": regions_out,
        "region_verdict": (rec.get("region_verdict") or "").strip() or None,
        "notes": (rec.get("notes") or "").strip()[:2000],
    }


# ------------------------------------------------------------ agreement -------


def fleiss_kappa(labels_per_unit: list[list[str]], categories: list[str]) -> dict | None:
    """Fleiss' kappa for a fixed number of raters per unit."""
    units = [u for u in labels_per_unit if len(u) >= 2]
    if not units:
        return None
    n_raters = len(units[0])
    if any(len(u) != n_raters for u in units):
        # keep the modal rater count so partial overlap cannot corrupt P_e
        common = Counter(len(u) for u in units).most_common(1)[0][0]
        units = [u for u in units if len(u) == common]
        n_raters = common
        if n_raters < 2:
            return None
    n_units = len(units)
    counts = [[sum(1 for x in u if x == c) for c in categories] for u in units]
    p_i = [(sum(c * (c - 1) for c in row)) / (n_raters * (n_raters - 1)) for row in counts]
    p_bar = sum(p_i) / n_units
    total = n_units * n_raters
    p_j = [sum(row[j] for row in counts) / total for j in range(len(categories))]
    p_e = sum(p * p for p in p_j)

    # Gwet's AC1 -- stable under the heavy prevalence of "yes" answers.
    q = len(categories)
    p_e_ac1 = sum(p * (1 - p) for p in p_j) / (q - 1) if q > 1 else 0.0
    # With a single category in play (e.g. every rater approves every edge) the
    # chance term saturates and kappa is undefined rather than 1.0; say so instead
    # of emitting a misleading number (or a NaN that breaks JSON).
    kappa = (p_bar - p_e) / (1 - p_e) if p_e < 1 else None
    ac1 = (p_bar - p_e_ac1) / (1 - p_e_ac1) if p_e_ac1 < 1 else None
    return {
        "kappa": round(float(kappa), 4) if kappa is not None else None,
        "ac1": round(float(ac1), 4) if ac1 is not None else None,
        "kappa_defined": kappa is not None,
        "observed_agreement": round(float(p_bar), 4),
        "expected_agreement": round(float(p_e), 4),
        "n_units": n_units,
        "n_raters": n_raters,
        "n_categories_used": sum(1 for p in p_j if p > 0),
        "category_share": {c: round(p, 4) for c, p in zip(categories, p_j)},
    }


def pairwise_kappa(labels_by_annotator: dict[str, dict[str, str]], categories: list[str]) -> dict:
    """Mean pairwise Cohen's kappa over units two annotators both rated."""
    from sklearn.metrics import cohen_kappa_score

    anns = sorted(labels_by_annotator)
    pairs, vals = 0, []
    for i in range(len(anns)):
        for j in range(i + 1, len(anns)):
            a, b = labels_by_annotator[anns[i]], labels_by_annotator[anns[j]]
            common = sorted(set(a) & set(b))
            if len(common) < 5:
                continue
            x = [a[u] for u in common]
            y = [b[u] for u in common]
            if len(set(x)) == 1 and len(set(y)) == 1 and x[0] == y[0]:
                k = 1.0  # degenerate but perfect agreement
            else:
                k = float(cohen_kappa_score(x, y, labels=categories))
            if k == k:
                vals.append(k)
                pairs += 1
    if not vals:
        return {"mean": None, "n_pairs": 0}
    return {"mean": round(sum(vals) / len(vals), 4), "n_pairs": pairs}


def _labels_by_unit(records: dict[str, dict], unit_of) -> dict[str, dict[str, str]]:
    """annotator -> unit_id -> label, for one verification target."""
    out: dict[str, dict[str, str]] = {}
    for ann, per_item in records.items():
        flat: dict[str, str] = {}
        for item_id, rec in per_item.items():
            for unit_key, label in unit_of(rec).items():
                if label:
                    flat[f"{item_id}|{unit_key}"] = label
        out[ann] = flat
    return out


def _units_to_rating_lists(labels: dict[str, dict[str, str]]) -> list[list[str]]:
    by_unit: dict[str, list[str]] = defaultdict(list)
    for _, flat in labels.items():
        for unit_id, label in flat.items():
            by_unit[unit_id].append(label)
    return [v for v in by_unit.values() if len(v) >= 2]


def _target_block(labels: dict[str, dict[str, str]], categories: list[str]) -> dict:
    lists = _units_to_rating_lists(labels)
    fleiss = fleiss_kappa(lists, categories)
    block = {
        "kappa": None, "ac1": None, "n_units": 0, "n_ratings": 0,
        "pairwise_cohen_mean": None,
        "category_share": {},
    }
    if fleiss:
        block.update(fleiss)
    block["n_ratings"] = sum(len(v) for v in labels.values())
    block["pairwise_cohen_mean"] = pairwise_kappa(labels, categories)["mean"]
    return block


def region_iou_stats(records: dict[str, dict], items: dict[str, dict]) -> dict:
    """IoU between annotators' effective boxes and against the reference box."""
    per_unit: dict[str, dict[str, list]] = defaultdict(dict)
    for ann, per_item in records.items():
        for item_id, rec in per_item.items():
            for key, entry in rec["regions"].items():
                unit_id = f"{item_id}|{key}"
                per_unit[unit_id][ann] = entry.get("box")
    to_ref, pairwise, corrected, total = [], [], 0, 0
    for unit_id, boxes in per_unit.items():
        # reference box comes from the bench item
        item_id, key = unit_id.split("|", 1)
        item = items.get(item_id)
        ref = None
        if item is not None:
            for u in region_units(item):
                if u["key"] == key:
                    ref = u["ref"]
                    break
        if ref is None:
            continue
        boxes = {a: b for a, b in boxes.items() if b}
        for box in boxes.values():
            to_ref.append(iou(box, ref))
        anns = sorted(boxes)
        for i in range(len(anns)):
            for j in range(i + 1, len(anns)):
                pairwise.append(iou(boxes[anns[i]], boxes[anns[j]]))
        total += 1
    # corrected rate over all annotations
    all_units = 0
    for per_item in records.values():
        for rec in per_item.values():
            for entry in rec["regions"].values():
                all_units += 1
                if entry["decision"] == "correct":
                    corrected += 1
    return {
        "n_regions_scored": total,
        "mean_iou_to_reference": round(sum(to_ref) / len(to_ref), 4) if to_ref else None,
        "mean_pairwise_iou": round(sum(pairwise) / len(pairwise), 4) if pairwise else None,
        "accept_rate": round(1 - corrected / all_units, 4) if all_units else None,
        "corrected_rate": round(corrected / all_units, 4) if all_units else None,
        "n_region_annotations": all_units,
    }


def region_iou_kappa(records: dict[str, dict], items: dict[str, dict],
                     threshold: float = 0.5) -> dict:
    """Kappa on the binarised decision ``IoU(effective box, reference) >= t``."""
    labels: dict[str, dict[str, str]] = {}
    for ann, per_item in records.items():
        flat = {}
        for item_id, rec in per_item.items():
            item = items.get(item_id)
            if item is None:
                continue
            refs = {u["key"]: u["ref"] for u in region_units(item)}
            for key, entry in rec["regions"].items():
                ref = refs.get(key)
                if ref is None:
                    continue
                box = entry.get("box") or ref
                flat[f"{item_id}|{key}"] = "ok" if iou(box, ref) >= threshold else "off"
        labels[ann] = flat
    block = _target_block(labels, ["ok", "off"])
    block["threshold"] = threshold
    return block


def compute_report(data_dir: str | Path | None = None, bench: str = "bench.jsonl",
                   surface: str = "surface.jsonl") -> dict:
    """The full B5 report: three kappas plus coverage and per-annotator detail."""
    sample = load_sample(data_dir)
    items = {it["id"]: it for it in load_pool((bench, surface))}
    records = load_submissions(data_dir)

    expected_per_item = sample["raters_per_item"]
    submitted_per_item: Counter = Counter()
    for per_item in records.values():
        for item_id in per_item:
            submitted_per_item[item_id] += 1

    scm_edges = _labels_by_unit(records, lambda r: r["scm"]["edges"])
    scm_nodes = _labels_by_unit(records, lambda r: r["scm"]["nodes"])
    scm_inter = _labels_by_unit(records, lambda r: {"intervention": r["scm"]["intervention"]})
    scm_verdict = _labels_by_unit(records, lambda r: {"verdict": r["scm"]["verdict"]})
    chain_steps = _labels_by_unit(records, lambda r: r["chain"]["steps"])
    chain_verdict = _labels_by_unit(records, lambda r: {"verdict": r["chain"]["verdict"]})
    regions = _labels_by_unit(records, lambda r: {k: v["decision"] for k, v in r["regions"].items()})

    agreement = {
        "scm_edges": _target_block(scm_edges, SCM_LABELS),
        "scm_nodes": _target_block(scm_nodes, SCM_LABELS),
        "scm_intervention": _target_block(scm_inter, SCM_LABELS),
        "scm_verdict": _target_block(scm_verdict, VERDICT_LABELS),
        "chain_steps": _target_block(chain_steps, SCM_LABELS),
        "chain_verdict": _target_block(chain_verdict, VERDICT_LABELS),
        "region_decision": _target_block(regions, REGION_LABELS),
        "region_iou": region_iou_kappa(records, items),
    }

    per_annotator = {}
    for ann in [a["id"] for a in annotators_of(sample)]:
        per_item = records.get(ann, {})
        durations = [r["duration_s"] for r in per_item.values() if r.get("duration_s")]
        n_regions = sum(len(r["regions"]) for r in per_item.values())
        n_corrected = sum(
            1 for r in per_item.values() for e in r["regions"].values() if e["decision"] == "correct"
        )
        edge_labels = [v for r in per_item.values() for v in r["scm"]["edges"].values()]
        step_labels = [v for r in per_item.values() for v in r["chain"]["steps"].values()]
        per_annotator[ann] = {
            "submitted": len(per_item),
            "assigned": len(sample["assignment"].get(ann, [])),
            "mean_duration_s": round(sum(durations) / len(durations), 1) if durations else None,
            "edge_yes_rate": round(sum(1 for v in edge_labels if v == "yes") / len(edge_labels), 4)
            if edge_labels else None,
            "step_yes_rate": round(sum(1 for v in step_labels if v == "yes") / len(step_labels), 4)
            if step_labels else None,
            "region_accept_rate": round(1 - n_corrected / n_regions, 4) if n_regions else None,
            "scm_verdicts": dict(Counter(r["scm"]["verdict"] for r in per_item.values())),
            "chain_verdicts": dict(Counter(r["chain"]["verdict"] for r in per_item.values())),
        }

    def primary(block: dict) -> float | None:
        return block.get("kappa")

    report = {
        "generated": now_iso(),
        "protocol": {
            "n_items": sample["n_items"],
            "raters_per_item": sample["raters_per_item"],
            "n_annotators": len(annotators_of(sample)),
            "seed": sample["seed"],
            "created": sample["created"],
            "by_type": sample["by_type"],
            "by_domain": sample["by_domain"],
            "by_pool": sample["by_pool"],
            "design": sample["design"],
        },
        "coverage": {
            "item_annotations_expected": sample["n_items"] * sample["raters_per_item"],
            "item_annotations_submitted": sum(len(v) for v in records.values()),
            "items_with_full_k_raters": sum(
                1 for it in sample["items"]
                if submitted_per_item[it["item_id"]] >= expected_per_item
            ),
            "annotators_active": sorted(records),
            "per_annotator": per_annotator,
        },
        "agreement": agreement,
        "region_iou": region_iou_stats(records, items),
        "primary": {
            "kappa_scm": primary(agreement["scm_edges"]),
            "kappa_chain": primary(agreement["chain_steps"]),
            "kappa_region": primary(agreement["region_decision"]),
            "kappa_scm_verdict": primary(agreement["scm_verdict"]),
            "kappa_chain_verdict": primary(agreement["chain_verdict"]),
            "kappa_region_iou": primary(agreement["region_iou"]),
        },
    }
    return report


def kappa_band(value: float | None) -> str:
    """Landis & Koch interpretation."""
    if value is None:
        return "n/a"
    if value < 0:
        return "poor"
    if value <= 0.20:
        return "slight"
    if value <= 0.40:
        return "fair"
    if value <= 0.60:
        return "moderate"
    if value <= 0.80:
        return "substantial"
    return "almost perfect"


def report_markdown(report: dict) -> str:
    a = report["agreement"]
    p = report["protocol"]
    cov = report["coverage"]
    r = report["region_iou"]

    def row(name: str, block: dict) -> str:
        k = block.get("kappa")
        ks = "—" if k is None else f"{k:.3f}"
        ac = block.get("ac1")
        acs = "—" if ac is None else f"{ac:.3f}"
        pw = block.get("pairwise_cohen_mean")
        pws = "—" if pw is None else f"{pw:.3f}"
        return (f"| {name} | {block.get('n_units', 0)} | {block.get('n_ratings', 0)} | "
                f"{ks} | {acs} | {pws} | {kappa_band(k)} |")

    lines = [
        "# 人工标注协议报告（B5）",
        "",
        f"- 生成时间：{report['generated']}",
        f"- 样本：{p['n_items']} 条（池 {report['protocol']['by_pool']}），"
        f"每条由 {p['raters_per_item']} 名标注者独立校验，共 {p['n_annotators']} 名标注者",
        f"- 抽样设计：{p['design']}，seed={p['seed']}（{p['created']}）",
        f"- 进度：{cov['items_with_full_k_raters']}/{p['n_items']} 条已满 {p['raters_per_item']} 人；"
        f"已收 {cov['item_annotations_submitted']}/{cov['item_annotations_expected']} 份标注",
        "",
        "## 三套 κ（主要结果）",
        "",
        "| 校验目标 | κ | AC1 | 一致性带宽 |",
        "| --- | --- | --- | --- |",
    ]
    for name, key in (("SCM 结构（因果边逐条）", "scm_edges"),
                      ("推理链（逐步骤）", "chain_steps"),
                      ("区域框（接受/重画）", "region_decision")):
        block = a[key]
        k = block.get("kappa")
        ac = block.get("ac1")
        lines.append(
            f"| {name} | {'—' if k is None else f'{k:.3f}'} | "
            f"{'—' if ac is None else f'{ac:.3f}'} | {kappa_band(k)} |"
        )

    lines += [
        "",
        "## 全部一致性统计",
        "",
        "| 单位 | 单元数 | 判定数 | Fleiss κ | Gwet AC1 | 平均成对 Cohen κ | 带宽 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        row("SCM 因果边", a["scm_edges"]),
        row("SCM 节点状态", a["scm_nodes"]),
        row("SCM 干预节点", a["scm_intervention"]),
        row("SCM 整体判定（有效/需修正/无效）", a["scm_verdict"]),
        row("推理链步骤", a["chain_steps"]),
        row("推理链整体判定", a["chain_verdict"]),
        row("区域框接受/重画", a["region_decision"]),
        row("区域 IoU ≥ 0.5（与参考框）", a["region_iou"]),
        "",
        "## 区域 IoU",
        "",
        f"- 覆盖 {r['n_regions_scored']} 个区域、{r['n_region_annotations']} 次判定",
        f"- 与参考框的平均 IoU：{r['mean_iou_to_reference']}",
        f"- 标注者之间的平均成对 IoU：{r['mean_pairwise_iou']}",
        f"- 接受率 {r['accept_rate']}，重画率 {r['corrected_rate']}",
        "",
        "## 逐标注者",
        "",
        "| 标注者 | 已标/分配 | 平均耗时(s) | 边判 yes 率 | 步骤 yes 率 | 区域接受率 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for ann, st in cov["per_annotator"].items():
        lines.append(
            f"| {ann} | {st['submitted']}/{st['assigned']} | {st['mean_duration_s']} | "
            f"{st['edge_yes_rate']} | {st['step_yes_rate']} | {st['region_accept_rate']} |"
        )
    lines += [
        "",
        "> κ 采用 Fleiss' κ（每条目固定 k 名标注者）；由于标注以「是/接受」为主，"
        "同时报告对流行度不敏感的 Gwet AC1，论文中建议两者并列。",
        "",
    ]
    return "\n".join(lines)


def report_latex(report: dict) -> str:
    a = report["agreement"]
    p = report["protocol"]
    rows = []
    for label, key in (("SCM structure (per edge)", "scm_edges"),
                       ("Reasoning chain (per step)", "chain_steps"),
                       ("Region boxes (accept/redraw)", "region_decision")):
        b = a[key]
        k = b.get("kappa")
        ac = b.get("ac1")
        rows.append(
            f"{label} & {b.get('n_units', 0)} & {b.get('n_ratings', 0)} & "
            f"{'--' if k is None else f'{k:.3f}'} & {'--' if ac is None else f'{ac:.3f}'} \\\\"
        )
    table = "\n".join([
        "% generated by `python -m reasondata.anno_report`",
        "\\begin{table}[t]",
        "\\centering\\small",
        "\\caption{Inter-annotator agreement of the human verification study "
        f"({p['n_items']} items, {p['raters_per_item']} annotators per item, "
        f"{p['n_annotators']} annotators in total). $\\kappa$ is Fleiss' $\\kappa$; "
        "AC1 is Gwet's agreement coefficient, which is robust to the skewed "
        "prevalence of approvals.}",
        "\\label{tab:annotation-agreement}",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Verification target & Units & Ratings & $\\kappa$ & AC1 \\\\",
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])
    return table


def report_macros(report: dict) -> str:
    """LaTeX macros; names are pure letters on purpose (see the paper's macro
    naming lesson: digits break \\newcommand names)."""
    p = report["primary"]
    iou_stats = report["region_iou"]
    protocol = report["protocol"]

    def fmt(value, digits=3) -> str:
        return "--" if value is None else f"{value:.{digits}f}"

    lines = [
        "% generated by `python -m reasondata.anno_report` -- do not edit by hand",
        f"\\newcommand{{\\HAnnoItems}}{{{protocol['n_items']}}}",
        f"\\newcommand{{\\HAnnoRaterPerItem}}{{{protocol['raters_per_item']}}}",
        f"\\newcommand{{\\HAnnoAnnotators}}{{{protocol['n_annotators']}}}",
        f"\\newcommand{{\\HKappaSCM}}{{{fmt(p['kappa_scm'])}}}",
        f"\\newcommand{{\\HKappaChain}}{{{fmt(p['kappa_chain'])}}}",
        f"\\newcommand{{\\HKappaRegion}}{{{fmt(p['kappa_region'])}}}",
        f"\\newcommand{{\\HKappaSCMVerdict}}{{{fmt(p['kappa_scm_verdict'])}}}",
        f"\\newcommand{{\\HKappaChainVerdict}}{{{fmt(p['kappa_chain_verdict'])}}}",
        f"\\newcommand{{\\HKappaRegionIou}}{{{fmt(p['kappa_region_iou'])}}}",
        f"\\newcommand{{\\HRegionIouRef}}{{{fmt(iou_stats['mean_iou_to_reference'])}}}",
        f"\\newcommand{{\\HRegionIouPair}}{{{fmt(iou_stats['mean_pairwise_iou'])}}}",
        f"\\newcommand{{\\HRegionAcceptRate}}{{{fmt(iou_stats['accept_rate'])}}}",
        "",
    ]
    import re
    for line in lines:
        m = re.match(r"\\newcommand\{\\([A-Za-z]+)\}", line)
        if m and not m.group(1).isalpha():
            raise ValueError(f"macro name with non-letters: {m.group(1)}")
    return "\n".join(lines)


def write_report_files(report: dict, out_dir: str | Path | None = None,
                       tables_dir: Path | None = None) -> dict[str, Path]:
    out = anno_dir(out_dir)
    paths: dict[str, Path] = {}
    paths["json"] = out / "report.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=1))
    paths["md"] = out / "report.md"
    paths["md"].write_text(report_markdown(report))
    if report["coverage"]["item_annotations_submitted"] == 0:
        # Nothing annotated yet: do not drop a placeholder table/macros into the
        # paper tree, where they would look like real (all "--") results.
        return paths
    paths["macros"] = out / "numbers_annotation.tex"
    paths["macros"].write_text(report_macros(report))
    tables_dir = Path(tables_dir or (config.ROOT / "paper" / "tables"))
    tables_dir.mkdir(parents=True, exist_ok=True)
    paths["table"] = tables_dir / "annotation_agreement.tex"
    paths["table"].write_text(report_latex(report))
    return paths

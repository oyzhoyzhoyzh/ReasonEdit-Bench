"""Aggregate probe verdicts and reference metrics into bench-level scores,
failure attribution and the tables used in the paper.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .bench import load_bench, read_jsonl
from .runs import label

FAILURE_NAMES = {
    "OK": "no error",
    "IUE": "instruction understanding error",
    "RPE": "reasoning / planning error",
    "GE": "region grounding error",
    "PQE": "pixel generation error",
    "CI": "causal inconsistency",
}


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_probe_scores(results_dir: Path | None = None, pattern: str = "probes_*.jsonl") -> dict:
    root = Path(results_dir or config.RESULTS)
    per: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    seen: set[str] = set()
    if "*" in pattern:
        import glob as _glob

        pat = pattern if Path(pattern).is_absolute() else str(root / pattern)
        paths = [Path(p) for p in sorted(_glob.glob(pat))]
    else:
        paths = [Path(pattern)]
    for path in paths:
        if not path.exists():
            continue
        for rec in read_jsonl(path):
            if rec.get("pid") in seen:      # the same probe may be judged twice
                continue
            seen.add(rec.get("pid"))
            key = (rec["item_id"], rec["system"])
            per[key][rec["kind"]].append(rec)
    return per


def load_auto_scores(results_dir: Path | None = None, name: str = "auto_metrics.jsonl") -> dict:
    root = Path(results_dir or config.RESULTS)
    out = {}
    path = Path(name) if "*" not in name and str(name).endswith(".jsonl") else root / name
    if not path.is_absolute():
        path = root / path
    if path.exists():
        for rec in read_jsonl(path):
            out[(rec["item_id"], rec["system"])] = rec
    return out


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def score_pair(item: dict, probes: dict, auto: dict | None) -> dict:
    # Keep DPS semantically restricted to descendants. Older probe files used
    # ``dps`` for every required-effect record, including one explicitly
    # requested maintained state; normalise that record here so existing raw
    # verdicts remain reusable without changing the benchmark's definition.
    probes = {kind: list(values) for kind, values in probes.items()}
    non_desc = {e["id"] for e in item.get("effects", [])
                if not e.get("is_descendant", True)}
    moved = []
    kept = []
    for p in probes.get("dps", []):
        suffix = p.get("pid", "").rsplit("|", 1)[-1]
        if suffix in non_desc:
            q = dict(p)
            q["kind"] = "nps"
            moved.append(q)
        else:
            kept.append(p)
    probes["dps"] = kept
    if moved:
        probes["nps"] = list(probes.get("nps", [])) + moved

    def vals(kind):
        return [p["value"] for p in probes.get(kind, [])]

    tcs_v = vals("tcs")
    dps_v = vals("dps")
    nps_v = vals("nps")
    qua_v = vals("qua")
    if not tcs_v or not dps_v or not nps_v:
        return {}

    tcs = float(np.mean(tcs_v))
    dps = float(np.mean(dps_v))
    nps = float(np.mean(nps_v))
    qua = float(np.mean(qua_v)) if qua_v else 1.0
    dps_strict = float(np.mean([v >= 1.0 for v in dps_v]))
    nps_strict = float(np.mean([v >= 1.0 for v in nps_v]))

    # order-consistent chain score for the multi-step domain
    ocs = None
    if item["domain"] == "multi_step":
        ordered = sorted(probes.get("dps", []), key=lambda p: (p.get("ordinal") or 0))
        acc = 0
        ok_prefix = True
        for p in ordered:
            if ok_prefix and p["value"] >= 1.0:
                acc += 1
            else:
                ok_prefix = False
        ocs = acc / max(1, len(ordered))

    ccs = (tcs + dps + nps) / 3.0
    rec = {
        "item_id": item["id"], "system": probes["tcs"][0]["system"],
        "domain": item["domain"], "type": item["type"],
        "difficulty": item["meta"]["difficulty"],
        "chain_length": item["meta"]["chain_length"],
        "num_nodes": item["meta"]["num_nodes"], "depth": item["meta"]["depth"],
        "num_effects": item["meta"]["num_effects"],
        "tcs": tcs, "dps": dps, "nps": nps, "qua": qua,
        "dps_strict": dps_strict, "nps_strict": nps_strict,
        "ccs": ccs, "ocs": ocs,
        "n_probes": len(tcs_v) + len(dps_v) + len(nps_v) + len(qua_v),
    }
    if auto:
        rec.update({k: auto.get(k) for k in ("clipscore", "clip_i", "dino_i", "lpips")})
    rec["failure"] = attribute_failure(rec)
    rec["success"] = rec["failure"] == "OK"
    rec["strict_success"] = (tcs >= 1.0 and dps_strict >= 1.0 and nps_strict >= 1.0)
    return rec


def attribute_failure(rec: dict) -> str:
    """Deterministic failure attribution rule (see the paper, Sec. diagnosis)."""
    lpips = rec.get("lpips")
    dino = rec.get("dino_i")
    changed = (lpips is None) or (lpips > 0.02) or (dino is not None and dino < 0.985)
    big_change = (lpips is not None and lpips > 0.25) or (dino is not None and dino < 0.90)
    if not changed:
        return "IUE"
    if rec["tcs"] < 1.0:
        return "GE" if big_change else "IUE"
    if rec["dps_strict"] < 0.75:
        return "RPE"
    if rec["nps"] < 0.75:
        return "CI"
    if rec["qua"] < 1.0:
        return "PQE"
    return "OK"


def build_table(results_dir: Path | None = None, bench: str = "bench.jsonl",
                probe_pattern: str = "probes_*.jsonl",
                auto_name: str = "auto_metrics.jsonl",
                systems: list[str] | None = None) -> list[dict]:
    items = {it["id"]: it for it in load_bench(bench)}
    probes = load_probe_scores(results_dir, probe_pattern)
    autos = load_auto_scores(results_dir, auto_name)
    rows = []
    for (item_id, system), kinds in probes.items():
        if systems and system not in systems:
            continue
        item = items.get(item_id)
        if not item:
            continue
        rec = score_pair(item, kinds, autos.get((item_id, system)))
        if rec:
            rows.append(rec)
    return rows


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def summarize(rows: list[dict], group_keys=("system",)) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in group_keys)].append(r)
    out = []
    for key, rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        d = dict(zip(group_keys, key))
        d.update({
            "n": len(rs),
            "tcs": np.mean([r["tcs"] for r in rs]),
            "dps": np.mean([r["dps"] for r in rs]),
            "nps": np.mean([r["nps"] for r in rs]),
            "ccs": np.mean([r["ccs"] for r in rs]),
            "ocs": np.mean([r["ocs"] for r in rs if r["ocs"] is not None])
            if any(r["ocs"] is not None for r in rs) else None,
            "success": np.mean([r["success"] for r in rs]),
            "strict_success": np.mean([r["strict_success"] for r in rs]),
            "clipscore": np.nanmean([r.get("clipscore", np.nan) for r in rs]),
            "clip_i": np.nanmean([r.get("clip_i", np.nan) for r in rs]),
            "dino_i": np.nanmean([r.get("dino_i", np.nan) for r in rs]),
            "lpips": np.nanmean([r.get("lpips", np.nan) for r in rs]),
        })
        fails = Counter(r["failure"] for r in rs)
        for k in FAILURE_NAMES:
            d[f"fail_{k}"] = fails.get(k, 0) / max(1, len(rs))
        out.append(d)
    return out


def bootstrap_ci(values: list[float], n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    vals = list(values)
    if not vals:
        return (float("nan"), float("nan"))
    stats = []
    for _ in range(n_boot):
        sample = [vals[rng.randrange(len(vals))] for _ in vals]
        stats.append(sum(sample) / len(sample))
    stats.sort()
    return stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]


def fmt(value, digits=3) -> str:
    if value is None:
        return "--"
    if isinstance(value, float) and (np.isnan(value)):
        return "--"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(c[0] for c in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = []
    for r in rows:
        cells = []
        for _, k in columns:
            v = r.get(k)
            cells.append(fmt(v) if isinstance(v, float) else ("--" if v is None else str(v)))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.RESULTS / "analysis"))
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--probe-pattern", default="probes_*.jsonl")
    ap.add_argument("--auto-name", default="auto_metrics.jsonl")
    ap.add_argument("--systems", default=None,
                    help="comma separated system names (default: the six final systems)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from .runs import FINAL_SYSTEMS

    systems = args.systems.split(",") if args.systems else FINAL_SYSTEMS
    rows = build_table(bench=args.bench, probe_pattern=args.probe_pattern,
                       auto_name=args.auto_name, systems=systems)
    if not rows:
        print("no scored rows yet")
        return
    with (out_dir / "scores.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    main_cols = [("System", "system"), ("TCS", "tcs"), ("DPS", "dps"), ("NPS", "nps"),
                 ("CCS", "ccs"), ("OCS", "ocs"), ("Succ", "success"),
                 ("CLIP-S", "clipscore"), ("DINO-I", "dino_i"), ("LPIPS", "lpips")]
    summary = summarize(rows)
    for r in summary:
        r["system"] = label(r["system"])

    lines = ["# ReasonEdit-Bench results", ""]
    lines.append(f"## Overall (all {len({r['item_id'] for r in rows})} items, "
                 f"{len({r['system'] for r in rows})} systems)")
    lines.append(markdown_table(summary, main_cols))
    lines.append("")

    for key, title in (("domain", "Task domain"), ("difficulty", "Difficulty"),
                       ("type", "Fine-grained task type")):
        sub = summarize(rows, ("system", key))
        by_system = defaultdict(list)
        for r in sub:
            by_system[label(r["system"])].append(r)
        lines.append(f"## CCS by {title}")
        lines.append("")
        for sysname, rs in sorted(by_system.items()):
            cols = [(title, key), ("CCS", "ccs"), ("DPS", "dps"), ("NPS", "nps"),
                    ("Succ", "success"), ("n", "n")]
            lines.append(f"### {sysname}")
            lines.append(markdown_table(rs, cols))
            lines.append("")

    # failure distribution
    fails = summarize(rows, ("system",))
    cols = [("System", "system")] + [(FAILURE_NAMES[k], f"fail_{k}") for k in FAILURE_NAMES]
    for r in fails:
        r["system"] = label(r["system"])
    lines.append("## Failure attribution")
    lines.append(markdown_table(fails, cols))
    lines.append("")

    (out_dir / "tables.md").write_text("\n".join(lines))
    (out_dir / "summary.json").write_text(json.dumps(
        {"overall": summary, "n_rows": len(rows)}, indent=2, ensure_ascii=False))
    print("\n".join(lines[:40]))
    print(f"\nwrote {out_dir/'tables.md'}")


if __name__ == "__main__":
    main()

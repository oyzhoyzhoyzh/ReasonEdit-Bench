"""Statistical analysis and figures for the paper."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .aggregate import FAILURE_NAMES, bootstrap_ci, summarize
from .bench import read_jsonl
from .runs import label


def paired_bootstrap(a: list[float], b: list[float], n_boot: int = 5000,
                     seed: int = 0) -> tuple[float, float, float]:
    """Paired bootstrap of mean(a) - mean(b)."""
    assert len(a) == len(b)
    rng = random.Random(seed)
    diffs = np.array(a) - np.array(b)
    mean = float(diffs.mean())
    stats = []
    n = len(diffs)
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(float(diffs[idx].mean()))
    stats.sort()
    lo, hi = stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]
    p = 2 * min(sum(1 for s in stats if s <= 0) / n_boot,
                sum(1 for s in stats if s >= 0) / n_boot)
    return mean, lo, hi, p


def spearman(x: list[float], y: list[float]) -> float:
    from scipy.stats import spearmanr

    if len(x) < 5:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def kappa(a: list[str], b: list[str]) -> float:
    from sklearn.metrics import cohen_kappa_score

    return float(cohen_kappa_score(a, b))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--human", default=str(config.RESULTS / "human_eval" / "ratings.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(Path(args.scores))
    from .runs import FINAL_SYSTEMS

    rows = [r for r in rows if r["system"] in FINAL_SYSTEMS]
    report: dict = {}

    # ---------------------------------------------------- system comparison --
    by_sys = defaultdict(dict)
    for r in rows:
        by_sys[r["system"]][r["item_id"]] = r
    systems = sorted(by_sys)
    base = "qwen_image_edit"
    comparisons = {}
    if base in by_sys:
        for s in systems:
            if s == base:
                continue
            common = sorted(set(by_sys[s]) & set(by_sys[base]))
            if len(common) < 20:
                continue
            a = [by_sys[s][i]["ccs"] for i in common]
            b = [by_sys[base][i]["ccs"] for i in common]
            m, lo, hi, p = paired_bootstrap(a, b)
            comparisons[s] = {"delta_ccs": m, "ci": [lo, hi], "p": p, "n": len(common)}
    report["vs_base_ccs"] = comparisons

    # ------------------------------------------------- monotonicity trends --
    trends = {}
    for s in systems:
        rs = sorted(by_sys[s].values(), key=lambda r: r["chain_length"])
        buckets = defaultdict(list)
        for r in rs:
            buckets[min(r["chain_length"], 6)].append(r["ccs"])
        trends[s] = {str(k): {"n": len(v), "ccs": float(np.mean(v))}
                     for k, v in sorted(buckets.items())}
    report["ccs_by_chain_length"] = trends

    depth_trends = {}
    for s in systems:
        buckets = defaultdict(list)
        for r in by_sys[s].values():
            buckets[min(r["depth"], 5)].append(r["ccs"])
        depth_trends[s] = {str(k): {"n": len(v), "ccs": float(np.mean(v))}
                           for k, v in sorted(buckets.items())}
    report["ccs_by_graph_depth"] = depth_trends

    # ------------------------------------------- metric / human agreement --
    human_path = Path(args.human)
    if human_path.exists():
        hr = read_jsonl(human_path)
        score_by = {(r["item_id"], r["system"]): r for r in rows}
        metrics = defaultdict(list)
        for h in hr:
            r = score_by.get((h["item_id"], h["system"]))
            if not r:
                continue
            metrics["ccs"].append((r["ccs"], float(h["logical"])))
            metrics["dps"].append((r["dps"], float(h["logical"])))
            metrics["clipscore"].append((r.get("clipscore", np.nan), float(h["instruction"])))
            metrics["dino_i"].append((r.get("dino_i", np.nan), float(h["quality"])))
            metrics["lpips"].append((r.get("lpips", np.nan), float(h["quality"])))
        report["human_correlation"] = {
            k: {"spearman": spearman([x for x, _ in v], [y for _, y in v]),
                "n": len(v)}
            for k, v in metrics.items()
        }
        auto_f = [score_by[(h["item_id"], h["system"])]["failure"] for h in hr
                  if (h["item_id"], h["system"]) in score_by]
        man_f = [h["manual_failure"] for h in hr
                 if (h["item_id"], h["system"]) in score_by]
        report["failure_attribution"] = {
            "kappa": kappa(auto_f, man_f),
            "accuracy": float(np.mean([a == m for a, m in zip(auto_f, man_f)])),
            "n": len(auto_f),
            "confusion": {
                a: dict(Counter(m for aa, m in zip(auto_f, man_f) if aa == a))
                for a in sorted(set(auto_f))
            },
        }

    (out_dir / "stats.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()

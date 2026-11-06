"""Summarise a multi-seed generation-variance study.

The main table generates every item once per system, so the paper can bound judge
noise (a repeat run of the same judge) but not generation noise.  This module reads
the per-item scores of several seeds of one editor and reports the spread of the
causal scores across seeds, per item and in aggregate.

    python -m reasondata.multiseed_report --scores results/analysis_multiseed/scores.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import config
from .bench import read_jsonl
from .stats import spearman


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis_multiseed" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "multiseed.json"))
    args = ap.parse_args()

    rows = read_jsonl(Path(args.scores))
    by_seed: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_seed[r["system"]][r["item_id"]] = r
    seeds = sorted(by_seed)
    if len(seeds) < 2:
        raise SystemExit(f"need at least two seeds, found {seeds}")

    common = set.intersection(*[set(by_seed[s]) for s in seeds])
    common = sorted(common)
    out: dict = {"seeds": seeds, "n_items": len(common), "per_seed": {}}

    for metric in ("tcs", "dps", "nps", "ccs", "strict_success"):
        out["per_seed"][metric] = {}
        for s in seeds:
            vals = [float(by_seed[s][i][metric]) for i in common]
            out["per_seed"][metric][s] = st.mean(vals)

    summary: dict[str, dict] = {}
    for metric in ("tcs", "dps", "nps", "ccs", "strict_success"):
        means = [out["per_seed"][metric][s] for s in seeds]
        # per-item spread: how far a single item moves when only the seed changes
        item_spread = []
        for i in common:
            vals = [float(by_seed[s][i][metric]) for s in seeds]
            item_spread.append(max(vals) - min(vals))
        summary[metric] = {
            "mean": st.mean(means),
            "std_across_seeds": st.pstdev(means) if len(means) > 1 else 0.0,
            "range_across_seeds": max(means) - min(means),
            "mean_item_spread": st.mean(item_spread),
            "p95_item_spread": sorted(item_spread)[int(0.95 * (len(item_spread) - 1))],
        }
    out["summary"] = summary

    # rank agreement of the per-item CCS between seed pairs
    pair_rho = []
    for a in range(len(seeds)):
        for b in range(a + 1, len(seeds)):
            xs = [float(by_seed[seeds[a]][i]["ccs"]) for i in common]
            ys = [float(by_seed[seeds[b]][i]["ccs"]) for i in common]
            pair_rho.append(spearman(xs, ys))
    out["pairwise_spearman_items"] = pair_rho
    out["min_pairwise_spearman"] = min(pair_rho) if pair_rho else None

    dst = Path(args.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print("wrote", dst)


if __name__ == "__main__":
    main()

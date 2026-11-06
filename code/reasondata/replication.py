"""Compare two judges over the same probes, and the two score sets they induce.

The paper's main results come from a hosted API judge (Qwen3-VL-Plus).  This script
measures how much survives when the whole benchmark is re-judged by the open-weight
local model (Qwen3-VL-8B): per-probe verdict agreement, and whether the system
ranking and the reported scores change.

    python -m reasondata.replication \
        --api "results/probes_api_*.jsonl" \
        --local "results/probes_local_full_shard*.jsonl" \
        --api-summary results/analysis/summary.json \
        --local-summary results/analysis_local/summary.json \
        --out results/analysis/replication.json \
        --table paper/tables/replication_table.tex
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import config
from .bench import read_jsonl
from .judge_agreement import load_probes
from .runs import FINAL_SYSTEMS, SYSTEM_LABELS, label_short
from .stats import kappa, spearman


#: summary.json stores display labels; map them back to the canonical system keys
_LABEL_TO_SYSTEM = {SYSTEM_LABELS[s]: s for s in FINAL_SYSTEMS}


def load_summary(path: Path) -> dict[str, dict]:
    if not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text())
    rows = data.get("overall", data) if isinstance(data, dict) else data
    out = {}
    for r in rows:
        key = _LABEL_TO_SYSTEM.get(r.get("system"))
        if key:
            out[key] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=str(config.RESULTS / "probes_api_*.jsonl"))
    ap.add_argument("--local", default=str(config.RESULTS / "probes_local_full_shard*.jsonl"))
    ap.add_argument("--api-summary", default=str(config.RESULTS / "analysis" / "summary.json"))
    ap.add_argument("--local-summary",
                    default=str(config.RESULTS / "analysis_local" / "summary.json"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "replication.json"))
    ap.add_argument("--table", default=str(config.ROOT / "paper" / "tables"
                                           / "replication_table.tex"))
    args = ap.parse_args()

    api, loc = load_probes(args.api), load_probes(args.local)
    common = sorted(set(api) & set(loc))
    if not common:
        raise SystemExit("no shared probes between the two judges")
    a = [api[p]["answer"] for p in common]
    b = [loc[p]["answer"] for p in common]

    by_kind: dict[str, list[int]] = {}
    for p in common:
        k = api[p]["kind"]
        agg = by_kind.setdefault(k, [0, 0])
        agg[0] += api[p]["answer"] == loc[p]["answer"]
        agg[1] += 1

    s_api, s_loc = load_summary(Path(args.api_summary)), load_summary(Path(args.local_summary))
    systems = [s for s in FINAL_SYSTEMS if s in s_api and s in s_loc]
    ccs_api = [s_api[s]["ccs"] for s in systems]
    ccs_loc = [s_loc[s]["ccs"] for s in systems]
    delta = [l - a for a, l in zip(ccs_api, ccs_loc)]
    order_api = sorted(systems, key=lambda s: -s_api[s]["ccs"])
    order_loc = sorted(systems, key=lambda s: -s_loc[s]["ccs"])

    out = {
        "n_shared_probes": len(common),
        "verdict_agreement": float(np.mean([x == y for x, y in zip(a, b)])),
        "verdict_kappa": kappa(a, b),
        "answer_mix_api": {k: float(np.mean([x == k for x in a]))
                           for k in ("yes", "no", "unclear")},
        "answer_mix_local": {k: float(np.mean([x == k for x in b]))
                             for k in ("yes", "no", "unclear")},
        "agreement_by_kind": {k: {"accuracy": v[0] / v[1], "n": v[1]}
                              for k, v in sorted(by_kind.items())},
        "systems": systems,
        "ccs_api": ccs_api,
        "ccs_local": ccs_loc,
        "ccs_delta": delta,
        "ccs_max_abs_delta": float(np.max(np.abs(delta))) if delta else None,
        "ccs_mean_abs_delta": float(np.mean(np.abs(delta))) if delta else None,
        "ccs_spearman": spearman(ccs_api, ccs_loc),
        "ranking_identical": order_api == order_loc,
        "order_api": order_api,
        "order_local": order_loc,
        "strict_api": [s_api[s]["strict_success"] for s in systems],
        "strict_local": [s_loc[s]["strict_success"] for s in systems],
        "best_contract_api": max(s_api[s]["strict_success"] for s in systems) if systems else None,
        "best_contract_local": max(s_loc[s]["strict_success"] for s in systems) if systems else None,
        "oracle_contract_fail_local": (1 - s_loc["qwen_image_edit__oracle"]["strict_success"]
                                       if "qwen_image_edit__oracle" in s_loc else None),
        "tcs_minus_dps_base_local": (s_loc["qwen_image_edit"]["tcs"]
                                     - s_loc["qwen_image_edit"]["dps"]
                                     if "qwen_image_edit" in s_loc else None),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    lines = [
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabular}{lccc}",
        "\\toprule",
             "System & CCS$_{\\mathrm{API}}$ & CCS$_{\\mathrm{loc}}$ & $\\Delta$CCS \\\\",
        "\\midrule",
    ]
    for s, ca, cl in zip(systems, ccs_api, ccs_loc):
        lines.append(f"{label_short(s)} & {ca:.3f} & {cl:.3f} & {cl - ca:+.3f} \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
    ]
    Path(args.table).write_text("\n".join(lines))

    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("ccs_api", "ccs_local", "strict_api", "strict_local")},
                     indent=2, ensure_ascii=False))
    print(f"table -> {args.table}")
    print(f"json  -> {args.out}")


if __name__ == "__main__":
    main()

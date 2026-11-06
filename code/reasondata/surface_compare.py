"""Reasoning items vs their surface controls, paired on the same image.

``surface.py`` builds one surface edit for a reasoning item, on the same photograph and
the same object, with the preserved set copied verbatim.  This module scores both
conditions with the identical region-grounded protocol and reports the gap, which is the
quantity the research proposal asks for ("reasoning-based editing is much harder than
surface editing").

    python -m reasondata.surface_compare \
        --reasoning results/analysis_local_reason/scores.jsonl \
        --surface   results/analysis_surface/scores.jsonl \
        --out results/analysis/surface_compare.json \
        --table paper/tables/surface_table.tex
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .bench import read_jsonl
from .runs import label_short
from .stats import paired_bootstrap

#: system label -> (reasoning run key, surface run key)
PAIRS = {
    "qwen_image_edit": ("qwen_image_edit", "qwen_image_edit__surface"),
    "instructpix2pix": ("instructpix2pix", "instructpix2pix__surface"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reasoning",
                    default=str(config.RESULTS / "analysis_local" / "scores.jsonl"))
    ap.add_argument("--surface",
                    default=str(config.RESULTS / "analysis_surface" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "surface_compare.json"))
    ap.add_argument("--table", default=str(config.ROOT / "paper" / "tables"
                                           / "surface_table.tex"))
    args = ap.parse_args()

    def idx(path):
        return {(r["item_id"], r["system"]): r for r in read_jsonl(Path(path))}

    reason, surf = idx(args.reasoning), idx(args.surface)
    pairs: dict[str, dict] = {}
    for name, (r_key, s_key) in PAIRS.items():
        # the surface item id is "<reasoning item id>_surface"
        shared = sorted({(i, s) for (i, s) in surf if s == s_key})
        rows = []
        for item_id, _ in shared:
            parent = item_id[: -len("_surface")]
            r = reason.get((parent, r_key))
            s = surf.get((item_id, s_key))
            if r and s:
                rows.append((r, s))
        if not rows:
            continue
        R = [r for r, _ in rows]
        S = [s for _, s in rows]
        delta, delta_lo, delta_hi, delta_p = paired_bootstrap(
            [s["ccs"] for s in S], [r["ccs"] for r in R]
        )
        discordant_right = sum((not r["strict_success"]) and s["strict_success"]
                               for r, s in rows)
        discordant_left = sum(r["strict_success"] and (not s["strict_success"])
                              for r, s in rows)
        discordant = discordant_right + discordant_left
        if discordant:
            tail = sum(math.comb(discordant, j)
                       for j in range(min(discordant_right, discordant_left) + 1))
            contract_p = min(1.0, 2 * tail / (2 ** discordant))
        else:
            contract_p = 1.0
        pairs[name] = {
            "n": len(rows),
            "reasoning": {k: float(np.mean([r[k] for r in R]))
                          for k in ("tcs", "dps", "nps", "ccs")},
            "surface": {k: float(np.mean([s[k] for s in S]))
                        for k in ("tcs", "dps", "nps", "ccs")},
            "delta_ccs": delta, "delta_ci": [delta_lo, delta_hi],
            "delta_p": delta_p, "contract_p": contract_p,
            "win_rate": float(np.mean([1.0 if s["ccs"] > r["ccs"] + 1e-9 else
                                       0.5 if abs(s["ccs"] - r["ccs"]) <= 1e-9 else 0.0
                                       for r, s in rows])),
            "contract_reasoning": float(np.mean([r["strict_success"] for r in R])),
            "contract_surface": float(np.mean([s["strict_success"] for s in S])),
            "difficulty_reasoning": dict(Counter(r["difficulty"] for r in R)),
        }
    if not pairs:
        raise SystemExit("no paired reasoning/surface scores found")

    pooled = list(pairs.values())
    out = {"pairs": pairs, "pooled": {
        "n": sum(p["n"] for p in pooled),
        "delta_ccs": float(np.mean([p["delta_ccs"] for p in pooled])),
        "win_rate": float(np.mean([p["win_rate"] for p in pooled])),
        "reasoning_ccs": float(np.mean([p["reasoning"]["ccs"] for p in pooled])),
        "surface_ccs": float(np.mean([p["surface"]["ccs"] for p in pooled])),
        "reasoning_contract": float(np.mean([p["contract_reasoning"] for p in pooled])),
        "surface_contract": float(np.mean([p["contract_surface"] for p in pooled])),
        "components": {k: {"reasoning": float(np.mean([p["reasoning"][k] for p in pooled])),
                           "surface": float(np.mean([p["surface"][k] for p in pooled]))}
                       for k in ("tcs", "dps", "nps")},
    }}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    lines = [
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{2pt}",
        "\\begin{tabular}{lccccc}",
        "\\toprule",
        "System & CCS$_s$ & CCS$_r$ & $\\Delta$ & Cont.$_s$ (\\%) & Cont.$_r$ (\\%) \\\\",
        "\\midrule",
    ]
    for name, p in pairs.items():
        lines.append(
            f"{label_short(name)} & {p['surface']['ccs']:.3f} & {p['reasoning']['ccs']:.3f} "
            f"& {p['delta_ccs']:+.3f} & {100*p['contract_surface']:.0f} & "
            f"{100*p['contract_reasoning']:.0f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    Path(args.table).write_text("\n".join(lines))

    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"table -> {args.table}")


if __name__ == "__main__":
    main()

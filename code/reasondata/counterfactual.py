"""The counterfactual control: does the contract reject a causally invalid edit?

Every benchmark item carries a *causally invalid counterfactual*: an instruction that
is plausible as a phrase but contradicts an edge of the annotated graph ("turn the
lamp on but keep the room dim").  We generate those edits with the same editors,
score them against the **original** contract, and ask whether the protocol separates
them from the editors' own attempts at the real instruction.

The comparison is paired and within-judge, so it is run under the local open-weight
judge whose positive-side scores are already in ``results/analysis_local``.

    python -m reasondata.counterfactual \
        --positive results/analysis_local/scores.jsonl \
        --cf        results/analysis_cf/scores.jsonl \
        --out results/analysis/counterfactual.json \
        --table paper/tables/counterfactual_table.tex
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .bench import read_jsonl
from .runs import label_short

#: system key -> (key of its positive run, key of its counterfactual run)
PAIRS = {
    "qwen_image_edit": ("qwen_image_edit", "qwen_image_edit__cf"),
    "instructpix2pix": ("instructpix2pix", "instructpix2pix__cf"),
}

FAILS = ("OK", "IUE", "RPE", "GE", "PQE", "CI")


def index(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["item_id"], r["system"]): r for r in rows}


def mean(rows: list[dict], key: str) -> float:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return float(np.mean(vals)) if vals else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--positive", default=str(config.RESULTS / "analysis_local" / "scores.jsonl"))
    ap.add_argument("--cf", default=str(config.RESULTS / "analysis_cf" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "counterfactual.json"))
    ap.add_argument("--table", default=str(config.ROOT / "paper" / "tables"
                                           / "counterfactual_table.tex"))
    args = ap.parse_args()

    pos, cf = index(read_jsonl(Path(args.positive))), index(read_jsonl(Path(args.cf)))
    out: dict = {"pairs": {}}

    for name, (pos_sys, cf_sys) in PAIRS.items():
        shared = sorted({i for (i, s) in pos if s == pos_sys}
                        & {i for (i, s) in cf if s == cf_sys})
        if not shared:
            continue
        P = [pos[(i, pos_sys)] for i in shared]
        C = [cf[(i, cf_sys)] for i in shared]
        d = [p["ccs"] - c["ccs"] for p, c in zip(P, C)]
        wins = float(np.mean([1.0 if x > 1e-9 else 0.5 if abs(x) <= 1e-9 else 0.0
                              for x in d]))
        # signature of surface compliance: the intervention happened, the required
        # consequences did not follow
        surface = float(np.mean([1.0 if (c["tcs"] >= 1.0 and c["dps"] < 0.5) else 0.0
                                 for c in C]))
        # the informative subset: items on which the editor got the *real*
        # instruction right, so a low counterfactual score cannot be blamed on a
        # generally failing editor
        good = [p["item_id"] for p in P if p["strict_success"]]
        C_good = [cf[(i, cf_sys)] for i in good if (i, cf_sys) in cf]
        # consequences conditional on the intervention having landed
        p_tcs = [r for r in P if r["tcs"] >= 1.0]
        c_tcs = [r for r in C if r["tcs"] >= 1.0]
        out["pairs"][name] = {
            "n": len(shared),
            "system_positive": pos_sys,
            "system_cf": cf_sys,
            "ccs_positive": mean(P, "ccs"),
            "ccs_cf": mean(C, "ccs"),
            "ccs_delta": float(np.mean(d)),
            "discrimination": wins,
            "tcs_positive": mean(P, "tcs"), "tcs_cf": mean(C, "tcs"),
            "dps_positive": mean(P, "dps"), "dps_cf": mean(C, "dps"),
            "nps_positive": mean(P, "nps"), "nps_cf": mean(C, "nps"),
            "contract_positive": float(np.mean([r["strict_success"] for r in P])),
            "contract_cf": float(np.mean([r["strict_success"] for r in C])),
            "surface_compliance": surface,
            "n_pos_success": len(C_good),
            "ccs_cf_given_pos_success": mean(C_good, "ccs") if C_good else None,
            "cf_fail_given_pos_success": (float(np.mean([not r["strict_success"]
                                                         for r in C_good]))
                                          if C_good else None),
            "n_tcs_pos": len(p_tcs), "n_tcs_cf": len(c_tcs),
            "dps_given_tcs_positive": mean(p_tcs, "dps") if p_tcs else None,
            "dps_given_tcs_cf": mean(c_tcs, "dps") if c_tcs else None,
            "failure_cf": {k: float(np.mean([r["failure"] == k for r in C])) for k in FAILS},
            "failure_positive": {k: float(np.mean([r["failure"] == k for r in P]))
                                 for k in FAILS},
        }

    if not out["pairs"]:
        raise SystemExit("no counterfactual scores found; generate and judge the cf runs first")

    # pooled over systems
    pooled = list(out["pairs"].values())
    sub = [p for p in pooled if p["n_pos_success"]]
    subs = [p for p in pooled if p["n_tcs_cf"]]
    out["pooled"] = {
        "n": sum(p["n"] for p in pooled),
        "ccs_delta": float(np.mean([p["ccs_delta"] for p in pooled])),
        "discrimination": float(np.mean([p["discrimination"] for p in pooled])),
        "surface_compliance": float(np.mean([p["surface_compliance"] for p in pooled])),
        "ci_cf": float(np.mean([p["failure_cf"]["CI"] for p in pooled])),
        "ci_positive": float(np.mean([p["failure_positive"]["CI"] for p in pooled])),
        "rpe_cf": float(np.mean([p["failure_cf"]["RPE"] for p in pooled])),
        "n_pos_success": sum(p["n_pos_success"] for p in sub),
        "ccs_cf_given_pos_success": (float(np.mean([p["ccs_cf_given_pos_success"]
                                                    for p in sub])) if sub else None),
        "cf_fail_given_pos_success": (float(np.mean([p["cf_fail_given_pos_success"]
                                                     for p in sub])) if sub else None),
        "dps_given_tcs_cf": (float(np.mean([p["dps_given_tcs_cf"] for p in subs]))
                             if subs else None),
        "dps_given_tcs_positive": (float(np.mean([p["dps_given_tcs_positive"]
                                                  for p in subs])) if subs else None),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    lines = [
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{3.5pt}",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
           "System & CCS$_{\\mathrm{instr}}$ & CCS$_{\\mathrm{cf}}$ & $\\Delta$ & Sep. (\\%) \\\\",
        "\\midrule",
    ]
    for name, p in out["pairs"].items():
        lines.append(f"{label_short(name)} & {p['ccs_positive']:.3f} & {p['ccs_cf']:.3f} & "
                     f"{p['ccs_delta']:+.3f} & {100*p['discrimination']:.0f} \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
    ]
    Path(args.table).write_text("\n".join(lines))

    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"table -> {args.table}")


if __name__ == "__main__":
    main()

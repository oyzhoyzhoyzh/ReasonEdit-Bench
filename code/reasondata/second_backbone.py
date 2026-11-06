"""Second-backbone control for the separation claim (Review Report M1).

Compares, on the *same* 108-item stratified subset, the four conditions
(base, +CoT, +Oracle-SCM, +CausalScaffold) on two backbones:

* Qwen-Image-Edit --- the backbone used throughout the paper;
* FLUX.1-Kontext   --- the only other strong editor whose weights run on this
  machine, generated for this control (``results/flux_kontext_2nd/``).

This is a control, not a tenth entry in the main table: the main comparison
still uses the full 324-item benchmark.

    python -m reasondata.second_backbone
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config
from .aggregate import build_table, summarize

QWEN = {
    "base": "qwen_image_edit",
    "cot": "qwen_image_edit__cot",
    "oracle": "qwen_image_edit__oracle",
    "scaffold": "qwen_image_edit__scaffold_full",
}
FLUX = {
    "base": "flux_kontext_2nd",
    "cot": "flux_kontext_2nd__cot",
    "oracle": "flux_kontext_2nd__oracle",
    "scaffold": "flux_kontext_2nd__scaffold_full",
}
ORDER = ["base", "cot", "oracle", "scaffold"]
LABEL = {"base": "base", "cot": "+CoT", "oracle": "+Oracle-SCM",
         "scaffold": "+CausalScaffold"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=str(config.RESULTS / "pairs108.txt"))
    ap.add_argument("--new-probes", default=str(config.RESULTS / "probes_api_2nd.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "second_backbone.json"))
    ap.add_argument("--table", default=str(config.ROOT / "paper" / "tables"
                                           / "second_backbone_table.tex"))
    args = ap.parse_args()

    subset = set(Path(args.pairs).read_text().strip().split(","))
    systems = list(QWEN.values()) + list(FLUX.values())

    rows: list[dict] = []
    # the paper's own runs (API judge); note that a pattern without a wildcard is
    # interpreted as a literal path, so pass absolute paths here
    own = ("probes_api_all.jsonl", "probes_api_new.jsonl", "probes_api_oracle.jsonl",
           "probes_api_scaffold.jsonl", "probes_api_2nd_scaffold.jsonl")
    for name in own:
        path = Path(config.RESULTS) / name
        if path.exists():
            rows += build_table(probe_pattern=str(path), systems=systems)
    # the second-backbone runs
    newp = Path(args.new_probes)
    if newp.exists():
        rows += build_table(probe_pattern=str(newp), systems=systems)
    # the same (item, system) can appear in more than one probe file; the paper's
    # own aggregation keeps the first occurrence, so do the same here
    seen: set[tuple[str, str]] = set()
    deduped = []
    for r in rows:
        key = (r["item_id"], r["system"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    rows = deduped
    rows = [r for r in rows if r["item_id"] in subset]

    summary = {(r["system"],): r for r in summarize(rows)}
    out = {"n_items": len(subset), "conditions": []}
    for backbone, table in (("Qwen-Image-Edit", QWEN), ("FLUX.1-Kontext", FLUX)):
        for key in ORDER:
            d = summary.get((table[key],))
            if not d:
                continue
            out["conditions"].append({
                "backbone": backbone, "condition": LABEL[key], "system": table[key],
                "n": d["n"], "tcs": d["tcs"], "dps": d["dps"], "nps": d["nps"],
                "ccs": d["ccs"], "contract": d["strict_success"],
            })
    Path(args.out).write_text(json.dumps(out, indent=2))

    lines = ["\\scriptsize", "\\setlength{\\tabcolsep}{2.5pt}",
             "\\begin{tabular}{@{}llccccc@{}}", "\\toprule",
             "Backbone & Condition & TCS & DPS & NPS & CCS & Contract (\\%) \\\\", "\\midrule"]
    for row in out["conditions"]:
        lines.append(f"{row['backbone']} & {row['condition']} & {row['tcs']:.3f} & "
                     f"{row['dps']:.3f} & {row['nps']:.3f} & {row['ccs']:.3f} & "
                     f"{100*row['contract']:.1f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    Path(args.table).parent.mkdir(parents=True, exist_ok=True)
    Path(args.table).write_text("\n".join(lines))
    print(json.dumps(out, indent=2))
    print("wrote", args.out, "and", args.table)


if __name__ == "__main__":
    main()

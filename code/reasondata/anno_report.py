"""Aggregate the human annotations and report the three kappas (review item B5).

    python -m reasondata.anno_report                 # write json + md + tex
    python -m reasondata.anno_report --print         # also print the markdown
"""

from __future__ import annotations

import argparse
import json

from . import anno, config


def main() -> None:
    ap = argparse.ArgumentParser(description="B5 human-annotation agreement report")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--out", default=None, help="output directory for report files")
    ap.add_argument("--tables-dir", default=str(config.ROOT / "paper" / "tables"))
    ap.add_argument("--print", action="store_true", help="print the markdown report")
    ap.add_argument("--json", action="store_true", help="print the report json")
    args = ap.parse_args()

    report = anno.compute_report(args.data_dir)
    paths = anno.write_report_files(report, args.out, args.tables_dir)

    p = report["primary"]
    cov = report["coverage"]
    print(f"items {report['protocol']['n_items']} x raters {report['protocol']['raters_per_item']}"
          f" -> {cov['item_annotations_submitted']}/{cov['item_annotations_expected']} submissions"
          f" ({cov['items_with_full_k_raters']} items with the full rater set)")
    for name in ("kappa_scm", "kappa_chain", "kappa_region"):
        val = p[name]
        print(f"  {name:14s} = {'n/a' if val is None else f'{val:.3f}'}  ({anno.kappa_band(val)})")
    for name in ("kappa_scm_verdict", "kappa_chain_verdict", "kappa_region_iou"):
        val = p[name]
        print(f"  {name:14s} = {'n/a' if val is None else f'{val:.3f}'}  ({anno.kappa_band(val)})")
    print(f"region IoU: mean-to-reference {report['region_iou']['mean_iou_to_reference']}, "
          f"mean pairwise {report['region_iou']['mean_pairwise_iou']}, "
          f"accept rate {report['region_iou']['accept_rate']}")
    for key, path in paths.items():
        print(f"  wrote {key}: {path}")
    if args.print:
        print()
        print(anno.report_markdown(report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

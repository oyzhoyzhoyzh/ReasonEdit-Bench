"""Second pass of the CausalScaffold baseline.

The scaffold verifies the first-pass edit with the same region-grounded probes
used for evaluation, then asks the editor to redo only the items whose causal
contract was violated -- naming the effect that did not appear and the fact that
was destroyed.  This is a training-free reasoning-and-revision loop.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from . import config
from .aggregate import score_pair
from .bench import load_bench, read_jsonl, write_jsonl
from .runs import outputs_of


def unmet(item: dict, rec: dict, probes: dict) -> tuple[list[str], list[str]]:
    effects = [p for p in probes.get("dps", []) if p["value"] < 1.0]
    preserved = [p for p in probes.get("nps", []) if p["value"] < 1.0]
    miss_effect = [p["question"] for p in effects]
    broke = [p["question"] for p in preserved]
    if rec.get("tcs", 1.0) < 1.0:
        miss_effect.insert(0, probes["tcs"][0]["question"])
    return miss_effect, broke


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--source-run", default=str(config.RESULTS / "qwen_image_edit" / "cot"))
    ap.add_argument("--probes", default="probes_api*.jsonl",
                    help="glob (relative to results/) of probe jsonl files")
    ap.add_argument("--system", default="qwen_image_edit__cot")
    ap.add_argument("--min-dps", type=float, default=1.0)
    ap.add_argument("--out", default=str(config.RESULTS / "qwen_image_edit" / "scaffold_requests.jsonl"))
    args = ap.parse_args()

    items = {it["id"]: it for it in load_bench(args.bench)}
    probe_files = sorted(config.RESULTS.glob(args.probes))
    per = defaultdict(lambda: defaultdict(list))
    seen = set()
    for path in probe_files:
        for rec in read_jsonl(path):
            if rec["system"] == args.system and rec["pid"] not in seen:
                seen.add(rec["pid"])
                per[rec["item_id"]][rec["kind"]].append(rec)

    requests = []
    stats = defaultdict(int)
    for item_id, kinds in per.items():
        item = items.get(item_id)
        if not item or "dps" not in kinds or "tcs" not in kinds:
            continue
        rec = score_pair(item, kinds, None)
        miss_effect, broke = unmet(item, rec, kinds)
        stats["total"] += 1
        if not miss_effect and not broke:
            continue
        parts = [f"Edit this photograph: {item['instruction']}."]
        if miss_effect:
            parts.append("A previous attempt did not achieve this: "
                         + "; ".join(m[:120] for m in miss_effect[:3])
                         + ". Make sure it is clearly visible in the result.")
        if broke:
            parts.append("The previous attempt also altered things that must stay as they "
                         "are: " + "; ".join(m[:120] for m in broke[:2]) + ".")
        prompt = " ".join(parts)
        requests.append({"item_id": item_id, "prompt": prompt,
                         "missed_effects": miss_effect, "broken_preserved": broke})
        stats["repair"] += 1

    write_jsonl(Path(args.out), requests)
    print(json.dumps(dict(stats), ensure_ascii=False))
    print(f"wrote {len(requests)} repair requests -> {args.out}")


if __name__ == "__main__":
    main()

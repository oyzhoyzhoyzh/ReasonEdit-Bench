"""Run one editing back end over the benchmark.

Usage::

    python -m reasondata.run_edit --model qwen_image_edit --variant base --gpu 0 \
        --shard 0/2 --out results/qwen_image_edit/base

Outputs are written per item (``<item_id>.png``) plus a manifest JSONL, and the
script is resumable: existing images are skipped.
"""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench, read_jsonl, write_jsonl
from .editor import build_editor
from .taxonomy import TASK_TYPES


def prompt_for(item: dict, variant: str, plan: dict | None = None) -> str:
    """Compose the instruction string handed to the editor."""
    if variant == "cf":
        # counterfactual negative control: the stored instruction that is plausible as
        # a phrase but contradicts an edge of the annotated causal graph.  The edit is
        # then scored against the *original* contract, so a model that follows the
        # words honours the surface request and violates the causal one.
        cf = (item.get("counterfactual") or {}).get("instruction")
        return cf or item["instruction"]

    if plan and plan.get("prompt"):
        return plan["prompt"]
    ins = item["instruction"]
    if variant == "base":
        return ins

    if variant == "oracle":
        # upper bound: the ground-truth intervention plus its required effects
        iv = item["scm"]["intervention"]
        eff = "; ".join(e["statement"] or e["probe"] for e in item["effects"])
        keep = "; ".join(p["statement"] or p["probe"] for p in item["preserved"][:3])
        return (f"{ins}. The result must show: {eff}. "
                f"Keep unchanged: {keep}.")

    if variant in ("cot", "scaffold") and plan:
        steps = " ".join(s.get("text", "") for s in plan.get("plan", []) if s.get("text"))
        keep = "; ".join(plan.get("must_preserve", [])[:3])
        extra = f" Keep unchanged: {keep}." if keep else ""
        return f"{ins}. Reasoning: {steps}.{extra}".strip()

    return ins


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--variant", default="base")
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--out", default=None)
    ap.add_argument("--plan", default=None, help="plan JSONL for cot/scaffold variants")
    ap.add_argument("--pairs", default=None, help="only run these item ids (comma separated)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--bf16", action="store_true",
                    help="load the checkpoint in bf16 instead of 4-bit (needed on "
                         "accelerators without a working bitsandbytes backend)")
    ap.add_argument("--device-map", default=None,
                    help="optional diffusers/accelerate device map, e.g. balanced")
    ap.add_argument("--cpu-offload", action="store_true",
                    help="move pipeline components to the GPU only while in use")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else (config.RESULTS / args.model / args.variant)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"

    items = load_bench(args.bench)
    k, n = (int(x) for x in args.shard.split("/"))
    items = [it for i, it in enumerate(items) if i % n == k]
    if args.pairs:
        wanted = set(args.pairs.split(","))
        items = [it for it in items if it["id"] in wanted]
    if args.limit:
        items = items[: args.limit]

    plans = {}
    if args.plan and Path(args.plan).exists():
        plans = {r["item_id"]: r for r in read_jsonl(Path(args.plan))}

    done = set()
    if manifest_path.exists():
        for r in read_jsonl(manifest_path):
            if r.get("status") == "ok":
                done.add(r["item_id"])
    todo = [it for it in items if it["id"] not in done]
    print(f"[{args.model}/{args.variant}] shard {args.shard}: {len(todo)} to run "
          f"({len(done)} cached)", flush=True)
    if not todo:
        return

    editor_kwargs = {"load_in_4bit": False} if args.bf16 else {}
    if args.device_map:
        editor_kwargs["device_map"] = args.device_map
    if args.cpu_offload:
        editor_kwargs["cpu_offload"] = True
    editor = build_editor(args.model, device=f"cuda:{args.gpu}", **editor_kwargs)
    records = []
    for i, it in enumerate(todo, 1):
        src = Image.open(config.BENCH_IMAGES / f"{it['image_id']}.jpg").convert("RGB")
        prompt = prompt_for(it, args.variant, plans.get(it["id"]))
        t0 = time.time()
        rec = {
            "item_id": it["id"], "model": args.model, "variant": args.variant,
            "image_id": it["image_id"], "prompt": prompt, "seed": args.seed,
            "type": it["type"], "domain": it["domain"],
        }
        try:
            out = editor.edit(src, prompt, seed=args.seed)
            path = out_dir / f"{it['id']}.png"
            out.save(path)
            rec.update(status="ok", output=str(path), latency=time.time() - t0)
        except Exception as exc:  # noqa: BLE001
            rec.update(status="error", error=f"{exc}", traceback=traceback.format_exc()[-2000:],
                       latency=time.time() - t0)
        records.append(rec)
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} last={rec.get('latency', 0):.1f}s "
                  f"status={rec['status']}", flush=True)
            write_jsonl(manifest_path, read_jsonl(manifest_path) + records
                        if manifest_path.exists() else records)
            records = []
    if records:
        prev = read_jsonl(manifest_path) if manifest_path.exists() else []
        write_jsonl(manifest_path, prev + records)
    print(f"[{args.model}/{args.variant}] finished -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()

"""Load one editor and generate a balanced shard of several Qwen conditions.

This is used for the main-backbone multi-seed study.  Unlike invoking
``run_edit`` once per condition, each process loads the 54 GB BF16 checkpoint
once and then iterates over all condition/seed tasks assigned to its shard.
Manifests are written per GPU to avoid concurrent writers to one file.
"""

from __future__ import annotations

import argparse
import time
import traceback
from collections import defaultdict
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench, read_jsonl, write_jsonl
from .editor import build_editor
from .run_edit import prompt_for


def task_dirs(root: Path, seeds: list[int], variants: list[str]):
    for seed in seeds:
        for variant in variants:
            yield seed, variant, root / f"qwen_multiseed_s{seed}" / variant


def merge_manifests(root: Path, seeds: list[int], variants: list[str]) -> None:
    for seed, variant, out_dir in task_dirs(root, seeds, variants):
        by_item = {}
        for path in sorted(out_dir.glob("manifest*.jsonl")):
            for rec in read_jsonl(path):
                item_id = rec.get("item_id")
                if not item_id or rec.get("status") != "ok":
                    continue
                output = Path(rec.get("output", ""))
                if not output.exists():
                    continue
                by_item[item_id] = rec
        if by_item:
            write_jsonl(out_dir / "manifest.jsonl",
                        [by_item[k] for k in sorted(by_item)])
            print(f"merged {len(by_item):3d} -> {out_dir}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--root", default=str(config.RESULTS))
    ap.add_argument("--seeds", default="20260924,20260925,20260926")
    ap.add_argument("--variants", default="base,cot,oracle")
    ap.add_argument("--pairs-file", default=None)
    ap.add_argument("--plan", default=str(config.RESULTS / "plans_all.jsonl"))
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s]
    variants = [v for v in args.variants.split(",") if v]
    root = Path(args.root)
    if args.merge:
        merge_manifests(root, seeds, variants)
        return

    k, n = (int(x) for x in args.shard.split("/"))
    pairs = set()
    if args.pairs_file:
        pairs = {x.strip() for x in Path(args.pairs_file).read_text().split(",")
                 if x.strip()}
    items = [it for it in load_bench() if not pairs or it["id"] in pairs]
    shard_items = [it for i, it in enumerate(items) if i % n == k]
    default_plans = {}
    if Path(args.plan).exists():
        default_plans = {r["item_id"]: r for r in read_jsonl(Path(args.plan))}

    editor = build_editor("qwen_image_edit", device=f"cuda:{args.gpu}",
                          load_in_4bit=False)
    for seed, variant, out_dir in task_dirs(root, seeds, variants):
        if variant == "scaffold":
            request_path = root / f"qwen_multiseed_s{seed}" / "scaffold_requests.jsonl"
            plans = {r["item_id"]: r for r in read_jsonl(request_path)}
        else:
            plans = default_plans
        # CausalScaffold is defined as "CoT output, replaced by a repair only when
        # the verifier requested one".  Items without a request must fall back to
        # the first CoT output during assembly; they must not be regenerated with
        # the base instruction here.
        task_items = (
            [it for it in shard_items if it["id"] in plans]
            if variant == "scaffold" else shard_items
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / f"manifest_shard_{k}.jsonl"
        previous = read_jsonl(manifest_path) if manifest_path.exists() else []
        by_item = {r["item_id"]: r for r in previous
                   if r.get("status") == "ok"}
        todo = [it for it in task_items if not (out_dir / f"{it['id']}.png").exists()]
        print(f"[gpu {args.gpu}] seed={seed} variant={variant}: "
              f"{len(todo)} missing / {len(task_items)} shard items", flush=True)
        for index, item in enumerate(todo, 1):
            src = Image.open(config.BENCH_IMAGES / f"{item['image_id']}.jpg").convert("RGB")
            prompt = prompt_for(item, variant, plans.get(item["id"]))
            output = out_dir / f"{item['id']}.png"
            rec = {
                "item_id": item["id"], "model": "qwen_image_edit",
                "variant": variant, "image_id": item["image_id"],
                "prompt": prompt, "seed": seed, "type": item["type"],
                "domain": item["domain"], "shard": f"{k}/{n}",
            }
            started = time.time()
            try:
                image = editor.edit(src, prompt, seed=seed)
                image.save(output)
                rec.update(status="ok", output=str(output),
                           latency=time.time() - started)
            except Exception as exc:  # noqa: BLE001
                rec.update(status="error", error=str(exc),
                           traceback=traceback.format_exc()[-2000:],
                           latency=time.time() - started)
            by_item[item["id"]] = rec
            write_jsonl(manifest_path, [by_item[x] for x in sorted(by_item)])
            print(f"  {index}/{len(todo)} {item['id']} status={rec['status']} "
                  f"{rec['latency']:.1f}s", flush=True)

        # Also materialise manifest entries for images produced before this
        # balanced-shard run.  Their exact latency is intentionally omitted.
        for item in task_items:
            output = out_dir / f"{item['id']}.png"
            if output.exists() and item["id"] not in by_item:
                by_item[item["id"]] = {
                    "item_id": item["id"], "model": "qwen_image_edit",
                    "variant": variant, "image_id": item["image_id"],
                    "prompt": prompt_for(item, variant, plans.get(item["id"])),
                    "seed": seed, "type": item["type"],
                    "domain": item["domain"], "shard": f"{k}/{n}",
                    "status": "ok", "output": str(output),
                    "latency": None,
                }
        write_jsonl(manifest_path, [by_item[x] for x in sorted(by_item)])
    print(f"[gpu {args.gpu}] shard complete", flush=True)


if __name__ == "__main__":
    main()

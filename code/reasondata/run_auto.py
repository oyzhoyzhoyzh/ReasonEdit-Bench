"""Compute reference-based metrics (CLIPScore / CLIP-I / DINO-I / LPIPS)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from . import config
from .auto_metrics import AutoMetrics
from .bench import load_bench, read_jsonl
from .runs import list_runs, outputs_of


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--out", default=None)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    out_path = Path(args.out or (config.RESULTS / "auto_metrics.jsonl"))
    done = {(r["item_id"], r["system"]): r for r in read_jsonl(out_path)} if out_path.exists() else {}
    items = {it["id"]: it for it in load_bench(args.bench)}
    am = AutoMetrics(device=f"cuda:{args.gpu}")

    fh = out_path.open("a")
    for system, run_dir in sorted(list_runs().items()):
        outputs = outputs_of(run_dir)
        todo = [(i, p) for i, p in sorted(outputs.items())
                if (i, system) not in done and i in items]
        for i in range(0, len(todo), args.batch):
            chunk = todo[i : i + args.batch]
            srcs = [Image.open(config.BENCH_IMAGES / f"{items[j]['image_id']}.jpg").convert("RGB")
                    for j, _ in chunk]
            edts = [Image.open(p).convert("RGB") for _, p in chunk]
            ins = [items[j]["instruction"] for j, _ in chunk]
            res = am.all_metrics(srcs, edts, ins, batch=args.batch)
            for (j, p), m in zip(chunk, res):
                fh.write(json.dumps({"item_id": j, "system": system, **m}) + "\n")
            fh.flush()
        print(f"{system}: {len(todo)} processed", flush=True)
    fh.close()
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()

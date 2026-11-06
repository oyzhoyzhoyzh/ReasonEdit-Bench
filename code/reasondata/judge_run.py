"""Run region-grounded probes over every generated image."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench
from .probe import (Probe, PROBE_SYSTEM, build_probes, judge_probe, probe_inputs,
                    read_probe_jsonl, record_from_answer)
from .runs import list_runs, outputs_of
from .vlm import LocalVLM


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--runs", default=None, help="comma separated system names (default: all)")
    ap.add_argument("--backend", default="local", choices=["local", "dashscope"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-image-side", type=int, default=768)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample-per-system", type=int, default=0,
                    help="judge a deterministic subset of items per system")
    ap.add_argument("--workers", type=int, default=8,
                    help="concurrent requests for the API backend")
    ap.add_argument("--batch-size", type=int, default=1,
                    help="local backend only: probes judged in one forward pass "
                         "(probes of the same item are grouped together)")
    args = ap.parse_args()

    out_path = Path(args.out or (config.RESULTS / f"probes_{args.backend}_shard"
                                 f"{args.shard.replace('/', 'of')}.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cache = read_probe_jsonl(out_path)

    items = {it["id"]: it for it in load_bench(args.bench)}
    runs = list_runs()
    if args.runs:
        keep = set(args.runs.split(","))
        runs = {k: v for k, v in runs.items() if k in keep}
    print(f"systems: {sorted(runs)}", flush=True)

    # build the work list, then shard it
    work: list[tuple[Probe, Path, Path]] = []
    groups_all: list[list[tuple[Probe, Path, Path]]] = []
    for system, run_dir in sorted(runs.items()):
        outputs = outputs_of(run_dir)
        ids = sorted(outputs.items())
        if args.sample_per_system:
            step = max(1, len(ids) // args.sample_per_system)
            ids = ids[::step][: args.sample_per_system]
        for item_id, out_img in ids:
            item = items.get(item_id)
            if not item:
                continue
            src = config.BENCH_IMAGES / f"{item['image_id']}.jpg"
            group = []
            for probe in build_probes(item, system, out_img):
                if probe.pid in cache:
                    continue
                group.append((probe, src, out_img))
            work.extend(group)
            if group:
                groups_all.append(group)
    k, n = (int(x) for x in args.shard.split("/"))
    if args.batch_size > 1:
        # shard whole item groups: a group is judged in one forward pass, so it must
        # not be split across two processes
        groups = [g for i, g in enumerate(groups_all) if i % n == k]
        work = [w for g in groups for w in g]
    else:
        work = [w for i, w in enumerate(work) if i % n == k]
        groups = []
    if args.limit:
        work = work[: args.limit]
        if groups:
            limited, n_left = [], args.limit
            for g in groups:
                if n_left <= 0:
                    break
                take = g[:n_left]
                limited.append(take)
                n_left -= len(take)
            groups = limited
    print(f"probes to run: {len(work)}", flush=True)
    if not work:
        return

    if args.backend == "local":
        client = LocalVLM.get(args.model or config.MODELS["qwen3vl8b"], device=f"cuda:{args.gpu}")
        run_seq = None
    else:
        from .vlm import DashScopeClient
        client = DashScopeClient(model=args.model or config.ANNOT_MODEL)
        from concurrent.futures import ThreadPoolExecutor

        run_seq = ThreadPoolExecutor(max_workers=args.workers)

    fh = out_path.open("a")
    t0 = time.time()

    def do_one(w):
        probe, src_p, out_p = w
        try:
            src = Image.open(src_p).convert("RGB")
            edt = Image.open(out_p).convert("RGB")
            return judge_probe(client, probe, src, edt, max_image_side=args.max_image_side)
        except Exception as exc:  # noqa: BLE001
            return {"pid": probe.pid, "item_id": probe.item_id, "system": probe.system,
                    "kind": probe.kind, "question": probe.question, "answer": "unclear",
                    "value": 0.5, "evidence": f"error: {exc}", "region": probe.region,
                    "ordinal": probe.ordinal, "latency": 0.0}

    if run_seq is not None:
        futs = [run_seq.submit(do_one, w) for w in work]
        for i, fut in enumerate(futs, 1):
            fh.write(json.dumps(fut.result(), ensure_ascii=False) + "\n")
            if i % 200 == 0:
                fh.flush()
                print(f"  {i}/{len(work)}", flush=True)
        run_seq.shutdown()
        fh.close()
        print(f"done -> {out_path}", flush=True)
        return

    if args.batch_size > 1:
        chunks: list[list] = []
        for g in groups:
            for i in range(0, len(g), args.batch_size):
                chunks.append(g[i:i + args.batch_size])
        done = 0
        for chunk in chunks:
            try:
                prompts, canvases = [], []
                for probe, src_p, out_p in chunk:
                    src = Image.open(src_p).convert("RGB")
                    edt = Image.open(out_p).convert("RGB")
                    prompt, canvas = probe_inputs(probe, src, edt,
                                                  max_image_side=args.max_image_side)
                    prompts.append(prompt)
                    canvases.append([canvas])
                resps = client.chat_batch(prompts, canvases, system=PROBE_SYSTEM,
                                          temperature=0.0, max_tokens=2000)
                recs = [record_from_answer(p, r.text, r.latency)
                        for (p, _, _), r in zip(chunk, resps)]
            except Exception as exc:  # noqa: BLE001
                print(f"  batch failed ({exc}); falling back to one-by-one", flush=True)
                recs = [do_one(w) for w in chunk]
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                done += 1
            if done % 50 < len(chunk) or done == len(work):
                fh.flush()
                rate = done / max(1e-6, time.time() - t0)
                eta = (len(work) - done) / max(rate, 1e-6) / 60
                print(f"  {done}/{len(work)}  {rate:.2f} probes/s  eta {eta:.1f} min",
                      flush=True)
        fh.close()
        print(f"done -> {out_path}", flush=True)
        return

    for i, w in enumerate(work, 1):
        rec = do_one(w)
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if i % 25 == 0:
            fh.flush()
            rate = i / max(1e-6, time.time() - t0)
            eta = (len(work) - i) / max(rate, 1e-6) / 60
            print(f"  {i}/{len(work)}  {rate:.2f} probes/s  eta {eta:.1f} min", flush=True)
    fh.close()
    print(f"done -> {out_path}", flush=True)


if __name__ == "__main__":
    main()

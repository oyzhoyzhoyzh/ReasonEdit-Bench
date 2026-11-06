"""Sensitivity of the region-grounded protocol to its two free knobs.

Two parameters of the probing protocol were fixed by hand and never varied:
the crop margin (``region_to_box(..., pad=0.12)``) and the judge temperature
(0.0).  A reviewer will ask whether the diagnosis survives a different choice, so
this module re-judges the same probes under a tighter / looser crop and under a
non-zero temperature, and compares the verdicts and the recomputed scores with the
cached defaults.

Usage:
    python -m reasondata.sensitivity --axis pad  --pads 0.0,0.30
    python -m reasondata.sensitivity --axis temp --temps 0.3
    python -m reasondata.sensitivity --compare
"""

from __future__ import annotations

import argparse
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench
from .framing_ablation import _ccs_from, _item_ccs, _paired_bootstrap, load_region_verdicts
from .probe import (PROBE_SYSTEM, PROBE_TEMPLATE, region_to_box, record_from_answer,
                    resize_max, side_by_side, build_probes)
from .runs import list_runs, outputs_of
from .vlm import DashScopeClient


def _resolve(run_dir: Path, item_id: str):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = run_dir / f"{item_id}{ext}"
        if p.exists():
            return p
    return None


def canvas_with_pad(probe, src: Image.Image, edt: Image.Image, pad: float,
                    max_image_side: int = 768) -> Image.Image:
    box_s = region_to_box(probe.region, src.size, pad=pad)
    box_e = region_to_box(probe.region, edt.size, pad=pad)
    return resize_max(side_by_side(src.crop(box_s), edt.crop(box_e)), max_image_side)


def build_work(systems, axis, settings, limit_items, seed):
    items = {it["id"]: it for it in load_bench()}
    runs = list_runs()
    region = load_region_verdicts()
    rng = random.Random(seed)
    work = []
    for system in systems:
        run_dir = runs.get(system)
        if run_dir is None:
            raise SystemExit(f"no run directory for system {system!r}")
        ids = sorted({p.stem for p in run_dir.glob("*.png")} | set(outputs_of(run_dir)))
        if limit_items and limit_items < len(ids):
            step = max(1, len(ids) // limit_items)
            ids = ids[::step][:limit_items]
        for item_id in ids:
            item = items.get(item_id)
            out_img = _resolve(run_dir, item_id)
            if item is None or out_img is None:
                continue
            src = config.BENCH_IMAGES / f"{item['image_id']}.jpg"
            for probe in build_probes(item, system, out_img):
                if probe.region is None or probe.pid not in region:
                    continue
                for s in settings:
                    work.append((probe, src, out_img, axis, s))
    return work


def run(systems, axis, settings, out_name, limit_items, seed, workers, max_side):
    out_path = config.RESULTS / out_name
    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add(f"{r['pid']}|{r['axis']}|{r['setting']}")
    work = build_work(systems, axis, settings, limit_items, seed)
    todo = [w for w in work if f"{w[0].pid}|{w[3]}|{w[4]}" not in done]
    print(f"axis={axis} settings={settings} candidates={len(work)} todo={len(todo)}", flush=True)
    if not todo:
        return

    client = DashScopeClient()
    fh = out_path.open("a")
    lock = threading.Lock()
    t0 = time.time()

    def do_one(w):
        probe, src_p, out_p, ax, setting = w
        try:
            src = Image.open(src_p).convert("RGB")
            edt = Image.open(out_p).convert("RGB")
            if ax == "pad":
                canvas = canvas_with_pad(probe, src, edt, float(setting), max_side)
                temp = 0.0
            else:
                from .probe import probe_inputs
                _prompt, canvas = probe_inputs(probe, src, edt, max_side)
                temp = float(setting)
            resp = client.chat(PROBE_TEMPLATE.format(question=probe.question),
                               images=[canvas], system=PROBE_SYSTEM,
                               temperature=temp, max_tokens=2000)
            rec = record_from_answer(probe, resp.text, resp.latency)
        except Exception as exc:  # noqa: BLE001
            rec = {"pid": probe.pid, "item_id": probe.item_id, "system": probe.system,
                   "kind": probe.kind, "question": probe.question, "answer": "unclear",
                   "value": 0.5, "evidence": f"error: {exc}", "region": probe.region,
                   "ordinal": probe.ordinal, "latency": 0.0}
        rec["axis"], rec["setting"] = ax, str(setting)
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
        return rec

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(do_one, w) for w in todo]):
            fut.result()
            n += 1
            if n % 100 == 0:
                print(f"  {n}/{len(todo)}  {n/(time.time()-t0):.1f}/s", flush=True)
    fh.close()
    print(f"done {n} in {time.time()-t0:.0f}s -> {out_path}", flush=True)


def compare(out_name="probes_sensitivity.jsonl"):
    region = load_region_verdicts()
    rows = [json.loads(l) for l in (config.RESULTS / out_name).read_text().splitlines() if l.strip()]
    out = {"n": len(rows), "axes": {}}
    for axis in sorted({r["axis"] for r in rows}):
        out["axes"][axis] = {}
        for setting in sorted({r["setting"] for r in rows if r["axis"] == axis}):
            sel = [r for r in rows if r["axis"] == axis and r["setting"] == setting]
            per_sys = {}
            for system in sorted({r["system"] for r in sel}):
                w = [r for r in sel if r["system"] == system]
                reg = [region[r["pid"]] for r in w]
                agree = sum(1 for a, b in zip(w, reg) if a["answer"] == b["answer"]) / len(w)
                iw, ir = _item_ccs(w), _item_ccs(reg)
                shared = [i for i in iw if i in ir]
                mean, lo, hi, p = _paired_bootstrap([iw[i] for i in shared],
                                                    [ir[i] for i in shared])
                per_sys[system] = {
                    "n": len(w), "agreement": agree,
                    "ccs_variant": _ccs_from(w)["ccs"], "ccs_default": _ccs_from(reg)["ccs"],
                    "delta_ccs": mean, "ci": [lo, hi], "p": p,
                    "yes_variant": sum(1 for r in w if r["answer"] == "yes") / len(w),
                    "yes_default": sum(1 for r in reg if r["answer"] == "yes") / len(reg),
                }
            out["axes"][axis][setting] = per_sys
    dst = config.RESULTS / "analysis" / "sensitivity.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print("wrote", dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="qwen_image_edit,instructpix2pix")
    ap.add_argument("--axis", default="pad", choices=["pad", "temp"])
    ap.add_argument("--pads", default="0.0,0.30")
    ap.add_argument("--temps", default="0.3")
    ap.add_argument("--out", default="probes_sensitivity.jsonl")
    ap.add_argument("--limit-items", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max-image-side", type=int, default=768)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    if args.compare:
        compare(args.out)
        return
    settings = (args.pads if args.axis == "pad" else args.temps).split(",")
    run([s for s in args.systems.split(",") if s], args.axis, settings, args.out,
        args.limit_items, args.seed, args.workers, args.max_image_side)


if __name__ == "__main__":
    main()

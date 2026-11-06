"""Whole-frame versus region-grounded probing.

The central methodological claim of the paper is that verifying a proposition on
the region it is about keeps a local failure visible, whereas a judge that sees
the whole scene can be convinced by an untouched, well-rendered background.

This module tests that claim directly.  It re-judges the *same* probes, with the
*same* judge, the same question and the same canvas budget, but always on the
full frame instead of the proposition's region, and then compares the two sets of
verdicts.  Probes that already have no region are identical under the two
conditions and are skipped.  A small random subsample of the region condition is
re-judged in the same batch so that judge drift between the original run and this
one can be bounded.

Usage:
    python -m reasondata.framing_ablation --systems qwen_image_edit,instructpix2pix
    python -m reasondata.framing_ablation --compare
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench
from .probe import Probe, probe_inputs, record_from_answer
from .runs import list_runs, outputs_of
from .vlm import DashScopeClient


REGION_PROBE_FILES = [
    "probes_api_all.jsonl",
    "probes_api_new.jsonl",
    "probes_api_oracle.jsonl",
    "probes_api_scaffold.jsonl",
]


def _flat(probe: Probe) -> Probe:
    """The same probe judged on the full frame (region removed)."""
    return Probe(probe.pid, probe.item_id, probe.system, probe.kind, probe.question,
                 None, probe.weight, probe.ordinal)


def load_region_verdicts() -> dict[str, dict]:
    """pid -> cached region-grounded verdict, from the files the paper scores from."""
    out: dict[str, dict] = {}
    for name in REGION_PROBE_FILES:
        path = config.RESULTS / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["pid"]] = rec
    return out


def build_work(systems, limit_items, seed, recheck_frac):
    items = {it["id"]: it for it in load_bench()}
    runs = list_runs()
    region = load_region_verdicts()
    rng = random.Random(seed)

    def resolve(run_dir: Path, item_id: str):
        """Locate a generated image even when the manifest holds stale paths."""
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = run_dir / f"{item_id}{ext}"
            if p.exists():
                return p
        return None

    work = []
    for system in systems:
        run_dir = runs.get(system)
        if run_dir is None:
            raise SystemExit(f"no run directory for system {system!r}")
        listed = outputs_of(run_dir)
        outputs = []
        for p in sorted(run_dir.glob("*")):
            if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            outputs.append((p.stem, p))
        for item_id, p in sorted(listed.items()):
            if item_id not in {i for i, _ in outputs}:
                outputs.append((item_id, p))
        outputs = sorted(set(outputs))
        if limit_items and limit_items < len(outputs):
            step = max(1, len(outputs) // limit_items)
            outputs = outputs[::step][:limit_items]
        for item_id, out_img in outputs:
            item = items.get(item_id)
            if item is None:
                continue
            src = config.BENCH_IMAGES / f"{item['image_id']}.jpg"
            from .probe import build_probes
            for probe in build_probes(item, system, out_img):
                if probe.region is None:
                    continue
                cached = region.get(probe.pid)
                if cached is None:
                    continue
                cond = "whole"
                if rng.random() < recheck_frac:
                    cond = "region"
                work.append((probe, src, out_img, cond))
    return work


def run(systems, out_name, limit_items, seed, recheck_frac, workers, max_side):
    out_path = config.RESULTS / out_name
    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done.add(rec["pid"] + "|" + rec["condition"])

    work = build_work(systems, limit_items, seed, recheck_frac)
    todo = [w for w in work if (w[0].pid + "|" + w[3]) not in done]
    print(f"systems={systems} candidates={len(work)} todo={len(todo)}", flush=True)
    if not todo:
        return

    client = DashScopeClient()
    fh = out_path.open("a")
    t0 = time.time()
    lock = __import__("threading").Lock()

    def do_one(w):
        probe, src_p, out_p, cond = w
        try:
            src = Image.open(src_p).convert("RGB")
            edt = Image.open(out_p).convert("RGB")
            target = _flat(probe) if cond == "whole" else probe
            prompt, canvas = probe_inputs(target, src, edt, max_image_side=max_side)
            from .probe import PROBE_SYSTEM
            resp = client.chat(prompt, images=[canvas], system=PROBE_SYSTEM,
                               temperature=0.0, max_tokens=2000)
            rec = record_from_answer(probe, resp.text, resp.latency)
        except Exception as exc:  # noqa: BLE001
            rec = {"pid": probe.pid, "item_id": probe.item_id, "system": probe.system,
                   "kind": probe.kind, "question": probe.question, "answer": "unclear",
                   "value": 0.5, "evidence": f"error: {exc}", "region": probe.region,
                   "ordinal": probe.ordinal, "latency": 0.0}
        rec["condition"] = cond
        rec["ori_region"] = probe.region
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
        return rec

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(do_one, w) for w in todo]
        for fut in as_completed(futs):
            fut.result()
            n += 1
            if n % 50 == 0:
                print(f"  {n}/{len(todo)}  {n/(time.time()-t0):.1f}/s", flush=True)
    fh.close()
    print(f"done {n} probes in {time.time()-t0:.0f}s -> {out_path}", flush=True)


def _ccs_from(verdicts: list[dict]) -> dict:
    """Recompute the causal scores from a set of probe verdicts (region or whole)."""
    by_item: dict[str, dict] = {}
    for r in verdicts:
        d = by_item.setdefault(r["item_id"], {"tcs": [], "dps": [], "nps": []})
        if r["kind"] in d:
            d[r["kind"]].append(float(r["value"]))
    tcs = [sum(v["tcs"]) / len(v["tcs"]) for v in by_item.values() if v["tcs"]]
    dps = [sum(v["dps"]) / len(v["dps"]) for v in by_item.values() if v["dps"]]
    nps = [sum(v["nps"]) / len(v["nps"]) for v in by_item.values() if v["nps"]]
    m = lambda x: sum(x) / len(x) if x else float("nan")  # noqa: E731
    t, d, n = m(tcs), m(dps), m(nps)
    return {"tcs": t, "dps": d, "nps": n, "ccs": (t + d + n) / 3,
            "n_items": len(by_item), "n_probes": len(verdicts)}


def _item_ccs(verdicts: list[dict]) -> dict[str, float]:
    """Per-item CCS on a fixed probe subset (used for the paired test)."""
    by_item: dict[str, dict] = {}
    for r in verdicts:
        d = by_item.setdefault(r["item_id"], {"tcs": [], "dps": [], "nps": []})
        if r["kind"] in d:
            d[r["kind"]].append(float(r["value"]))
    out = {}
    for item_id, v in by_item.items():
        parts = [sum(v[k]) / len(v[k]) for k in ("tcs", "dps", "nps") if v[k]]
        if parts:
            out[item_id] = sum(parts) / len(parts)
    return out


def _paired_bootstrap(a: list[float], b: list[float], n_boot: int = 5000,
                      seed: int = 0):
    """Paired bootstrap of mean(a) - mean(b); deterministic for a fixed seed."""
    rng = random.Random(seed)
    diffs = [x - y for x, y in zip(a, b)]
    mean = sum(diffs) / len(diffs)
    stats = sorted(sum(diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))) / len(diffs)
                   for _ in range(n_boot))
    lo, hi = stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]
    p = 2 * min(sum(1 for s in stats if s <= 0) / n_boot,
                sum(1 for s in stats if s >= 0) / n_boot)
    return mean, lo, hi, min(1.0, p)


def compare(out_name="probes_framing.jsonl"):
    region = load_region_verdicts()
    rows = [json.loads(l) for l in (config.RESULTS / out_name).read_text().splitlines() if l.strip()]
    whole = [r for r in rows if r["condition"] == "whole"]
    recheck = [r for r in rows if r["condition"] == "region"]

    systems = sorted({r["system"] for r in whole})
    out = {"n_whole": len(whole), "systems": {}}

    if recheck:
        agree = sum(1 for r in recheck if region[r["pid"]]["answer"] == r["answer"])
        out["region_recheck"] = {"n": len(recheck), "agreement": agree / len(recheck)}

    for system in systems:
        w = [r for r in whole if r["system"] == system]
        reg = []
        for r in w:
            c = region.get(r["pid"])
            if c is not None:
                reg.append(c)
        agree = sum(1 for a, b in zip(w, reg) if a["answer"] == b["answer"])
        pair = {}
        for kind in ("tcs", "dps", "nps"):
            ww = [r for r in w if r["kind"] == kind]
            rr = [region[r["pid"]] for r in ww]
            if not ww:
                continue
            yes_w = sum(1 for r in ww if r["answer"] == "yes") / len(ww)
            yes_r = sum(1 for r in rr if r["answer"] == "yes") / len(rr)
            unc_w = sum(1 for r in ww if r["answer"] == "unclear") / len(ww)
            unc_r = sum(1 for r in rr if r["answer"] == "unclear") / len(rr)
            pair[kind] = {"n": len(ww), "yes_whole": yes_w, "yes_region": yes_r,
                          "unclear_whole": unc_w, "unclear_region": unc_r,
                          "agree": sum(1 for a, b in zip(ww, rr) if a["answer"] == b["answer"]) / len(ww)}
        # CCS recomputed on the identical probe subset under each condition
        ccs_whole = _ccs_from(w)
        ccs_region = _ccs_from(reg)
        iw, ir = _item_ccs(w), _item_ccs(reg)
        shared = [i for i in iw if i in ir]
        dmean, dlo, dhi, dp = _paired_bootstrap([iw[i] for i in shared],
                                                [ir[i] for i in shared])
        probe_stats = {}
        for kind in ("tcs", "dps"):
            wk = [r for r in w if r["kind"] == kind]
            rk = [region[r["pid"]] for r in wk]
            if not wk:
                continue
            probe_stats[kind] = {
                "n": len(wk),
                "yes_whole": sum(1 for r in wk if r["answer"] == "yes") / len(wk),
                "yes_region": sum(1 for r in rk if r["answer"] == "yes") / len(rk),
                "value_whole": sum(float(r["value"]) for r in wk) / len(wk),
                "value_region": sum(float(r["value"]) for r in rk) / len(rk),
                "unclear_whole": sum(1 for r in wk if r["answer"] == "unclear") / len(wk),
                "unclear_region": sum(1 for r in rk if r["answer"] == "unclear") / len(rk),
            }
        out["systems"][system] = {
            "n": len(w), "verdict_agreement": agree / len(w),
            "by_kind": pair,
            "probe_stats": probe_stats,
            "delta_ccs": dmean, "delta_ci": [dlo, dhi], "delta_p": dp,
            "whole": ccs_whole, "region": ccs_region,
            "delta_ccs_whole_minus_region": ccs_whole["ccs"] - ccs_region["ccs"],
        }
    dst = config.RESULTS / "analysis" / "framing.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print("wrote", dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="qwen_image_edit,instructpix2pix")
    ap.add_argument("--out", default="probes_framing.jsonl")
    ap.add_argument("--limit-items", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--recheck-frac", type=float, default=0.1)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--max-image-side", type=int, default=768)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    if args.compare:
        compare(args.out)
        return
    run([s for s in args.systems.split(",") if s], args.out, args.limit_items,
        args.seed, args.recheck_frac, args.workers, args.max_image_side)


if __name__ == "__main__":
    main()

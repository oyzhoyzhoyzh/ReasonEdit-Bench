"""Cross-benchmark evaluation on GEdit-Bench (Step1X-Edit, 2025).

The proposal asks for a comparison against public editing benchmarks.  GEdit-Bench is
the useful one to run because its protocol is exactly the one the paper argues against:
it ships real user instructions and source images, no reference outputs, and grades an
edit with a holistic vision-language verdict plus source-similarity metrics.  Running the
same systems under both protocols therefore tests whether the standard protocol and the
causal contract agree about which editors are better.

Stages::

    python -m reasondata.crossbench prepare --n-per-type 24
    python -m reasondata.crossbench generate --model qwen_image_edit --gpu 0 --shard 0/2
    python -m reasondata.crossbench score --gpu 0
    python -m reasondata.crossbench compare
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from . import config
from .auto_metrics import AutoMetrics
from .bench import read_jsonl
from .runs import FINAL_SYSTEMS, SYSTEM_LABELS, label_short
from .stats import spearman

GEDIT_DIR = Path(os.environ.get("RIE_GEDIT_DIR", config.RAW_DATA / "GEdit-Bench"))
CROSS_DIR = config.DATA / "GEdit-Bench"
SRC_DIR = CROSS_DIR / "images"
OUT_ROOT = config.RESULTS / "crossbench"

#: only the base conditions are meaningful on a benchmark with no causal annotation
CROSS_SYSTEMS = ["instructpix2pix", "sd15_inpaint", "sd2_inpaint", "sdxl_inpaint",
                 "flux_fill", "qwen_image_edit"]

HOLISTIC_SYSTEM = (
    "You are an image-editing judge. You see the source photograph and the edited "
    "result. Decide whether the edit followed the instruction. Answer with strict JSON."
)
HOLISTIC_PROMPT = """Instruction: {instruction}

Does the edited image follow this instruction? Judge the whole frame.
Reply with JSON only: {{"follows": true/false, "evidence": "at most twelve words"}}"""


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted((v, i) for i, v in enumerate(values))
    out = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[ordered[k][1]] = rank
        i = j + 1
    return out


def spear(x: list[float], y: list[float]) -> float:
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def exact_spearman_p(x: list[float], y: list[float]) -> float:
    """Two-sided exact permutation p-value for a small system-level sample."""
    observed = abs(spear(x, y))
    total = hit = 0
    for perm in itertools.permutations(y):
        total += 1
        if abs(spear(x, list(perm))) >= observed - 1e-12:
            hit += 1
    return hit / total


def load_items() -> list[dict]:
    return read_jsonl(CROSS_DIR / "items.jsonl")


# --------------------------------------------------------------------- prepare --
def prepare(n_per_type: int, seed: int = 7) -> None:
    import datasets

    files = sorted(glob.glob(str(GEDIT_DIR / "data-*.arrow")))
    ds = datasets.load_dataset("arrow", data_files=files, split="train")
    ds = ds.filter(lambda r: r["instruction_language"] == "en")
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    by_type: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(ds["task_type"]):
        by_type[t].append(i)
    import random
    rng = random.Random(seed)
    picked: list[int] = []
    for t in sorted(by_type):
        idx = by_type[t]
        rng.shuffle(idx)
        picked.extend(idx[:n_per_type])
    rows = []
    for i in sorted(picked):
        rec = ds[i]
        iid = f"ge_{i:05d}"
        path = SRC_DIR / f"{iid}.jpg"
        if not path.exists():
            img = rec["input_image_raw"]
            if max(img.size) > 1536:
                s = 1536 / max(img.size)
                img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
            img.convert("RGB").save(path, quality=95)
        rows.append({"id": iid, "task_type": rec["task_type"],
                     "instruction": rec["instruction"].strip(), "src": str(path)})
    (CROSS_DIR / "items.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with (CROSS_DIR / "items.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[crossbench] {len(rows)} items -> {CROSS_DIR/'items.jsonl'}")
    print(Counter(r["task_type"] for r in rows).most_common())


# -------------------------------------------------------------------- generate --
def generate(model: str, gpu: str, shard: str, limit: int) -> None:
    from .editor import build_editor

    items = load_items()
    k, n = (int(x) for x in shard.split("/"))
    items = [it for i, it in enumerate(items) if i % n == k]
    if limit:
        items = items[:limit]
    out_dir = OUT_ROOT / model
    out_dir.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in out_dir.glob("*.jpg")}
    todo = [it for it in items if it["id"] not in done]
    print(f"[{model}] shard {shard}: {len(todo)} to run ({len(done)} cached)", flush=True)
    if not todo:
        return
    editor = build_editor(model, device=f"cuda:{gpu}")
    import time
    for i, it in enumerate(todo, 1):
        src = Image.open(it["src"]).convert("RGB")
        t0 = time.time()
        try:
            out = editor.edit(src, it["instruction"], seed=0)
            out.convert("RGB").save(out_dir / f"{it['id']}.jpg", quality=95)
            status = f"{time.time()-t0:.1f}s"
        except Exception as exc:  # noqa: BLE001
            status = f"ERROR {exc}"
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} {status}", flush=True)


# ----------------------------------------------------------------------- score --
def score(gpu: str) -> None:
    from .probe import resize_max, side_by_side
    from .vlm import LocalVLM

    items = load_items()
    am = AutoMetrics(device=f"cuda:{gpu}")
    judge = LocalVLM.get(config.MODELS["qwen3vl8b"], device=f"cuda:{gpu}")
    for model in CROSS_SYSTEMS:
        out_dir = OUT_ROOT / model
        outs = {p.stem: p for p in out_dir.glob("*.jpg")}
        todo = [it for it in items
                if it["id"] in outs and not (out_dir / f"{it['id']}.json").exists()]
        if not todo:
            print(f"[{model}] {len(outs)} outputs, all scored", flush=True)
            continue
        for i in range(0, len(todo), 8):
            chunk = todo[i:i + 8]
            srcs = [Image.open(it["src"]).convert("RGB") for it in chunk]
            edts = [Image.open(outs[it["id"]]).convert("RGB") for it in chunk]
            ins = [it["instruction"] for it in chunk]
            clip_s = am.clip_scores(edts, ins)
            dino = am.dino_sim(srcs, edts)
            lp = am.lpips(srcs, edts)
            canvases = [resize_max(side_by_side(resize_max(a, 448), resize_max(b, 448)), 896)
                        for a, b in zip(srcs, edts)]
            resps = judge.chat_batch([HOLISTIC_PROMPT.format(instruction=t) for t in ins],
                                     [[c] for c in canvases], system=HOLISTIC_SYSTEM,
                                     temperature=0.0, max_tokens=200)
            for it, cs, dn, l, r in zip(chunk, clip_s, dino, lp, resps):
                try:
                    from .vlm import extract_json
                    v = extract_json(r.text)
                    follows = float(bool(v.get("follows")))
                except Exception:  # noqa: BLE001
                    low = r.text.lower()
                    follows = float('"follows": true' in low or '"follows":true' in low)
                (out_dir / f"{it['id']}.json").write_text(json.dumps(
                    {"id": it["id"], "task_type": it["task_type"], "system": model,
                     "clipscore": cs, "dino_i": dn, "lpips": l, "follows": follows}))
        print(f"[{model}] scored {len(todo)}", flush=True)


# --------------------------------------------------------------------- compare --
def compare(table_path: str) -> None:
    # GEdit-Bench side: mean over items of each standard metric, per system
    rows = []
    for model in CROSS_SYSTEMS:
        recs = list((OUT_ROOT / model).glob("*.json"))
        vals = [json.loads(p.read_text()) for p in recs]
        if not vals:
            continue
        rows.append({
            "system": model, "n": len(vals),
            "clipscore": sum(v["clipscore"] for v in vals) / len(vals),
            "dino_i": sum(v["dino_i"] for v in vals) / len(vals),
            "lpips": sum(v["lpips"] for v in vals) / len(vals),
            "follows": sum(v["follows"] for v in vals) / len(vals),
        })
    # ReasonEdit-Bench side: contract CCS under the API judge
    local = {r["system"]: r for r in
             json.loads((config.RESULTS / "analysis" / "summary.json").read_text())["overall"]}
    for row in rows:
        # summary.json is keyed by display label; rows carry the internal system key
        s = local.get(SYSTEM_LABELS.get(row["system"], row["system"]))
        row["reason_edit_ccs"] = s["ccs"] if s else None
        row["reason_edit_contract"] = s["strict_success"] if s else None
    have = [r for r in rows if r["reason_edit_ccs"] is not None]
    # GEdit-Bench's own protocol: instruction following first, then preservation
    order_gedit = sorted(have, key=lambda r: (-r["follows"], -r["dino_i"]))
    order_ours = sorted(have, key=lambda r: -r["reason_edit_ccs"])
    correlations = {}
    for name, field in (("follows", "follows"), ("clip", "clipscore"),
                        ("dino", "dino_i"), ("lpips", "lpips")):
        x = [r[field] for r in have]
        y = [r["reason_edit_ccs"] for r in have]
        correlations[name] = {
            "rho": spear(x, y),
            "exact_permutation_p": exact_spearman_p(x, y),
        }
    out = {
        "rows": rows,
        "order_gedit": [r["system"] for r in order_gedit],
        "order_reason": [r["system"] for r in order_ours],
        "spearman_follows_vs_ccs": spearman([r["follows"] for r in have],
                                            [r["reason_edit_ccs"] for r in have]),
        "spearman_clip_vs_ccs": spearman([r["clipscore"] for r in have],
                                         [r["reason_edit_ccs"] for r in have]),
        "spearman_dino_vs_ccs": spearman([r["dino_i"] for r in have],
                                         [r["reason_edit_ccs"] for r in have]),
        "spearman_lpips_vs_ccs": spearman([r["lpips"] for r in have],
                                          [r["reason_edit_ccs"] for r in have]),
        "correlations": correlations,
    }
    (config.RESULTS / "analysis" / "crossbench.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))

    lines = ["\\footnotesize", "\\setlength{\\tabcolsep}{3.5pt}",
             "\\begin{tabular}{lccccc}", "\\toprule",
             "System & Follows (\\%)$\\uparrow$ & CLIP-S$\\uparrow$ & DINO-I$\\uparrow$ & "
             "LPIPS$\\downarrow$ & CCS$_{\\mathrm{ours}}\\uparrow$ \\\\", "\\midrule"]
    for r in sorted(have, key=lambda r: -r["reason_edit_ccs"]):
        lines.append(f"{label_short(r["system"])} & {100*r['follows']:.0f} & "
                     f"{r['clipscore']:.2f} & {r['dino_i']:.2f} & {r['lpips']:.2f} & "
                     f"{r['reason_edit_ccs']:.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    Path(table_path).write_text("\n".join(lines))
    print(json.dumps(out, indent=2, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--n-per-type", type=int, default=24)
    p = sub.add_parser("generate")
    p.add_argument("--model", required=True)
    p.add_argument("--gpu", default="0")
    p.add_argument("--shard", default="0/1")
    p.add_argument("--limit", type=int, default=0)
    p = sub.add_parser("score")
    p.add_argument("--gpu", default="0")
    p = sub.add_parser("compare")
    p.add_argument("--table", default=str(config.ROOT / "paper" / "tables"
                                          / "crossbench_table.tex"))
    args = ap.parse_args()
    if args.stage == "prepare":
        prepare(args.n_per_type)
    elif args.stage == "generate":
        generate(args.model, args.gpu, args.shard, args.limit)
    elif args.stage == "score":
        score(args.gpu)
    else:
        compare(args.table)


if __name__ == "__main__":
    main()

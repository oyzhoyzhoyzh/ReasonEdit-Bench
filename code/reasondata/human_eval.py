"""Build the human-audit kit.

The automatic scores are only trustworthy if a human agrees with them, so we
export a stratified sample of (item, system) results as montages -- source image,
generated image, instruction, reasoning chain and the probes -- together with a
blank rating sheet.  The ratings are later compared with the automatic metrics
(Spearman correlation) and with the automatic failure attribution (Cohen kappa).
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from . import config
from .bench import load_bench, read_jsonl, write_jsonl
from .probe import resize_max, side_by_side
from .runs import label, list_runs, outputs_of


def build_montage(item: dict, src: Image.Image, edt: Image.Image, header: str) -> Image.Image:
    pair = side_by_side(resize_max(src, 640), resize_max(edt, 640))
    band = 120
    canvas = Image.new("RGB", (pair.width, pair.height + band), (255, 255, 255))
    canvas.paste(pair, (0, band))
    d = ImageDraw.Draw(canvas)
    y = 6
    for line in header.split("\n"):
        d.text((8, y), line[:150], fill=(0, 0, 0))
        y += 15
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "human_eval"))
    ap.add_argument("--per-system", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--systems", default=None, help="comma separated subset of systems")
    ap.add_argument("--contact-sheet", type=int, default=4,
                    help="montages per contact sheet (0 disables)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    items = {it["id"]: it for it in load_bench(args.bench)}
    scores = read_jsonl(Path(args.scores))
    runs = list_runs()

    by_system = defaultdict(list)
    for r in scores:
        by_system[r["system"]].append(r)
    rng = random.Random(args.seed)
    sheet = []
    for system, rs in sorted(by_system.items()):
        if args.systems and system not in set(args.systems.split(",")):
            continue
        # stratify: half successes, half failures where possible
        succ = [r for r in rs if r["success"]]
        fail = [r for r in rs if not r["success"]]
        rng.shuffle(succ), rng.shuffle(fail)
        pick = succ[: args.per_system // 2] + fail[: args.per_system - args.per_system // 2]
        for r in pick:
            item = items[r["item_id"]]
            run_dir = runs[system]
            out_img = outputs_of(run_dir).get(r["item_id"])
            if not out_img:
                continue
            src = Image.open(config.BENCH_IMAGES / f"{item['image_id']}.jpg").convert("RGB")
            edt = Image.open(out_img).convert("RGB")
            header = (
                f"[{r['item_id']}] system={label(system)} type={item['type']} "
                f"difficulty={item['meta']['difficulty']}\n"
                f"instruction: {item['instruction']}\n"
                f"reasoning chain: " + " | ".join(s["thought"] for s in item["reasoning_chain"])[:180]
            )
            montage = build_montage(item, src, edt, header)
            fname = f"{r['item_id']}__{system}.jpg"
            montage.save(out_dir / "images" / fname, quality=90)
            sheet.append({
                "file": fname, "item_id": r["item_id"], "system": system,
                "type": item["type"], "domain": item["domain"],
                "instruction": item["instruction"],
                "expected_effects": [e["probe"] for e in item["effects"]],
                "preserved": [p["probe"] for p in item["preserved"]],
                "auto_tcs": r["tcs"], "auto_dps": r["dps"], "auto_nps": r["nps"],
                "auto_ccs": r["ccs"], "auto_failure": r["failure"],
                "rate_instruction_following_1to5": "",
                "rate_logical_consistency_1to5": "",
                "rate_image_quality_1to5": "",
                "manual_failure_class (OK/IUE/RPE/GE/PQE/CI)": "",
                "notes": "",
            })
    write_jsonl(out_dir / "rating_sheet.jsonl", sheet)
    print(f"wrote {len(sheet)} montages -> {out_dir}")

    if args.contact_sheet:
        per = int(args.contact_sheet)
        files = [s["file"] for s in sheet]
        for i in range(0, len(files), per):
            chunk = files[i : i + per]
            tile_w = 620
            tiles = []
            for f in chunk:
                im = Image.open(out_dir / "images" / f).convert("RGB")
                s = tile_w / im.width
                tiles.append(im.resize((tile_w, max(1, int(im.height * s))), Image.LANCZOS))
            h = max(t.height for t in tiles)
            canvas = Image.new("RGB", (tile_w * 2 + 12, h * 2 + 12), (255, 255, 255))
            for k, t in enumerate(tiles):
                canvas.paste(t, ((k % 2) * (tile_w + 12), (k // 2) * (h + 12)))
            path = out_dir / f"sheet_{i//per:02d}.jpg"
            canvas.save(path, quality=88)
        print(f"contact sheets -> {out_dir}")


if __name__ == "__main__":
    main()

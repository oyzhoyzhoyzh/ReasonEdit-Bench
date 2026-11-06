"""Qualitative figure: cases where the verification loop repaired a broken contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .bench import read_jsonl
from .probe import resize_max
from .runs import outputs_of


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "figures" / "fig6_repair.pdf"))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--height", type=int, default=320)
    args = ap.parse_args()

    items = {it["id"]: it for it in read_jsonl(config.BENCH_DIR / "bench.jsonl")}
    rows = read_jsonl(Path(args.scores))
    by = {}
    for r in rows:
        by.setdefault(r["system"], {})[r["item_id"]] = r
    cot = by.get("qwen_image_edit__cot", {})
    scaf = by.get("qwen_image_edit__scaffold_full", {})
    cands = []
    for iid, s in scaf.items():
        c = cot.get(iid)
        if not c:
            continue
        if c["dps"] < 0.75 and s["dps"] >= 0.9 and s["nps"] >= 0.75 and s["tcs"] >= 1.0:
            cands.append((s["dps"] - c["dps"], iid))
    cands.sort(reverse=True)
    picks = [i for _, i in cands[: args.n]]
    print("selected:", picks)

    cot_dir = outputs_of(config.RESULTS / "qwen_image_edit" / "cot")
    scaf_dir = outputs_of(config.RESULTS / "qwen_image_edit" / "scaffold_full")
    cot_root = config.RESULTS / "qwen_image_edit" / "cot"
    scaf_root = config.RESULTS / "qwen_image_edit" / "scaffold_full"
    H = args.height
    W = 500
    gap = 12
    label_w = 38
    header_h = 52
    row_gap = 8
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if not bold_path.exists():
        bold_path = font_path
    header_font = ImageFont.truetype(str(bold_path), 22)
    label_font = ImageFont.truetype(str(bold_path), 22)

    def fit(im):
        im.thumbnail((W, H), Image.LANCZOS)
        cell = Image.new("RGB", (W, H), (255, 255, 255))
        cell.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        return cell

    def local_output(root: Path, table: dict[str, Path], item_id: str) -> Path:
        if item_id in table and table[item_id].exists():
            return table[item_id]
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = root / f"{item_id}{ext}"
            if path.exists():
                return path
        raise FileNotFoundError(f"no output for {item_id} under {root}")

    tiles = []
    row_width = label_w + 3 * W + 2 * gap
    for index, iid in enumerate(picks):
        item = items[iid]
        src = fit(Image.open(config.BENCH_IMAGES / f"{item['image_id']}.jpg").convert("RGB"))
        a = fit(Image.open(local_output(cot_root, cot_dir, iid)).convert("RGB"))
        b = fit(Image.open(local_output(scaf_root, scaf_dir, iid)).convert("RGB"))
        row = Image.new("RGB", (row_width, H), (255, 255, 255))
        row.paste(src, (label_w, 0))
        row.paste(a, (label_w + W + gap, 0))
        row.paste(b, (label_w + 2 * (W + gap), 0))
        d = ImageDraw.Draw(row)
        d.text((8, H // 2 - 14), f"({chr(97 + index)})", fill=(0, 0, 0), font=label_font)
        tiles.append(row)

    canvas = Image.new(
        "RGB",
        (row_width, header_h + len(tiles) * H + (len(tiles) - 1) * row_gap),
        (255, 255, 255),
    )
    draw = ImageDraw.Draw(canvas)
    headers = ("Source", "First-pass CoT", "Repaired output")

    def centered_text(text: str, left: int, right: int, y: int, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        x = left + (right - left - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, fill=(0, 0, 0), font=font)

    for col, title in enumerate(headers):
        left = label_w + col * (W + gap)
        centered_text(title, left, left + W, 12, header_font)
    y = header_h
    for t in tiles:
        canvas.paste(t, (0, y))
        y += H + row_gap
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".pdf":
        canvas.save(out, "PDF", resolution=300)
        canvas.save(out.with_suffix(".png"), quality=90)
    else:
        canvas.save(out, quality=90)
    print("wrote", out)


if __name__ == "__main__":
    main()

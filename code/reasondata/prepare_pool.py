"""Build a pool of candidate source images from the local datasets.

Two sources are used:

* MagicBrush -- real photographs with human written editing instructions.  We
  keep the photographs and discard the original (surface-level) instructions,
  because our benchmark writes its own reasoning-centric instructions.
* ADE20K -- scene photographs shipped with per-object polygons, which give us
  exact object extents and therefore a reliable grounding anchor for the
  object-level causal graphs.

Run ``python -m reasondata.prepare_pool --magicbrush-files 8 --ade20k 600``.
"""

from __future__ import annotations

import argparse
import io
import json

import numpy as np
import pandas as pd
from PIL import Image

from . import config

MAX_SIDE = 1024


def _save(img: Image.Image, path, max_side: int = MAX_SIDE) -> tuple[int, int]:
    img = img.convert("RGB")
    if max(img.size) > max_side:
        s = max_side / max(img.size)
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                         Image.LANCZOS)
    img.save(path, format="JPEG", quality=92)
    return img.size


def collect_magicbrush(n_files: int, out_dir, per_file: int | None = None) -> list[dict]:
    files = sorted(config.MAGICBRUSH_DIR.glob("train-*.parquet"))[:n_files]
    records, seen = [], set()
    for fp in files:
        df = pd.read_parquet(fp, columns=["img_id", "source_img"])
        if per_file:
            df = df.iloc[:per_file]
        for _, row in df.iterrows():
            img_id = int(row["img_id"])
            if img_id in seen:
                continue
            seen.add(img_id)
            name = f"mb_{img_id:08d}.jpg"
            dst = out_dir / name
            if not dst.exists():
                try:
                    img = Image.open(io.BytesIO(row["source_img"]["bytes"]))
                    _save(img, dst)
                except Exception:  # noqa: BLE001
                    continue
            records.append({
                "image_id": f"mb_{img_id:08d}",
                "path": name,
                "origin": "MagicBrush",
                "source_meta": {"img_id": img_id},
            })
    return records


def collect_ade20k(n_images: int, out_dir, start: int = 0) -> list[dict]:
    df = pd.read_parquet(config.ADE20K_PARQUET)
    records = []
    for idx in range(start, min(start + n_images, len(df))):
        row = df.iloc[idx]
        name = f"ade_{idx:06d}.jpg"
        dst = out_dir / name
        meta_objs = []
        segs = row["segmentations"]
        try:
            img = Image.open(io.BytesIO(row["image"]["bytes"]))
            size = _save(img, dst)
        except Exception:  # noqa: BLE001
            continue
        # per-object extents from the instance masks (pixel value == object id)
        for obj, seg in zip(row["objects"], segs):
            try:
                m = np.array(Image.open(io.BytesIO(seg["bytes"])))
                mask = m == int(obj["id"])
                if mask.sum() < 200:
                    continue
                ys, xs = np.where(mask)
                h, w = mask.shape
                meta_objs.append({
                    "id": int(obj["id"]),
                    "name": str(obj["name"]),
                    "bbox1000": [int(1000 * xs.min() / w), int(1000 * ys.min() / h),
                                 int(1000 * (xs.max() + 1) / w), int(1000 * (ys.max() + 1) / h)],
                    "area_frac": float(mask.mean()),
                })
            except Exception:  # noqa: BLE001
                continue
        meta_objs.sort(key=lambda o: -o["area_frac"])
        records.append({
            "image_id": name[:-4],
            "path": name,
            "origin": "ADE20K",
            "source_meta": {"scene": " ".join(map(str, row["scene"])),
                            "objects": meta_objs[:25], "size": list(size)},
        })
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--magicbrush-files", type=int, default=8)
    ap.add_argument("--ade20k", type=int, default=600)
    ap.add_argument("--ade20k-start", type=int, default=0)
    ap.add_argument("--out", default=str(config.POOL_DIR))
    args = ap.parse_args()

    out_dir = config.DATA / "pool" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    pool = []
    if args.magicbrush_files > 0:
        mb = collect_magicbrush(args.magicbrush_files, out_dir)
        print(f"MagicBrush: {len(mb)} images")
        pool += mb
    if args.ade20k > 0:
        ade = collect_ade20k(args.ade20k, out_dir, args.ade20k_start)
        print(f"ADE20K: {len(ade)} images")
        pool += ade

    index = config.POOL_DIR / "index.jsonl"
    with index.open("w") as f:
        for r in pool:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(pool)} records -> {index}")


if __name__ == "__main__":
    main()

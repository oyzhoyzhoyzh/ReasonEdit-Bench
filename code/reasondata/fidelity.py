"""Distribution-level fidelity without a VLM: a Fréchet distance between the
edited images and the source photographs they were derived from.

The paper's other reference metrics (CLIP-I, DINO-I, LPIPS) compare one edited
image with one source image.  This script adds the distribution-level
counterpart: it extracts AlexNet fc7 features for every edited image of a
system and for the source photographs, and reports the Fréchet distance between
the two feature sets.  A lower value means the system's output distribution
stays closer to the photographs it started from.

It needs no network access and no vision-language model: the AlexNet weights
ship with torchvision and are cached locally.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from . import config
from .bench import read_jsonl
from .runs import FINAL_SYSTEMS, list_runs, outputs_of


def feature_extractor(device: str):
    import torch.nn as nn
    from torchvision.models import AlexNet_Weights, alexnet

    model = alexnet(weights=AlexNet_Weights.IMAGENET1K_V1).eval().to(device)
    extractor = nn.Sequential(
        model.features, model.avgpool, nn.Flatten(), *model.classifier[:5]
    ).eval().to(device)
    preprocess = AlexNet_Weights.IMAGENET1K_V1.transforms()
    return extractor, preprocess


@torch.inference_mode()
def features(paths: list[Path], extractor, preprocess, device: str, batch: int = 32) -> np.ndarray:
    out = []
    for i in range(0, len(paths), batch):
        ims = [preprocess(Image.open(p).convert("RGB")) for p in paths[i:i + batch]]
        x = torch.stack(ims).to(device)
        out.append(extractor(x).float().cpu().numpy())
    return np.concatenate(out, axis=0) if out else np.zeros((0, 4096), dtype=np.float32)


def frechet(a: np.ndarray, b: np.ndarray, n_components: int = 256) -> float:
    """Fréchet distance between two feature sets (the FID formula).

    The raw features are 4096-dimensional while a system contributes a few
    hundred images, so the covariance is singular and its matrix square root is
    both slow and ill-conditioned.  We therefore fit one PCA basis on the pooled
    features and compute the distance in the leading ``n_components``
    directions; 256 components keep the sample-to-dimension ratio above one
    while preserving most of the variance.  This is a documented variant of the
    standard FID computation, and the paper says so.
    """

    from scipy.linalg import sqrtm

    pooled = np.concatenate([a, b], axis=0)
    mean = pooled.mean(0)
    u, s, vt = np.linalg.svd(pooled - mean, full_matrices=False)
    k = int(min(n_components, vt.shape[0]))
    basis = vt[:k]
    a = (a - mean) @ basis.T
    b = (b - mean) @ basis.T
    mu1, mu2 = a.mean(0), b.mean(0)
    c1 = np.cov(a, rowvar=False)
    c2 = np.cov(b, rowvar=False)
    diff = mu1 - mu2
    covmean, _ = sqrtm(c1.dot(c2), disp=False)
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    return float(diff.dot(diff) + np.trace(c1) + np.trace(c2) - 2.0 * np.trace(covmean))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--variants", default="base,cot,oracle,scaffold_full",
                    help="comma separated variant names to include per model")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "fidelity.json"))
    args = ap.parse_args()

    items = {it["id"]: it for it in read_jsonl(config.BENCH_DIR / args.bench)}
    runs = list_runs()
    keep = args.variants.split(",")
    systems = []
    for name in FINAL_SYSTEMS:
        if name not in runs:
            continue
        variant = name.split("__")[1] if "__" in name else "base"
        if variant in keep:
            systems.append(name)

    extractor, preprocess = feature_extractor(args.device)
    device = args.device

    src_cache: dict[str, np.ndarray] = {}
    rows = []
    for name in systems:
        run_dir = runs[name]
        outputs = outputs_of(run_dir)
        # manifests written on the original machine record stale absolute paths;
        # fall back to the item-named files next to them when that happens
        for i in items:
            if i in outputs and Path(outputs[i]).exists():
                continue
            for ext in (".png", ".jpg"):
                cand = Path(run_dir) / f"{i}{ext}"
                if cand.exists():
                    outputs[i] = cand
                    break
        ids = [i for i in items if i in outputs]
        ids = sorted(ids)[: args.limit or len(ids)]
        if not ids:
            continue
        edited = features([outputs[i] for i in ids], extractor, preprocess, device)
        per_source = []
        for i in ids:
            key = items[i]["image_id"]
            if key not in src_cache:
                src_cache[key] = features(
                    [config.BENCH_IMAGES / f"{key}.jpg"], extractor, preprocess, device)
            per_source.append(src_cache[key][0])
        source = np.stack(per_source)
        fd = frechet(edited, source)
        rows.append({"system": name, "n": len(ids), "frechet_alexnet": fd})
        print(f"{name:34s} n={len(ids):4d}  FD={fd:8.3f}")

    payload = {"feature": "alexnet-fc7", "rows": rows}
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print("wrote", args.out)


if __name__ == "__main__":
    main()

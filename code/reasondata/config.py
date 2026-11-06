"""Central configuration: filesystem layout, model registry, run-time knobs."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("RIE_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
POOL_DIR = DATA / "pool"
BENCH_DIR = DATA / "ReasonEdit-Bench"
BENCH_IMAGES = BENCH_DIR / "images"
RESULTS = ROOT / "results"
LOGS = ROOT / "logs"

for _p in (POOL_DIR, BENCH_DIR, BENCH_IMAGES, RESULTS, LOGS):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- datasets ---
# Source photographs, needed only to rebuild the benchmark from scratch.  The
# released images are already under data/ReasonEdit-Bench/images, so these paths
# matter only for `reasondata.build_bench`.
RAW_DATA = Path(os.environ.get("RIE_RAW_DATA", ROOT / "data" / "raw"))
MAGICBRUSH_DIR = Path(os.environ.get("RIE_MAGICBRUSH_DIR",
                                     RAW_DATA / "MagicBrush" / "data"))
ADE20K_PARQUET = Path(os.environ.get("RIE_ADE20K_PARQUET",
                                     RAW_DATA / "ADE20K" / "validation-00000-of-00001.parquet"))

# ------------------------------------------------------------------ models ---
# Root of the local checkpoint cache.  Overridable so that the release can be run
# from a directory other than the one used for the paper's own experiments.
HF_CACHE = os.environ.get("RIE_HF_CACHE", str(ROOT / "models"))

MODELS = {
    # vision-language models used for annotation / judging
    "qwen3vl8b": f"{HF_CACHE}/Qwen/Qwen3-VL-8B-Instruct",
    "qwen25vl7b": f"{HF_CACHE}/Qwen/Qwen2.5-VL-7B-Instruct",
    "qwen3vl32b": f"{HF_CACHE}/Qwen/Qwen3-VL-32B-Instruct",
    # editing models
    "qwen_image_edit": os.environ.get(
        "RIE_QWEN_IMAGE_EDIT_MODEL",
        f"{HF_CACHE}/ovedrive/Qwen-Image-Edit-2509-4bit",
    ),
    "flux_fill": f"{HF_CACHE}/black-forest-labs/FLUX.1-Fill-dev",
    "flux_kontext": f"{HF_CACHE}/black-forest-labs/FLUX.1-Kontext-dev",
    "powerpaint": f"{HF_CACHE}/JunhaoZhuang/PowerPaint_v2",
    "sd15_inpaint": f"{HF_CACHE}/stable-diffusion-v1-5/stable-diffusion-inpainting",
    "sd2_inpaint": f"{HF_CACHE}/sd2-community/stable-diffusion-2-inpainting",
    "instructpix2pix": f"{HF_CACHE}/timbrooks/instruct-pix2pix",
    # perceptual / retrieval backbones
    "clip": f"{HF_CACHE}/openai/clip-vit-large-patch14",
    "dinov2": f"{HF_CACHE}/facebook/dinov2-base",
    "grounding_dino": f"{HF_CACHE}/IDEA-Research/grounding-dino-tiny",
    "sam": f"{HF_CACHE}/bhf_dw/sam_vit_b_01ec64.pth",
}

# DashScope (Qwen API) -- used for large-scale annotation with a strong VLM.
DASHSCOPE_BASE = os.environ.get(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
ANNOT_MODEL = "qwen3-vl-plus"

# ------------------------------------------------------------- experiments ---
SEED = 20260924

EDIT_PROFILES = {
    "instructpix2pix": dict(steps=50, guidance=7.5, image_guidance=1.5),
    "qwen_image_edit": dict(steps=12, guidance=4.0),
    "qwen_image_edit_scaffold": dict(steps=12, guidance=4.0),
    "flux_fill": dict(steps=20, guidance=3.5),
    "flux_kontext": dict(steps=20, guidance=2.5),
    "powerpaint": dict(steps=30, guidance=7.5),
    "sd15_inpaint": dict(steps=30, guidance=7.5),
    "sd2_inpaint": dict(steps=30, guidance=7.5),
}


def rel(path: Path | str) -> str:
    """Return a path relative to the project root when possible."""
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)

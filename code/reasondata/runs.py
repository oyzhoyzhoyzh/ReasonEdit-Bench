"""Discovery of editing runs on disk."""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .bench import read_jsonl


def list_runs(results_dir: Path | None = None) -> dict[str, Path]:
    """Map system name -> directory of generated images."""
    root = Path(results_dir or config.RESULTS)
    runs: dict[str, Path] = {}
    for manifest in sorted(root.glob("*/*/manifest.jsonl")):
        rel = manifest.parent.relative_to(root)
        model, variant = rel.parts[0], rel.parts[1]
        name = model if variant == "base" else f"{model}__{variant}"
        runs[name] = manifest.parent
    return runs


def outputs_of(run_dir: Path) -> dict[str, Path]:
    """item_id -> generated image path (last successful write wins)."""
    manifest = Path(run_dir) / "manifest.jsonl"
    out: dict[str, Path] = {}
    if not manifest.exists():
        return out
    for rec in read_jsonl(manifest):
        if rec.get("status") == "ok" and rec.get("output"):
            p = Path(rec["output"])
            if p.exists():
                out[rec["item_id"]] = p
    return out


def prompts_of(run_dir: Path) -> dict[str, str]:
    manifest = Path(run_dir) / "manifest.jsonl"
    out: dict[str, str] = {}
    if manifest.exists():
        for rec in read_jsonl(manifest):
            if rec.get("status") == "ok":
                out[rec["item_id"]] = rec.get("prompt", "")
    return out


SYSTEM_LABELS = {
    "instructpix2pix": "InstructPix2Pix",
    "qwen_image_edit": "Qwen-Image-Edit",
    "qwen_image_edit__cot": "Qwen-Image-Edit + CoT",
    "qwen_image_edit__oracle": "Qwen-Image-Edit + Oracle-SCM",
    "qwen_image_edit__scaffold": "Qwen-Image-Edit + CausalScaffold",
    "qwen_image_edit__scaffold_full": "Qwen-Image-Edit + CausalScaffold",
    "flux_fill": "FLUX.1-Fill",
    "flux_kontext": "FLUX.1-Kontext",
    "sd15_inpaint": "SD1.5-Inpaint",
    "sd2_inpaint": "SD2-Inpaint",
    "sdxl_inpaint": "SDXL-Inpaint",
}

#: the six systems reported in the paper; intermediate artefacts (per-shard oracle
#: directories, the partial repair directory) are excluded from every table
FINAL_SYSTEMS = [
    "instructpix2pix",
    "sdxl_inpaint",
    "qwen_image_edit",
    "qwen_image_edit__cot",
    "qwen_image_edit__oracle",
    "qwen_image_edit__scaffold_full",
    "flux_fill",
    "flux_kontext",
    "sd15_inpaint",
    "sd2_inpaint",
]


def label(name: str) -> str:
    return SYSTEM_LABELS.get(name, name)


#: Compact labels used by every table.  They are deliberately identical to
#: ``SYSTEM_LABELS`` so that one system carries one name everywhere in the
#: paper; the narrow single-column tables compensate with ``\scriptsize`` and a
#: tighter ``\tabcolsep`` instead of a second naming scheme.
SHORT_LABELS = {
    "instructpix2pix": "InstructPix2Pix",
    "qwen_image_edit": "Qwen-Image-Edit",
    "qwen_image_edit__cot": "Qwen-Image-Edit + CoT",
    "qwen_image_edit__oracle": "Qwen-Image-Edit + Oracle-SCM",
    "qwen_image_edit__scaffold": "Qwen-Image-Edit + CausalScaffold",
    "qwen_image_edit__scaffold_full": "Qwen-Image-Edit + CausalScaffold",
    "flux_fill": "FLUX.1-Fill",
    "flux_kontext": "FLUX.1-Kontext",
    "sd15_inpaint": "SD1.5-Inpaint",
    "sd2_inpaint": "SD2-Inpaint",
    "sdxl_inpaint": "SDXL-Inpaint",
}


def label_short(name: str) -> str:
    return SHORT_LABELS.get(name, name)

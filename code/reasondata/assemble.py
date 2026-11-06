"""Assemble the CausalScaffold system directory from its two passes."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from . import config
from .bench import read_jsonl, write_jsonl
from .runs import outputs_of


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", default=str(config.RESULTS / "qwen_image_edit" / "cot"))
    ap.add_argument("--repair", default=str(config.RESULTS / "qwen_image_edit" / "scaffold"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    first, repair = Path(args.first), Path(args.repair)
    out = Path(args.out) if args.out else (config.RESULTS / "qwen_image_edit" / "scaffold_full")
    out.mkdir(parents=True, exist_ok=True)

    first_out = outputs_of(first)
    repair_out = outputs_of(repair)
    manifest = []
    for item_id, src in sorted(first_out.items()):
        chosen = repair_out.get(item_id, src)
        dst = out / f"{item_id}.png"
        if not dst.exists():
            shutil.copyfile(chosen, dst)
        manifest.append({"item_id": item_id, "model": "qwen_image_edit", "variant": "scaffold",
                         "status": "ok", "output": str(dst),
                         "source": "repair" if item_id in repair_out else "first_pass",
                         "prompt": ""})
    write_jsonl(out / "manifest.jsonl", manifest)
    n_rep = sum(1 for m in manifest if m["source"] == "repair")
    print(f"assembled {len(manifest)} items ({n_rep} repaired) -> {out}")


if __name__ == "__main__":
    main()

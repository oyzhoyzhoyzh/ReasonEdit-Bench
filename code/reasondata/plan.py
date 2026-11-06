"""Self-generated reasoning plans used by the reasoning-augmented baselines.

For the ``cot`` and ``scaffold`` systems the editor is not given the instruction
alone: a vision-language model first writes down the causal consequences of the
requested intervention and the facts that must survive the edit.  This is the
training-free way of injecting reasoning into an off-the-shelf editor and is the
strongest baseline we can run without fine-tuning.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from . import config
from .bench import load_bench, read_jsonl, write_jsonl
from .vlm import DashScopeClient, LocalVLM, extract_json

PLAN_SYSTEM = (
    "You are an expert photo retoucher who reasons carefully before acting. You "
    "answer with strict JSON and never describe edits that are not asked for."
)

PLAN_PROMPT = """An image is attached. A user asks for this edit:

"{instruction}"

Before editing, work out how the request propagates through the scene.
Return JSON:
{{
  "plan": [
    {{"step": 1, "text": "short description of what must be done first"}},
    {{"step": 2, "text": "the consequence that must follow from it"}}
  ],
  "must_preserve": ["three short phrases naming what must stay exactly as it is"],
  "expected_effects": ["short phrases naming what must visibly change"],
  "risk": "the single most likely way this edit goes wrong"
}}
Keep at most four plan steps and never mention image editing software.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--backend", default="dashscope", choices=["local", "dashscope"])
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=900)
    args = ap.parse_args()

    out_path = Path(args.out or (config.RESULTS / f"plans_shard{args.shard.replace('/', 'of')}.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {r["item_id"]: r for r in read_jsonl(out_path)} if out_path.exists() else {}

    items = load_bench(args.bench)
    k, n = (int(x) for x in args.shard.split("/"))
    items = [it for i, it in enumerate(items) if i % n == k and it["id"] not in done]
    if args.limit:
        items = items[: args.limit]
    print(f"plans to write: {len(items)} -> {out_path}", flush=True)
    if not items:
        return

    if args.backend == "local":
        vlm = LocalVLM.get(args.model or config.MODELS["qwen3vl8b"], device=f"cuda:{args.gpu}")
    else:
        vlm = DashScopeClient(model=args.model or config.ANNOT_MODEL)

    def one(it: dict) -> dict:
        img = Image.open(config.BENCH_IMAGES / f"{it['image_id']}.jpg").convert("RGB")
        try:
            resp = vlm.chat(PLAN_PROMPT.format(instruction=it["instruction"]),
                            images=[img], system=PLAN_SYSTEM, temperature=0.0,
                            max_tokens=args.max_new_tokens)
            plan = extract_json(resp.text)
        except Exception as exc:  # noqa: BLE001
            plan = {"plan": [], "must_preserve": [], "error": str(exc)}
        return {"item_id": it["id"], **plan}

    fh = out_path.open("a")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(one, it): it for it in items}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                rec = {"item_id": futs[fut]["id"], "error": str(exc)}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 20 == 0:
                fh.flush()
                print(f"  {i}/{len(items)}", flush=True)
    fh.close()
    print("done", flush=True)


if __name__ == "__main__":
    main()

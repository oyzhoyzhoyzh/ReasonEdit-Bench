"""Three-stage annotation pipeline for ReasonEdit-Bench.

Stage 1  scene inventory      -- object-level parse of every candidate image
Stage 2  task proposal        -- instantiate taxonomy types grounded in stage 1
Stage 3  adversarial review   -- independent model checks the causal contract

All stages cache to JSONL so the pipeline can be resumed and so the ablation in
the paper (single-model vs. cross-verified annotation) can be reproduced.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from . import config
from .taxonomy import (
    SCENE_PROMPT,
    SCENE_SYSTEM,
    TASK_PROMPT,
    TASK_SYSTEM,
    type_specs_text,
)
from .vlm import DashScopeClient, extract_json


# --------------------------------------------------------------------------- #
# cache utilities
# --------------------------------------------------------------------------- #
def load_cache(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["_key"]] = rec
    return out


class JsonlCache:
    def __init__(self, path: Path):
        self.path = path
        self.data = load_cache(path)
        self.fh = path.open("a")

    def __contains__(self, key):
        return key in self.data

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value):
        rec = {"_key": key, **value}
        self.data[key] = rec
        self.fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.fh.flush()

    def close(self):
        self.fh.close()


def _load_image(path: Path, max_side: int = 1024) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if max(img.size) > max_side:
        s = max_side / max(img.size)
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                         Image.LANCZOS)
    return img


# --------------------------------------------------------------------------- #
# stage 1: scene inventory
# --------------------------------------------------------------------------- #
def inventory_one(client, record, images_dir: Path) -> dict:
    img = _load_image(images_dir / record["path"])
    hint = ""
    if record.get("source_meta", {}).get("objects"):
        objs = ", ".join(o["name"] for o in record["source_meta"]["objects"][:15])
        hint = f"\n(An independent segmentation annotator saw these classes: {objs}.)"
    resp = client.chat(SCENE_PROMPT + hint, images=[img], system=SCENE_SYSTEM,
                       temperature=0.1, max_tokens=3000)
    inv = extract_json(resp.text)
    inv["_model"] = resp.model
    return inv


def run_inventory(records, workers: int = 12, cache_name: str = "inventory.jsonl") -> dict:
    cache = JsonlCache(config.BENCH_DIR / cache_name)
    client = DashScopeClient()
    todo = [r for r in records if r["image_id"] not in cache]
    print(f"[inventory] {len(records) - len(todo)} cached, {len(todo)} to do", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(inventory_one, client, r, config.POOL_DIR / "images"): r
            for r in todo
        }
        for i, fut in enumerate(as_completed(futs), 1):
            rec = futs[fut]
            try:
                cache.put(rec["image_id"], {"inventory": fut.result()})
            except Exception as exc:  # noqa: BLE001
                cache.put(rec["image_id"], {"inventory": None, "error": str(exc)})
            if i % 25 == 0:
                print(f"[inventory] {i}/{len(todo)}", flush=True)
    cache.close()
    return {k: v.get("inventory") for k, v in cache.data.items()}


# --------------------------------------------------------------------------- #
# stage 2: task proposal
# --------------------------------------------------------------------------- #
def _inventory_text(inv: dict) -> str:
    lines = [
        f"caption: {inv.get('caption', '')}",
        f"scene_type: {inv.get('scene_type', '')}",
        f"time_of_day: {inv.get('time_of_day', '')}   weather: {inv.get('weather', '')}",
        f"lighting: {inv.get('lighting', '')}",
        "objects:",
    ]
    for o in inv.get("objects", []):
        attrs = ", ".join(f"{k}={v}" for k, v in (o.get("attributes") or {}).items()
                          if str(v).strip())
        lines.append(f"  - {o.get('name')} bbox={o.get('bbox')} ({attrs})")
    lines.append("relations: " + "; ".join(inv.get("relations", [])))
    return "\n".join(lines)


def propose_one(client, record, inv, images_dir: Path, type_key: str) -> dict:
    """Generate a single task of a requested type (one API call)."""
    from .taxonomy import type_specs_text

    img = _load_image(images_dir / record["path"])
    prompt = TASK_PROMPT.format(
        inventory=_inventory_text(inv), type_key=type_key,
        type_spec=type_specs_text([type_key]),
    )
    resp = client.chat(prompt, images=[img], system=TASK_SYSTEM, temperature=0.5,
                       max_tokens=2000)
    try:
        data = extract_json(resp.text)
    except Exception:  # noqa: BLE001 - usually a truncated reply; ask for a shorter one
        shorter = (prompt + "\n\nYour previous answer was cut off. Reply again with a "
                   "complete but much shorter JSON object: 3 chain steps, 2 effects, "
                   "2 preserved facts, at most 4 nodes.")
        resp = client.chat(shorter, images=[img], system=TASK_SYSTEM, temperature=0.3,
                           max_tokens=2000)
        data = extract_json(resp.text)
    if isinstance(data, dict) and data.get("tasks"):
        data = data["tasks"][0]
    task = dict(data)
    task["type"] = type_key
    task["image_id"] = record["image_id"]
    task["_generator"] = resp.model
    task["_requested_type"] = type_key
    return task


PROPOSER_MODELS = ["qwen3-vl-plus", "qwen3-vl-235b-a22b-instruct"]


def run_propose(records, inventories, workers: int = 8, n_per_image: int = 3,
                type_keys=None, cache_name: str = "tasks.jsonl",
                stratified: bool = True, models=None) -> list[dict]:
    """One API call per (image, requested type), spread over several model pools.

    Short outputs keep latency low, and dedicating one thread pool per model uses
    each model's concurrency quota independently.
    """
    from .taxonomy import TASK_TYPES

    cache = JsonlCache(config.BENCH_DIR / cache_name)
    models = models or PROPOSER_MODELS
    clients = {m: DashScopeClient(model=m) for m in models}
    all_keys = type_keys or list(TASK_TYPES)

    work = []
    for i, r in enumerate(records):
        if not inventories.get(r["image_id"]):
            continue
        offset = i % len(all_keys) if stratified else 0
        stride = max(1, len(all_keys) // max(1, n_per_image))
        for j in range(n_per_image):
            tk = all_keys[(offset + j * stride) % len(all_keys)]
            key = f"{r['image_id']}::{tk}"
            cached = cache.get(key)
            if cached is None or not cached.get("task"):
                work.append((key, r, tk))
    print(f"[propose] {len(work)} (image,type) calls -> {cache_name}", flush=True)
    if not work:
        cache.close()
        return [rec["task"] for rec in cache.data.values() if rec.get("task")]

    pools = {m: ThreadPoolExecutor(max_workers=workers) for m in models}
    fut_map = {}
    for idx, (key, r, tk) in enumerate(work):
        model = models[idx % len(models)]
        fut = pools[model].submit(propose_one, clients[model], r,
                                  inventories[r["image_id"]],
                                  config.POOL_DIR / "images", tk)
        fut_map[fut] = (key, r, tk, model)

    done, errs = 0, 0
    for fut in as_completed(fut_map):
        key, r, tk, model = fut_map[fut]
        try:
            task = fut.result()
        except Exception as exc:  # noqa: BLE001
            task, errs = None, errs + 1
            if errs <= 20:
                print(f"  propose failed {key}: {str(exc)[:110]}", flush=True)
        cache.put(key, {"task": task})
        done += 1
        if done % 50 == 0:
            print(f"[propose] {done}/{len(work)} (errors {errs})", flush=True)
    for pool in pools.values():
        pool.shutdown()
    cache.close()
    return [rec["task"] for rec in cache.data.values() if rec.get("task")]




# --------------------------------------------------------------------------- #
# stage 3: adversarial review
# --------------------------------------------------------------------------- #
REVIEW_SYSTEM = (
    "You are a skeptical reviewer of an image-editing benchmark. You reject any "
    "annotation whose causal reasoning does not hold. Answers are strict JSON."
)

REVIEW_PROMPT = """Below is one candidate benchmark item: an image, an editing
instruction, an object-level causal graph, a reasoning chain and verification
probes.

INSTRUCTION
{instruction}

CAUSAL GRAPH
{graph}

REASONING CHAIN
{chain}

REQUIRED EFFECTS (each must be true of a correct edit)
{effects}

PRESERVED FACTS (each must still hold after a correct edit)
{preserved}

COUNTERFACTUAL (a plausible but causally wrong edit)
{counterfactual}

Judge the annotation itself, not the image quality. Answer:
{{
  "reasoning_required": true/false,   // is the instruction impossible to satisfy by a
                                      // purely surface-level copy/paste edit?
  "intervention_visible": true/false, // is the intervention variable really in the image?
  "effects_valid": true/false,        // is every required effect a genuine consequence?
  "effects_checkable": true/false,    // can each probe be answered from the edited image
                                      // alone, without seeing the original?
  "preserved_valid": true/false,      // are the preserved facts really unaffected by a
                                      // correct edit?
  "counterfactual_valid": true/false, // does the counterfactual really violate the graph?
  "leak": true/false,                 // does any probe simply repeat the instruction?
  "hardest_flaw": "the single most serious problem, or 'none'",
  "confidence": 0.0-1.0
}}
Reply with JSON only.
"""


def _fmt_graph(item: dict) -> str:
    nodes = "; ".join(f"{n['id']}={n['label']}" for n in item["scm"]["nodes"])
    edges = "; ".join(f"{e['src']}->{e['dst']} ({e['relation']})" for e in item["scm"]["edges"])
    iv = item["scm"]["intervention"]
    return f"nodes: {nodes}\nedges: {edges}\ndo({iv['node']}: {iv['variable']} {iv['from']} -> {iv['to']})"


def review_one(client, item, images_dir: Path, record) -> dict:
    img = _load_image(images_dir / record["path"])
    prompt = REVIEW_PROMPT.format(
        instruction=item["instruction"],
        graph=_fmt_graph(item),
        chain="\n".join(f"{s['step']}. {s['thought']}" for s in item["reasoning_chain"]),
        effects="\n".join(f"- {e['probe']}" for e in item["effects"]),
        preserved="\n".join(f"- {p['probe']}" for p in item["preserved"]),
        counterfactual=(item["counterfactual"]["instruction"] + " | reason: "
                        + item["counterfactual"]["reason"]),
    )
    resp = client.chat(prompt, images=[img], system=REVIEW_SYSTEM, temperature=0.0,
                       max_tokens=1200)
    verdict = extract_json(resp.text)
    verdict["_reviewer"] = resp.model
    return verdict


REVIEWER_MODELS = ["qwen3-vl-235b-a22b-instruct", "qwen3-vl-plus"]


def run_review(items, records_by_id, workers: int = 8,
               cache_name: str = "reviews.jsonl", models=None) -> dict:
    cache = JsonlCache(config.BENCH_DIR / cache_name)
    models = models or REVIEWER_MODELS
    clients = {m: DashScopeClient(model=m) for m in models}
    def _bad(it):
        rec = cache.get(it["id"])
        if rec is None:
            return True
        return "error" in (rec.get("verdict") or {})

    todo = [it for it in items if _bad(it)]
    print(f"[review] {len(todo)} items to review", flush=True)
    if not todo:
        cache.close()
        return {k: v.get("verdict") for k, v in cache.data.items()}

    pools = {m: ThreadPoolExecutor(max_workers=workers) for m in models}
    fut_map = {}
    for idx, it in enumerate(todo):
        model = models[idx % len(models)]
        fut = pools[model].submit(review_one, clients[model], it,
                                  config.POOL_DIR / "images",
                                  records_by_id[it["image_id"]])
        fut_map[fut] = it
    done = 0
    for fut in as_completed(fut_map):
        it = fut_map[fut]
        try:
            v = fut.result()
        except Exception as exc:  # noqa: BLE001
            v = {"error": str(exc)}
        cache.put(it["id"], {"verdict": v})
        done += 1
        if done % 25 == 0:
            print(f"[review] {done}/{len(todo)}", flush=True)
    for pool in pools.values():
        pool.shutdown()
    cache.close()
    return {k: v.get("verdict") for k, v in cache.data.items()}

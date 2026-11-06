"""Driver for the ReasonEdit-Bench construction pipeline."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from . import config
from .annotate import run_inventory, run_propose, run_review
from .bench import read_jsonl, write_jsonl
from .taxonomy import TASK_TYPES, graph_stats, normalize_task, score_difficulty


def load_pool(limit: int | None = None, seed: int = config.SEED) -> list[dict]:
    recs = read_jsonl(config.POOL_DIR / "index.jsonl")
    rng = random.Random(seed)
    rng.shuffle(recs)
    return recs[:limit] if limit else recs


REQUIRED_FLAGS = [
    "reasoning_required", "intervention_visible", "effects_valid",
    "effects_checkable", "preserved_valid", "counterfactual_valid",
]


def verdict_ok(v: dict | None) -> tuple[bool, str]:
    if not v or "error" in v:
        return False, "review_error"
    for f in REQUIRED_FLAGS:
        if v.get(f) is not True:
            return False, f
    if v.get("leak") is True:
        return False, "leak"
    if float(v.get("confidence", 0)) < 0.6:
        return False, "low_confidence"
    return True, "ok"


def finalize(raw_tasks, reviews, pool_by_id, target_per_type: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_type: dict[str, list[dict]] = defaultdict(list)
    rejects: Counter = Counter()
    for t in raw_tasks:
        iid = t.get("image_id")
        rec = pool_by_id.get(iid)
        if rec is None:
            continue
        try:
            item = normalize_task(t, iid)
        except Exception as exc:  # noqa: BLE001
            rejects[f"schema:{type(exc).__name__}"] += 1
            continue
        ok, why = verdict_ok(reviews.get(item["id"]))
        if not ok:
            rejects[f"review:{why}"] += 1
            continue
        stats = graph_stats(item)
        item["meta"] = {**stats, "difficulty": score_difficulty(item),
                        "review": reviews[item["id"]]}
        item["source"] = {"dataset": rec["origin"], "path": rec["path"]}
        by_type[item["type"]].append(item)

    selected: list[dict] = []
    used_images: Counter = Counter()
    # round-robin across types so rare types are not crowded out
    order = sorted(by_type, key=lambda k: len(by_type[k]))
    for k in order:
        rng.shuffle(by_type[k])
    quota = {k: min(target_per_type, len(by_type[k])) for k in order}
    taken: Counter = Counter()
    while any(taken[k] < quota[k] for k in order):
        for k in order:
            if taken[k] >= quota[k]:
                continue
            # prefer items whose source image has not been used yet
            pick = 0
            for j in range(len(by_type[k])):
                cand = by_type[k][j]
                if used_images[cand["image_id"]] == 0:
                    pick = j
                    break
            item = by_type[k].pop(pick)
            used_images[item["image_id"]] += 1
            taken[k] += 1
            selected.append(item)
    for i, it in enumerate(sorted(selected, key=lambda x: (x["type"], x["image_id"]))):
        it["sid"] = f"REB{i:04d}"
    return selected, rejects


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-limit", type=int, default=900)
    ap.add_argument("--tasks-per-image", type=int, default=3)
    ap.add_argument("--per-type", type=int, default=34)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cache-tag", default="", help="suffix for cache files")
    ap.add_argument("--out", default="bench.jsonl")
    ap.add_argument("--dev-size", type=int, default=18)
    args = ap.parse_args()

    pool = load_pool(args.pool_limit)
    print(f"pool: {len(pool)} images", flush=True)

    tag = args.cache_tag
    inv = run_inventory(pool, workers=args.workers,
                        cache_name=f"inventory{tag}.jsonl")
    pool_with_inv = [r for r in pool if inv.get(r["image_id"])]
    print(f"inventoried: {len(pool_with_inv)}", flush=True)

    raw = run_propose(pool_with_inv, inv, workers=args.workers,
                      n_per_image=args.tasks_per_image, cache_name=f"tasks{tag}.jsonl")
    print(f"raw proposals: {len(raw)}", flush=True)

    pool_by_id = {r["image_id"]: r for r in pool}
    # normalise first so review sees ids
    staged = []
    for t in raw:
        try:
            staged.append(normalize_task(t, t["image_id"]))
        except Exception:  # noqa: BLE001
            continue
    reviews = run_review(staged, pool_by_id, workers=args.workers,
                         cache_name=f"reviews{tag}.jsonl")

    selected, rejects = finalize(raw, reviews, pool_by_id, args.per_type, config.SEED)
    print(f"selected {len(selected)} items; rejects: {dict(rejects.most_common(12))}")

    config.BENCH_IMAGES.mkdir(parents=True, exist_ok=True)
    for it in selected:
        src = config.POOL_DIR / "images" / pool_by_id[it["image_id"]]["path"]
        dst = config.BENCH_IMAGES / f"{it['image_id']}.jpg"
        if not dst.exists():
            shutil.copyfile(src, dst)
    write_jsonl(config.BENCH_DIR / args.out, selected)

    # a small dev split for pipeline debugging
    rng = random.Random(config.SEED)
    strat = defaultdict(list)
    for it in selected:
        strat[it["type"]].append(it)
    dev = []
    for k, v in strat.items():
        dev += v[: max(1, args.dev_size // max(1, len(strat)))]
    rng.shuffle(dev)
    write_jsonl(config.BENCH_DIR / "bench_dev.jsonl", dev[: args.dev_size])

    stats = {
        "n": len(selected),
        "by_type": dict(Counter(i["type"] for i in selected)),
        "by_domain": dict(Counter(i["domain"] for i in selected)),
        "by_difficulty": dict(Counter(i["meta"]["difficulty"] for i in selected)),
        "by_dataset": dict(Counter(i["source"]["dataset"] for i in selected)),
        "rejects": dict(rejects),
        "avg_chain": sum(i["meta"]["chain_length"] for i in selected) / max(1, len(selected)),
        "avg_effects": sum(i["meta"]["num_effects"] for i in selected) / max(1, len(selected)),
        "avg_nodes": sum(i["meta"]["num_nodes"] for i in selected) / max(1, len(selected)),
        "avg_depth": sum(i["meta"]["depth"] for i in selected) / max(1, len(selected)),
    }
    (config.BENCH_DIR / "stats.json").write_text(json.dumps(stats, indent=2,
                                                            ensure_ascii=False))
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

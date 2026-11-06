"""Build the surface-edit control subset.

Proposal expectation (5.6) is that reasoning-based edits are much harder than surface
edits, but the benchmark alone cannot show that: it contains no surface items.  This
module generates one surface analogue per reasoning item, **on the same source image and
targeting the same object**, so the two conditions differ in one thing only -- whether the
consequences of the change have to be inferred or are simply stated.

A surface item reuses everything that is already valid for the image:

* the preserved set is copied verbatim from the reasoning item, so preservation is scored
  on exactly the same propositions on both sides of the comparison;
* a drafting model (given the image and the object the reasoning edit acts on) writes an
  instruction that names a directly visible appearance change, plus two probes that
  restate it;
* an adversarial reviewer checks that the item really is solvable by a surface edit, that
  the effects require no inference, and that no preserved fact refers to the object being
  changed.

    python -m reasondata.surface --workers 12 --out surface.jsonl
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

from . import config
from .annotate import JsonlCache, _load_image
from .bench import read_jsonl, write_jsonl
from .vlm import DashScopeClient, extract_json

SURFACE_SYSTEM = (
    "You annotate a control condition for an image-editing benchmark. The control item "
    "must be solvable by a direct, surface-level appearance change that a person could "
    "carry out without inferring anything: recolouring, restyling, replacing an object "
    "with another of the same category, resizing, adding or removing one object. The "
    "instruction must name the outcome itself and must not imply any consequence "
    "elsewhere in the scene. Answer with strict JSON."
)

SURFACE_PROMPT = """Look at the photograph. A reasoning benchmark item on this image edits
the {label} (box {region} on a 0-1000 scale), casting its edit as a cause whose
consequences must be inferred. We need a SURFACE CONTROL on the same image and the same
object: an edit whose result is stated outright.

Scene: {caption}
Target object: {label}

Write one surface edit and its verification probes:
{{
  "instruction": "at most 20 words, names the visible change directly, for example
                  'Recolour the ceramic lamp base to deep blue' or 'Replace the wooden
                  stool with a metal one'. No 'so that', no consequences, no reasoning.",
  "variable": "the attribute being changed, one word (colour, material, size, pose, ...)",
  "from": "its state before, at most 4 words",
  "to": "its state after, at most 4 words",
  "effects": [
    {{"statement": "the stated change, restated as a fact",
      "probe": "a yes/no question that checks exactly what the instruction asked",
      "region": [x1, y1, x2, y2] on a 0-1000 scale}}
  ]
}}

Rules:
- exactly 2 effects. Every probe must be answerable by looking at the edited image alone
  and must check only what the instruction literally asked for.
- The region must be the box of the object that changes, on the 0-1000 scale.
- Do not mention any other object, the lighting, shadows or the background.
Reply with JSON only.
"""

REVIEW_SYSTEM = (
    "You are a skeptical reviewer of an image-editing benchmark control condition. You "
    "reject any item that is not a genuine surface edit. Answers are strict JSON."
)

REVIEW_PROMPT = """A control item on the attached photograph should be solvable by a
direct appearance change, with no inference about consequences.

INSTRUCTION
{instruction}

REQUIRED EFFECTS (each must hold of a correct edit)
{effects}

PRESERVED FACTS (each must still hold after the correct edit)
{preserved}

Answer:
{{
  "surface_solvable": true/false,   // can this be done by a direct appearance change?
  "target_visible": true/false,     // is the object to be changed really in the image?
  "effects_stated": true/false,     // does every probe merely restate the instruction,
                                    // with nothing that has to be inferred?
  "preserved_clear": true/false,    // do all preserved facts hold on the source image and
                                    // avoid the object being changed?
  "hardest_flaw": "the single most serious problem, or 'none'",
  "confidence": 0.0-1.0
}}
Reply with JSON only.
"""


def _region_of(item: dict) -> tuple[str, list | None]:
    iv = item["scm"]["intervention"]
    node = next((n for n in item["scm"]["nodes"] if n["id"] == iv["node"]), None)
    return (node or {}).get("label", iv["node"]), (node or {}).get("region")


def draft_one(client, item: dict, caption: str, image: Image.Image) -> dict:
    label, region = _region_of(item)
    prompt = SURFACE_PROMPT.format(label=label, region=region or "unknown",
                                   caption=caption or "(none)")
    resp = client.chat(prompt, images=[image], system=SURFACE_SYSTEM,
                       temperature=0.4, max_tokens=1200)
    data = extract_json(resp.text)
    data["_drafter"] = resp.model
    return data


def build_item(item: dict, draft: dict, verdict: dict) -> dict | None:
    """Assemble a surface item in the benchmark's schema, or None if unusable."""
    eff = draft.get("effects") or []
    if not draft.get("instruction") or not eff:
        return None
    label, region = _region_of(item)
    effects = []
    for i, e in enumerate(eff[:3], 1):
        if not e.get("probe"):
            continue
        effects.append({
            "id": f"e{i}", "statement": str(e.get("statement") or e["probe"]),
            "probe": str(e["probe"]), "region": e.get("region") or region,
            "ordinal": i, "is_descendant": True,
        })
    if not effects:
        return None
    return {
        "id": f"{item['id']}_surface", "image_id": item["image_id"],
        "domain": "surface", "type": "surface",
        "instruction": str(draft["instruction"]).strip(),
        "scm": {
            "nodes": [{"id": "n1", "label": label, "kind": "object", "region": region,
                       "state_before": str(draft.get("from", ""))[:40]}],
            "edges": [],
            "intervention": {"node": "n1",
                             "variable": str(draft.get("variable", "appearance")),
                             "from": str(draft.get("from", ""))[:40],
                             "to": str(draft.get("to", ""))[:40]},
        },
        "reasoning_chain": [{"step": 1, "region": region,
                             "thought": f"Directly render the requested change to the "
                                        f"{label}; nothing else follows from it."}],
        "effects": effects,
        # verbatim, so preservation is scored on identical propositions on both sides
        "preserved": item["preserved"],
        "counterfactual": {"instruction": "", "violated_edge": "", "reason": ""},
        "descendants": ["n1"],
        "meta": {"num_nodes": 1, "num_edges": 1, "depth": 1, "chain_length": 1,
                 "num_effects": len(effects), "difficulty": "easy",
                 "source_type": item["type"], "paired_with": item["id"]},
        "_draft": draft, "_review": verdict,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--out", default="surface.jsonl")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    items = read_jsonl(config.BENCH_DIR / args.bench)
    if args.limit:
        items = items[: args.limit]
    inv = {}
    for name in ("inventory_full.jsonl", "inventory.jsonl"):
        p = config.BENCH_DIR / name
        if p.exists():
            for rec in read_jsonl(p):
                inv.setdefault(rec["_key"], rec.get("inventory") or {})

    draft_cache = JsonlCache(config.BENCH_DIR / "surface_drafts.jsonl")
    review_cache = JsonlCache(config.BENCH_DIR / "surface_reviews.jsonl")
    client = DashScopeClient()

    todo = [it for it in items
            if it["id"] not in draft_cache or it["id"] not in review_cache]
    print(f"[surface] {len(items) - len(todo)} cached, {len(todo)} to annotate", flush=True)

    def one(it):
        img = _load_image(config.BENCH_IMAGES / f"{it['image_id']}.jpg")
        caption = (inv.get(it["image_id"]) or {}).get("caption", "")
        if it["id"] not in draft_cache:
            draft_cache.put(it["id"], {"draft": draft_one(client, it, caption, img)})
        draft = draft_cache.get(it["id"])["draft"]
        if it["id"] not in review_cache:
            prompt = REVIEW_PROMPT.format(
                instruction=draft.get("instruction", ""),
                effects="\n".join(f"- {e.get('probe')}" for e in draft.get("effects", [])),
                preserved="\n".join(f"- {p['probe']}" for p in it["preserved"]),
            )
            resp = client.chat(prompt, images=[img], system=REVIEW_SYSTEM,
                               temperature=0.0, max_tokens=800)
            review_cache.put(it["id"], {"verdict": extract_json(resp.text)})
        return it["id"]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(one, it) for it in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  failed: {exc}", flush=True)
            if i % 25 == 0:
                print(f"[surface] {i}/{len(todo)}", flush=True)
    draft_cache.close()
    review_cache.close()

    out, rejects = [], {}
    for it in items:
        d = (draft_cache.get(it["id"]) or {}).get("draft")
        v = (review_cache.get(it["id"]) or {}).get("verdict") or {}
        if not d or "error" in v:
            rejects["draft_or_review_error"] = rejects.get("draft_or_review_error", 0) + 1
            continue
        bad = None
        for flag in ("surface_solvable", "target_visible", "effects_stated",
                     "preserved_clear"):
            if v.get(flag) is not True:
                bad = flag
                break
        if bad:
            rejects[bad] = rejects.get(bad, 0) + 1
            continue
        if float(v.get("confidence", 0)) < 0.6:
            rejects["low_confidence"] = rejects.get("low_confidence", 0) + 1
            continue
        rec = build_item(it, d, v)
        if rec:
            out.append(rec)
        else:
            rejects["schema"] = rejects.get("schema", 0) + 1

    write_jsonl(config.BENCH_DIR / args.out, out)
    stats = {"n": len(out), "rejects": rejects,
             "by_source_type": {t: sum(1 for r in out if r["meta"]["source_type"] == t)
                                for t in sorted({r["meta"]["source_type"] for r in out})}}
    (config.BENCH_DIR / "surface_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"[surface] kept {len(out)}/{len(items)} -> {config.BENCH_DIR / args.out}",
          flush=True)
    print(json.dumps(rejects, indent=2), flush=True)


if __name__ == "__main__":
    main()

# ReasonEdit-Bench

324 reasoning-based image-editing tasks, 36 in each of nine types
(physical / social / functional commonsense; single-cause / multi-cause /
counterfactual causal; ordered-sequential / conditional / long-horizon multi-step).

## Files

* `bench.jsonl` -- one JSON object per task (schema below).
* `bench_dev.jsonl` -- a small stratified split for pipeline debugging.
* `images/<image_id>.jpg` -- the source photographs (`image_id` is the stem).
* `stats.json` -- composition of the released set and the outcome of the last
  construction run (how many drafts were rejected and why).
* `inventory_full.jsonl`, `tasks_full.jsonl`, `reviews_full.jsonl` -- the raw caches
  of the three annotation stages, so every acceptance decision can be traced.
* `surface.jsonl`, `surface_reviews.jsonl`, `surface_stats.json` -- the surface-edit
  control: one no-reasoning counterpart for each reasoning item, built on the same
  photograph and target object, with its own review records and counts.

## Item schema

| field | meaning |
| --- | --- |
| `id` | `<image_id>_<type>` |
| `domain`, `type` | taxonomy labels (3 domains, 9 types) |
| `instruction` | the user instruction; it names the intervention and no consequence |
| `scm.nodes` | objects / attributes / events with a grounding box on a 0-1000 scale |
| `scm.edges` | `causes` / `enables` / `allows` / `prevents` relations with a mechanism |
| `scm.intervention` | `do(node.variable = value)` with the observed `from` state |
| `reasoning_chain` | the steps a model must take, each with the region it concerns |
| `effects` | propositions that must hold of a correct edit, each with a probe question and an `ordinal` |
| `preserved` | non-descendant facts that must survive, each with a probe question |
| `counterfactual` | a plausible but causally invalid edit of the same image |
| `descendants` | node ids reachable from the intervention in `scm` |
| `meta` | graph/chain statistics and the deterministic difficulty label |

Probe questions are written so that **yes** means "the contract is honoured". All
regions are integer boxes relative to the image size (0-1000).

## How it was built

Source images are MagicBrush photographs and ADE20K scenes (162 each). Three
annotation stages are recorded verbatim in the cache files: a scene inventory, a
type-conditioned task draft (two models, round-robin type assignment) and an
adversarial review by two stronger models that tries to falsify each annotation.
Only items passing every review check with confidence >= 0.6 are kept; see
`stats.json` for the acceptance counts.

## Licence and intended use

The annotations are released for research. Source photographs keep the licensing of
MagicBrush (COCO-derived) and ADE20K; images are included at reduced resolution
(long side <= 1024) for evaluation convenience.

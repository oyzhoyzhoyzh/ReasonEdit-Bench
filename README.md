# ReasonEdit-Bench

Code, benchmark and raw judge verdicts for **The Causal Contract of Reasoning-Based
Image Editing: A Benchmark and Failure Diagnosis**.

ReasonEdit-Bench contains 324 reasoning-based image-editing tasks. Each task pairs a
photograph with an instruction that names a *cause* and leaves its consequences
implicit, and is annotated with an object-level structural causal model, a grounded
reasoning chain, the descendant effects that must appear, the non-descendant facts that
must survive, and a causally invalid counterfactual. Correctness is checked without any
reference image: every proposition is verified on the region it is about, one yes/no
question at a time.

## What is in this repository

| Path | Contents |
| --- | --- |
| `code/reasondata/` | Python package; every entry point is `python -m reasondata.<module>` |
| `scripts/` | staged drivers for the full experiment (annotation → generation → probing → analysis) |
| `data/ReasonEdit-Bench/` | `bench.jsonl` (324 items), `images/` (421 photographs), the three annotation caches, the surface control, and `stats.json` |
| `results/analysis*/` | per-item scores, summaries and derived tables for every experiment in the paper |
| `results/probes_*.jsonl` | the raw judge verdicts (29 shards, 103,358 verdicts) behind those scores |
| `results/human_eval/` | the exploratory human audit records |
| `requirements.txt` | Python dependencies |

Not included, because they are reproducible or too large: generated images (~4 GB),
model checkpoints, and the paper sources (they live with the manuscript).

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Generation and judging need a GPU and local checkpoints; the analysis path below does
not.

## Quick start: recompute every table without a GPU

Every number in the paper follows from the released verdict files.

```bash
export RIE_ROOT=$PWD
bash scripts/refresh_all.sh
```

This writes `results/analysis/` (per-item scores, statistics), `results/figures/`
(figures) and `results/tables/` (LaTeX tables). Runtime is minutes on a CPU; no model
is loaded.

## Reproducing from scratch

The full pipeline is split into phases, each resumable and each driven by a script:

```bash
# 1. annotation: scene inventory -> task draft -> adversarial review -> selection
python3 -m reasondata.build_bench --stage all

# 2. generation for each condition (one script per phase)
bash scripts/phase1_generate.sh        # InstructPix2Pix, SDXL-Inpaint, Qwen-Image-Edit
bash scripts/phase3_scaffold.sh        # CausalScaffold: verify, then re-edit
bash scripts/phase7_extra_baselines.sh # SD1.5 / SD2 / FLUX.1-Fill

# 3. region-grounded probing (needs a judge; API or local)
bash scripts/phase2_judge.sh

# 4. analysis
bash scripts/refresh_all.sh
```

## Configuration

All paths and model locations are environment variables, so the package runs from any
checkout:

| Variable | Default | Meaning |
| --- | --- | --- |
| `RIE_ROOT` | the repository root | where `code/`, `data/`, `results/` live |
| `RIE_HF_CACHE` | `<root>/models` | local checkpoint cache (`.../Qwen/Qwen3-VL-8B-Instruct`, …) |
| `RIE_RAW_DATA` | `<root>/data/raw` | source datasets, only needed to rebuild the benchmark |
| `RIE_GEDIT_DIR` | `<root>/data/raw/GEdit-Bench` | GEdit-Bench copy for the cross-benchmark study |
| `DASHSCOPE_API_KEY` | empty | key for the hosted judge; unset it to run fully offline |
| `DASHSCOPE_BASE_URL` | DashScope compatible-mode URL | override for another OpenAI-compatible endpoint |

## The benchmark

`data/ReasonEdit-Bench/README.md` documents the item schema field by field: the SCM
nodes and edges, the intervention, the reasoning chain, the effect and preservation
propositions with their probe questions and 0–1000 regions, and the counterfactual.
Probe questions are phrased so that **yes** means the contract is honoured.

## Citing

```bibtex
@article{ouyang2026causal,
  title   = {The Causal Contract of Reasoning-Based Image Editing:
             A Benchmark and Failure Diagnosis},
  author  = {Ouyang, Zhouhao and Wu, Si},
  year    = {2026}
}
```

## Licence

Code and annotations are released for research use. The source photographs keep the
licences of MagicBrush (COCO-derived) and ADE20K; see
`data/ReasonEdit-Bench/README.md`.

## Contact

Zhouhao Ouyang — oyzh@cvresearch.work

"""Statistical report for the Qwen-Image-Edit multi-seed validation.

The input contains four inference-time conditions for each random seed:
base, CoT, Oracle-SCM, and the assembled CausalScaffold.  The report keeps
generation variance and judge repeat variability separate:

* seed effects are estimated after removing item effects;
* item × seed residual variance is the generation interaction;
* a repeated judge run supplies an item-clustered judge-error estimate.

Usage::

    python -m reasondata.qwen_multiseed_report \
        --scores results/analysis_qwen_multiseed/scores.jsonl \
        --out results/analysis/qwen_multiseed.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau, spearmanr

from .bench import read_jsonl

CONDITIONS = ("base", "cot", "oracle", "scaffold_full")
METRICS = ("tcs", "dps", "nps", "ccs", "strict_success")


def parse_system(system: str) -> tuple[int, str]:
    match = re.fullmatch(r"qwen_multiseed_s(\d+)(?:__(cot|oracle|scaffold_full))?", system)
    if not match:
        raise ValueError(f"unexpected system name: {system}")
    return int(match.group(1)), match.group(2) or "base"


def bootstrap_mean(values: list[float], n_boot: int = 5000,
                   seed: int = 20261104) -> tuple[float, float]:
    rng = random.Random(seed)
    vals = np.asarray(values, dtype=float)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = vals[np.fromiter(
            (rng.randrange(len(vals)) for _ in range(len(vals))),
            dtype=np.int64, count=len(vals)
        )].mean()
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def clustered_bootstrap(by_seed_item: dict[int, dict[str, float]],
                        n_boot: int = 5000, seed: int = 20261104) -> tuple[float, float]:
    """Bootstrap whole items while retaining all seeds within a sampled item."""
    seeds = sorted(by_seed_item)
    items = sorted(set.intersection(*(set(by_seed_item[s]) for s in seeds)))
    item_values = np.asarray([
        np.mean([by_seed_item[s][i] for s in seeds]) for i in items
    ], dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(items), size=(n_boot, len(items)))
    means = item_values[indices].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def two_way_variance(by_seed_item: dict[int, dict[str, float]]) -> dict:
    """Random-effects decomposition for a balanced item × seed design."""
    seeds = sorted(by_seed_item)
    items = sorted(set.intersection(*(set(by_seed_item[s]) for s in seeds)))
    y = np.array([[by_seed_item[s][i] for s in seeds] for i in items], dtype=float)
    n, m = y.shape
    grand = y.mean()
    ss_item = m * ((y.mean(axis=1) - grand) ** 2).sum()
    ss_seed = n * ((y.mean(axis=0) - grand) ** 2).sum()
    ss_error = ((y - y.mean(axis=1, keepdims=True)
                 - y.mean(axis=0, keepdims=True) + grand) ** 2).sum()
    ms_item = ss_item / max(1, n - 1)
    ms_seed = ss_seed / max(1, m - 1)
    ms_error = ss_error / max(1, (n - 1) * (m - 1))
    return {
        "n_items": n,
        "n_seeds": m,
        "item_variance": max(0.0, (ms_item - ms_error) / m),
        "seed_variance": max(0.0, (ms_seed - ms_error) / n),
        "item_x_seed_residual_variance": max(0.0, ms_error),
        "item_x_seed_residual_sd": math.sqrt(max(0.0, ms_error)),
    }


def exact_seed_order(condition_means: dict[str, dict[int, float]],
                     seed: int) -> list[str]:
    return sorted(CONDITIONS, key=lambda c: (-condition_means[c][seed], c))


def load_repeat_scores(path: Path | None) -> dict[tuple[str, str], float]:
    if not path or not path.exists():
        return {}
    return {(r["system"], r["item_id"]): float(r["ccs"])
            for r in read_jsonl(path)}


def compare_probe_verdicts(paths: list[Path], repeat_paths: list[Path]) -> dict:
    def load(path_list: list[Path]) -> dict[str, str]:
        out = {}
        for path in path_list:
            if path.exists():
                for rec in read_jsonl(path):
                    out[rec["pid"]] = rec.get("answer", "unclear")
        return out

    original, repeat = load(paths), load(repeat_paths)
    common = sorted(set(original) & set(repeat))
    if not common:
        return {}
    agree = sum(original[p] == repeat[p] for p in common) / len(common)
    from sklearn.metrics import cohen_kappa_score

    return {
        "n_verdicts": len(common),
        "exact_agreement": agree,
        "cohen_kappa": float(cohen_kappa_score(
            [original[p] for p in common], [repeat[p] for p in common]
        )),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True)
    ap.add_argument("--repeat-scores", default=None)
    ap.add_argument("--probes", default=None,
                    help="comma-separated original probe files")
    ap.add_argument("--repeat-probes", default=None,
                    help="comma-separated repeated-judge probe files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-boot", type=int, default=5000)
    args = ap.parse_args()

    rows = read_jsonl(Path(args.scores))
    table: dict[tuple[int, str], dict[str, dict]] = {}
    for row in rows:
        seed, condition = parse_system(row["system"])
        table.setdefault((seed, condition), {})[row["item_id"]] = row
    seeds = sorted({s for s, _ in table})
    if len(seeds) < 3:
        raise SystemExit(f"need at least three seeds, found {seeds}")
    missing = [(s, c) for s in seeds for c in CONDITIONS if (s, c) not in table]
    if missing:
        raise SystemExit(f"missing complete condition runs: {missing}")

    item_sets = {
        (s, c): set(table[(s, c)]) for s in seeds for c in CONDITIONS
    }
    common_items = set.intersection(*(item_sets[k] for k in item_sets))
    if not common_items:
        raise SystemExit("no common items across conditions and seeds")

    by_condition: dict[str, dict[str, dict[int, dict[str, float]]]] = {
        c: {metric: defaultdict(dict) for metric in METRICS} for c in CONDITIONS
    }
    for (seed, condition), records in table.items():
        for item_id, rec in records.items():
            if item_id not in common_items:
                continue
            for metric in METRICS:
                by_condition[condition][metric][seed][item_id] = float(rec[metric])

    condition_means = {c: {} for c in CONDITIONS}
    metrics_out: dict = {}
    for condition in CONDITIONS:
        metrics_out[condition] = {}
        for metric in METRICS:
            by_seed = {s: by_condition[condition][metric][s] for s in seeds}
            seed_means = {str(s): st.mean(by_seed[s].values()) for s in seeds}
            vals = list(seed_means.values())
            lo, hi = clustered_bootstrap(by_seed, args.n_boot,
                                         seed=20261104 + len(condition) + len(metric))
            item_spreads = [
                max(by_seed[s][i] for s in seeds) - min(by_seed[s][i] for s in seeds)
                for i in sorted(common_items)
            ]
            metrics_out[condition][metric] = {
                "seed_means": seed_means,
                "mean": st.mean(vals),
                "std_across_seeds_population": st.pstdev(vals),
                "std_across_seeds_sample": st.stdev(vals),
                "range_across_seeds": max(vals) - min(vals),
                "ci95_item_clustered": [lo, hi],
                "mean_item_spread": st.mean(item_spreads),
                "p95_item_spread": float(np.quantile(item_spreads, 0.95)),
                "variance_components": two_way_variance(by_seed),
            }
        condition_means[condition] = {
            s: metrics_out[condition]["ccs"]["seed_means"][str(s)]
            for s in seeds
        }

    orders = {str(s): exact_seed_order(condition_means, s) for s in seeds}
    pairs = []
    for i, a in enumerate(seeds):
        for b in seeds[i + 1:]:
            va = np.array([condition_means[c][a] for c in CONDITIONS])
            vb = np.array([condition_means[c][b] for c in CONDITIONS])
            tau = float(kendalltau(va, vb).statistic)
            pairs.append({
                "seed_a": str(a), "seed_b": str(b),
                "kendall_tau": tau,
                "identical_order": orders[str(a)] == orders[str(b)],
            })

    pairwise_rho = {}
    for condition in CONDITIONS:
        vals = []
        for i, a in enumerate(seeds):
            for b in seeds[i + 1:]:
                x = [by_condition[condition]["ccs"][a][it] for it in sorted(common_items)]
                y = [by_condition[condition]["ccs"][b][it] for it in sorted(common_items)]
                vals.append({
                    "seed_a": str(a), "seed_b": str(b),
                    "spearman": float(spearmanr(x, y).statistic),
                })
        pairwise_rho[condition] = vals

    contrasts = {}
    for left, right in (
        ("cot", "base"),
        ("oracle", "base"),
        ("scaffold_full", "cot"),
        ("scaffold_full", "base"),
    ):
        key = f"{left}_minus_{right}"
        contrasts[key] = {}
        for metric in METRICS:
            seed_deltas = {}
            for seed in seeds:
                paired = [
                    by_condition[left][metric][seed][item]
                    - by_condition[right][metric][seed][item]
                    for item in sorted(common_items)
                ]
                seed_deltas[str(seed)] = st.mean(paired)
            vals = list(seed_deltas.values())
            contrasts[key][metric] = {
                "per_seed_mean_delta": seed_deltas,
                "mean_delta": st.mean(vals),
                "min_seed_delta": min(vals),
                "max_seed_delta": max(vals),
                "positive_seeds": sum(v > 0 for v in vals),
                "negative_seeds": sum(v < 0 for v in vals),
                "sign_consistent": all(v > 0 for v in vals) or all(v < 0 for v in vals),
            }

    repeat = load_repeat_scores(Path(args.repeat_scores) if args.repeat_scores else None)
    repeat_rows = []
    judge_score_vars = []
    for (seed, condition), records in table.items():
        system = ("qwen_multiseed_s" + str(seed)
                  + ("" if condition == "base" else "__" + condition))
        deltas = [
            repeat[(system, item_id)] - float(records[item_id]["ccs"])
            for item_id in sorted(common_items)
            if (system, item_id) in repeat
        ]
        if deltas:
            repeat_rows.append({
                "seed": seed, "condition": condition,
                "n": len(deltas),
                "mean_delta_ccs": st.mean(deltas),
                "mean_abs_delta_ccs": st.mean(abs(v) for v in deltas),
                "std_delta_ccs": st.stdev(deltas) if len(deltas) > 1 else 0.0,
            })
            judge_score_vars.append(st.pvariance(deltas) / 2.0)

    judge_error_var = st.mean(judge_score_vars) if judge_score_vars else None
    residual_estimates = {}
    for condition in CONDITIONS:
        vc = metrics_out[condition]["ccs"]["variance_components"]
        residual = vc["item_x_seed_residual_variance"]
        residual_estimates[condition] = {
            "observed_item_x_seed_variance": residual,
            "estimated_judge_error_variance": judge_error_var,
            "generation_interaction_variance_after_judge_subtraction":
                max(0.0, residual - judge_error_var) if judge_error_var is not None else None,
        }

    probe_verdicts = {}
    if args.probes and args.repeat_probes:
        probe_verdicts = compare_probe_verdicts(
            [Path(p) for p in args.probes.split(",") if p],
            [Path(p) for p in args.repeat_probes.split(",") if p],
        )

    out = {
        "backbone": "Qwen-Image-Edit-2509 (dequantized NF4 weights, BF16 inference)",
        "n_items": len(common_items),
        "seeds": seeds,
        "conditions": list(CONDITIONS),
        "standardized_protocol": {
            "steps": 12,
            "guidance": 4.0,
            "judge": "qwen3-vl-plus",
            "judge_temperature": 0.0,
            "item_selection": "results/pairs108.txt (12 per task type)",
        },
        "metrics": metrics_out,
        "seed_rankings": orders,
        "ranking_stability": {
            "pairwise": pairs,
            "all_pairs_identical": all(p["identical_order"] for p in pairs),
            "identical_pair_fraction": sum(p["identical_order"] for p in pairs) / len(pairs),
            "minimum_kendall_tau": min(p["kendall_tau"] for p in pairs),
        },
        "pairwise_spearman_items": pairwise_rho,
        "condition_contrasts": contrasts,
        "judge_repeat": {
            "score_rows": repeat_rows,
            "probe_verdicts": probe_verdicts,
            "estimated_judge_error_variance": judge_error_var,
        },
        "generation_vs_judge": residual_estimates,
    }

    dst = Path(args.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "n_items": out["n_items"],
        "seeds": seeds,
        "ccs": {c: metrics_out[c]["ccs"]["mean"] for c in CONDITIONS},
        "ccs_std": {c: metrics_out[c]["ccs"]["std_across_seeds_population"]
                    for c in CONDITIONS},
        "ranking_stability": out["ranking_stability"],
        "judge_probe_agreement": probe_verdicts.get("exact_agreement"),
    }, indent=2))
    print("wrote", dst)


if __name__ == "__main__":
    main()

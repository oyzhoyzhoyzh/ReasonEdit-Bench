"""Publication figures for the paper."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import config  # noqa: E402
from .aggregate import FAILURE_NAMES  # noqa: E402
from .bench import read_jsonl  # noqa: E402
from .runs import label  # noqa: E402
from .stats import spearman  # noqa: E402

plt.rcParams.update({
    "font.size": 8.5,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "legend.frameon": True,
    "legend.borderpad": 0.3,
    "legend.labelspacing": 0.25,
    "legend.handlelength": 1.4,
})

#: Okabe-Ito colour-blind safe palette, used consistently across the figures.
OKABE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00",
         "#56B4E9", "#8C564B", "#000000", "#7F7F7F"]
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "*", "<"]


def boot_half_ci(values, n_boot: int = 2000, seed: int = 0) -> float:
    """Half-width of the 95% bootstrap interval of the mean, for error bars."""

    vals = np.asarray([v for v in values if v is not None and not np.isnan(v)], dtype=float)
    if len(vals) < 2:
        return 0.0
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(vals, size=len(vals), replace=True).mean()
                      for _ in range(n_boot)])
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(max(vals.mean() - lo, hi - vals.mean()))


#: Failure classes: colour plus hatch, so the stack stays readable in grayscale.
COLORS = {
    "OK": "#BDBDBD", "IUE": "#0072B2", "RPE": "#D55E00",
    "GE": "#009E73", "PQE": "#CC79A7", "CI": "#E69F00",
}
HATCH = {"OK": "", "IUE": "", "RPE": "///", "GE": "..", "PQE": "xx", "CI": "\\\\\\"}


def fig_failure_stack(rows, systems, out):
    fig, ax = plt.subplots(figsize=(6.6, 2.7))
    bottoms = np.zeros(len(systems))
    keys = ["IUE", "RPE", "GE", "PQE", "CI"]
    for k in keys:
        vals = []
        for s in systems:
            rs = [r for r in rows if r["system"] == s]
            vals.append(np.mean([r["failure"] == k for r in rs]) if rs else 0)
        ax.bar([label(s) for s in systems], vals, bottom=bottoms, label=FAILURE_NAMES[k],
               color=COLORS[k], hatch=HATCH[k], edgecolor="white", linewidth=0.4, width=0.62)
        bottoms += np.array(vals)
    ok = []
    for s in systems:
        rs = [r for r in rows if r["system"] == s]
        ok.append(np.mean([r["failure"] == "OK" for r in rs]) if rs else 0)
    ax.bar([label(s) for s in systems], ok, bottom=bottoms, label="no error",
           color=COLORS["OK"], edgecolor="white", linewidth=0.4, width=0.62)
    ax.set_ylabel("share of items")
    ax.set_ylim(0, 1)
    short = {"Qwen-Image-Edit + CausalScaffold": "Qwen-Image-Edit\n+ CausalScaffold",
             "Qwen-Image-Edit + Oracle-SCM": "Qwen-Image-Edit\n+ Oracle-SCM",
             "Qwen-Image-Edit + CoT": "Qwen-Image-Edit\n+ CoT",
             "Qwen-Image-Edit": "Qwen-Image-Edit",
             "InstructPix2Pix": "InstructPix2Pix"}
    ax.set_xticks(range(len(systems)))
    ax.set_xticklabels([short.get(label(s), label(s)) for s in systems],
                       rotation=30, ha="right", fontsize=7.5)
    ax.legend(ncol=3, fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


def fig_chain_curve(rows, systems, out):
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    xs_all = set()
    for i, s in enumerate(systems):
        buckets = defaultdict(list)
        for r in rows:
            if r["system"] == s:
                buckets[min(r["chain_length"], 6)].append(r["ccs"])
        xs = sorted(buckets)
        ys = [np.mean(buckets[x]) for x in xs]
        if len(xs) < 2:
            continue
        xs_all.update(xs)
        ax.plot(xs, ys, marker=MARKERS[i % len(MARKERS)], ms=4, lw=1.2,
                color=OKABE[i % len(OKABE)], label=f"{label(s)}")
    ticks = sorted(xs_all)
    counts = {}
    for x in ticks:
        counts[x] = sum(1 for r in rows if min(r["chain_length"], 6) == x
                        and r["system"] == systems[0])
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t}\n(n={counts[t]})" for t in ticks])
    ax.set_xlabel("reasoning-chain length")
    ax.set_ylabel("CCS")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.46))
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


def fig_domain_bars(rows, systems, out):
    domains = ["commonsense", "causal", "multi_step"]
    x = np.arange(len(domains))
    w = 0.8 / max(1, len(systems))
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    for i, s in enumerate(systems):
        vals = []
        for d in domains:
            rs = [r for r in rows if r["system"] == s and r["domain"] == d]
            vals.append(np.mean([r["ccs"] for r in rs]) if rs else 0)
        errs = [boot_half_ci([r["ccs"] for r in rows
                              if r["system"] == s and r["domain"] == d]) for d in domains]
        ax.bar(x + i * w - 0.4 + w / 2, vals, width=w, label=label(s),
               color=OKABE[i % len(OKABE)], edgecolor="white", linewidth=0.3,
               yerr=errs, capsize=1.2, error_kw=dict(lw=0.5, ecolor="#404040"))
    ax.set_xticks(x)
    ax.set_xticklabels(["commonsense", "causal", "multi-step"])
    ax.set_ylabel("CCS")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


def fig_metric_vs_human(scores, ratings, out):
    by = {(r["item_id"], r["system"]): r for r in scores}
    xs, ys, cols = [], [], []
    rng = np.random.default_rng(0)
    for h in ratings:
        r = by.get((h["item_id"], h["system"]))
        if not r:
            continue
        xs.append(r["ccs"])
        ys.append(float(h["logical"]))
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.7))
    jx = lambda v: np.asarray(v) + rng.normal(0, 0.012, size=len(v))
    jy = lambda v: np.asarray(v) + rng.normal(0, 0.06, size=len(v))
    axs[0].scatter(jx(xs), jy(ys), s=10, alpha=0.55, color=OKABE[0])
    rho0 = spearman(xs, ys)
    if len(xs) > 2:
        z = np.polyfit(xs, ys, 1)
        xg = np.linspace(min(xs), max(xs), 50)
        axs[0].plot(xg, np.polyval(z, xg), color="#000000", lw=1.0)
    axs[0].set_title(f"$\\rho$ = {rho0:.3f}  (n = {len(xs)})", fontsize=8)
    axs[0].set_xlabel("CCS (automatic)")
    axs[0].set_ylabel("human logical consistency (1-5)")
    clip_x = [by[(h["item_id"], h["system"])].get("clipscore", np.nan) for h in ratings
              if (h["item_id"], h["system"]) in by]
    clip_y = [float(h["instruction"]) for h in ratings
              if (h["item_id"], h["system"]) in by]
    axs[1].scatter(jx(clip_x), jy(clip_y), s=10, alpha=0.55, color=OKABE[1])
    rho1 = spearman(clip_x, clip_y)
    if len(clip_x) > 2:
        z = np.polyfit(clip_x, clip_y, 1)
        xg = np.linspace(min(clip_x), max(clip_x), 50)
        axs[1].plot(xg, np.polyval(z, xg), color="#000000", lw=1.0)
    axs[1].set_title(f"$\\rho$ = {rho1:.3f}  (n = {len(clip_x)})", fontsize=8)
    axs[1].set_xlabel("CLIPScore")
    axs[1].set_ylabel("human instruction following (1-5)")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


def fig_bench_overview(items, out):
    from .taxonomy import TASK_TYPES

    keys = list(TASK_TYPES)
    chain = [np.mean([i["meta"]["chain_length"] for i in items if i["type"] == k]) for k in keys]
    short = {"counterfactual": "counter-\nfactual", "long_horizon": "long-\nhorizon",
             "conditional": "condi-\ntional"}
    order = np.argsort(chain)
    keys = [keys[i] for i in order]
    chain = [chain[i] for i in order]
    errs = [boot_half_ci([i["meta"]["chain_length"] for i in items if i["type"] == k])
            for k in keys]
    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    x = np.arange(len(keys))
    ax.bar(x, chain, color=OKABE[0], width=0.62, yerr=errs, capsize=1.6,
           error_kw=dict(lw=0.6, ecolor="#404040"))
    overall = np.mean([i["meta"]["chain_length"] for i in items])
    ax.axhline(overall, color="#000000", ls="--", lw=0.9)
    ax.annotate(f"all items: {overall:.2f}",
                xy=(len(keys) - 0.35, overall), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([short.get(k, k.replace("_", " ")) for k in keys],
                       rotation=30, ha="right", fontsize=7.5)
    ax.set_ylabel("mean reasoning steps")
    ax.set_ylim(0, max(chain) * 1.25)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print("wrote", out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--human", default=str(config.RESULTS / "human_eval" / "ratings.jsonl"))
    ap.add_argument("--out", default=str(config.RESULTS / "figures"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = read_jsonl(config.BENCH_DIR / args.bench)
    fig_bench_overview(items, out / "fig1_bench.pdf")
    fig_bench_overview(items, out / "fig1_bench.png")

    scores_path = Path(args.scores)
    if scores_path.exists():
        rows = read_jsonl(scores_path)
        from .runs import FINAL_SYSTEMS

        rows = [r for r in rows if r["system"] in FINAL_SYSTEMS]
        systems = sorted({r["system"] for r in rows})
        fig_failure_stack(rows, systems, out / "fig2_failures.pdf")
        fig_failure_stack(rows, systems, out / "fig2_failures.png")
        fig_chain_curve(rows, systems, out / "fig3_chain.pdf")
        fig_chain_curve(rows, systems, out / "fig3_chain.png")
        fig_domain_bars(rows, systems, out / "fig4_domain.pdf")
        fig_domain_bars(rows, systems, out / "fig4_domain.png")
        if Path(args.human).exists():
            fig_metric_vs_human(rows, read_jsonl(Path(args.human)), out / "fig5_human.pdf")
            fig_metric_vs_human(rows, read_jsonl(Path(args.human)), out / "fig5_human.png")


if __name__ == "__main__":
    main()

"""Schematic overview of the causal contract and the probing protocol.

Produces ``results/figures/fig0_method.pdf``, the pipeline figure for the method
section: an instruction is turned into an object-level structural causal model, the
model fixes what must change and what must survive, and each proposition is verified
on the region it is about.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from . import config

INK = "#1b1b1b"
FILL = "#eef2f7"
ACCENT = "#dce9f7"
WARN = "#f7e6dc"


def box(ax, x, y, w, h, text, fill=FILL, size=8.2, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.0, edgecolor=INK, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            color=INK, weight=weight, wrap=True)


def arrow(ax, p, q, style="-|>", rad=0.0, lw=1.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9,
                                 linewidth=lw, color=INK, shrinkA=2, shrinkB=2,
                                 connectionstyle=f"arc3,rad={rad}"))


def main():
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.0)
    ax.axis("off")

    # ---- stage 1: instruction -------------------------------------------------
    box(ax, 0.12, 4.55, 1.86, 1.75,
        "Instruction\n\nnames a cause;\neffects implicit\n\n\u201cturn the\nlamp off\u201d", size=8.3)

    # ---- stage 2: structural causal model -------------------------------------
    box(ax, 2.42, 4.55, 2.75, 1.75,
        "Object-level SCM\n\n$do(v \\leftarrow x)$\n\n"
        "nodes: objects, attributes,\nevents\n"
        "edges: causes, enables,\nprevents", fill=ACCENT, size=8.2)

    # ---- stage 3: the contract ------------------------------------------------
    box(ax, 5.55, 5.25, 2.20, 0.72, "descendants $\\mathrm{De}(v)$:\nmust change",
        fill=ACCENT, size=8.6)
    box(ax, 5.55, 4.35, 2.20, 0.72, "non-descendants:\nmust survive",
        fill="#eaf3ea", size=8.6)
    ax.text(6.65, 4.05, "causal contract", ha="center", va="center", fontsize=9.2,
            style="italic", color=INK)

    # ---- stage 4: region-grounded probing -------------------------------------
    box(ax, 8.15, 3.95, 3.65, 2.35, "", fill=WARN)
    ax.text(9.98, 6.03, "Region-grounded probe", ha="center", va="center",
            fontsize=9.4, weight="bold", color=INK)
    # little crop schematic inside the probe box
    ax.add_patch(Rectangle((8.85, 5.42), 0.95, 0.38, fc="#c9c9c9", ec=INK, lw=1.0))
    ax.add_patch(Rectangle((9.87, 5.42), 0.95, 0.38, fc="#a8c8e8", ec=INK, lw=1.0))
    ax.text(9.32, 5.32, "BEFORE", ha="center", va="top", fontsize=7.4, color=INK)
    ax.text(10.34, 5.32, "AFTER", ha="center", va="top", fontsize=7.4, color=INK)
    ax.text(9.98, 4.99, "crop the region each\nproposition is about", ha="center",
            va="center", fontsize=8.0, color=INK)
    ax.text(9.98, 4.48, "ask one yes / no question\none probe per proposition",
            ha="center", va="center", fontsize=8.2, color=INK)

    arrow(ax, (1.98, 5.42), (2.42, 5.42))
    arrow(ax, (5.17, 5.42), (5.55, 5.42))
    arrow(ax, (7.75, 5.42), (8.15, 5.42))

    # ---- outputs --------------------------------------------------------------
    box(ax, 0.15, 0.35, 5.75, 2.25,
        "Scores per system\n\nTCS | DPS | NPS | OCS\n"
        "CCS = (TCS + DPS + NPS) / 3\nContract: every probe passes",
        size=9.0)
    box(ax, 6.20, 0.35, 5.60, 2.25,
        "deterministic failure attribution\n\nIUE (instruction) \u00b7 GE (grounding)\n"
        "RPE (reasoning) \u00b7 CI (causal) \u00b7 PQE (quality)",
        size=8.8)
    arrow(ax, (9.98, 3.95), (9.98, 3.30), rad=0.0)
    ax.plot([3.00, 9.98], [3.30, 3.30], color=INK, lw=1.1)
    arrow(ax, (3.00, 3.30), (3.00, 2.60), rad=0.0)
    arrow(ax, (9.00, 3.30), (9.00, 2.60), rad=0.0)
    ax.text(6.50, 3.47, "computed from the same probe verdicts",
            ha="center", va="bottom", fontsize=7.8, style="italic", color=INK)

    fig.tight_layout(pad=0.2)
    dst = config.RESULTS / "figures" / "fig0_method.pdf"
    dst.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dst, bbox_inches="tight")
    fig.savefig(dst.with_suffix(".png"), dpi=200, bbox_inches="tight")
    print("wrote", dst)


if __name__ == "__main__":
    main()

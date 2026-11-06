"""Export LaTeX tables for the paper from the aggregated scores."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import config
from .aggregate import FAILURE_NAMES, build_table, bootstrap_ci, summarize
from .bench import read_jsonl
from .runs import label, label_short
from .stats import paired_bootstrap


def pct(v: float, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{100*v:.{digits}f}"


def num(v: float, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{v:.{digits}f}"


def mark(values, digits: int = 3, pct: bool = False, lower_is_better: bool = False) -> list[str]:
    """Render a column and bold the best entry, underlining the runner-up.

    ``values`` is a list of floats (``nan`` allowed for a missing system).
    Ties share the same mark; the runner-up is only marked when it is strictly
    better than every remaining entry.
    """

    fmt = (lambda v: pct_str(v, digits)) if pct else (lambda v: num(v, digits))
    ok = [(i, v) for i, v in enumerate(values) if v is not None and not np.isnan(v)]
    out = [fmt(v) for v in values]
    if not ok:
        return out
    ordered = sorted(ok, key=lambda kv: kv[1], reverse=not lower_is_better)
    best = ordered[0][1]
    best_idx = [i for i, v in ordered if v == best]
    second = None
    for _, v in ordered:
        if v != best:
            second = v
            break
    second_idx = [i for i, v in ordered if second is not None and v == second]
    for i in best_idx:
        out[i] = f"\\textbf{{{fmt(values[i])}}}"
    for i in second_idx:
        out[i] = f"\\underline{{{fmt(values[i])}}}"
    return out


def pct_str(v: float, digits: int = 1) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "--"
    return f"{100*v:.{digits}f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--out", default=str(config.ROOT / "paper" / "tables"))
    ap.add_argument("--order", default=None, help="comma separated system order")
    ap.add_argument("--systems", default=None)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(Path(args.scores))
    from .runs import FINAL_SYSTEMS

    systems = sorted({r["system"] for r in rows})
    keep = args.systems.split(",") if args.systems else FINAL_SYSTEMS
    systems = [s for s in systems if s in keep]
    rows = [r for r in rows if r["system"] in keep]
    if args.order:
        order = args.order.split(",")
        systems = [s for s in order if s in systems] + [s for s in systems if s not in order]

    summary = {tuple([r["system"]]): r for r in summarize(rows)}
    by_sys = {s: [r for r in rows if r["system"] == s] for s in systems}

    # ------------------------------------------------------------ main table --
    lines = [
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{1.0pt}",
        "\\begin{tabular}{l" + "c" * 11 + "}",
        "\\toprule",
        "System & TCS$\\uparrow$ & DPS$\\uparrow$ & NPS$\\uparrow$ & CCS$\\uparrow$ & "
        "CCS sd$\\downarrow$ & OCS$\\uparrow$ & Contract\\,(\\%)$\\uparrow$ & CLIP-S$\\uparrow$ & "
        "DINO-I$\\uparrow$ & LPIPS$\\downarrow$ & RPE+CI\\,(\\%)$\\downarrow$ \\\\",
        "\\midrule",
    ]
    cols = [
        ([summary[(s,)]["tcs"] for s in systems], 3, False, False),
        ([summary[(s,)]["dps"] for s in systems], 3, False, False),
        ([summary[(s,)]["nps"] for s in systems], 3, False, False),
        ([summary[(s,)]["ccs"] for s in systems], 3, False, False),
        ([float(np.std([r["ccs"] for r in by_sys[s]], ddof=1)) for s in systems], 3, False, True),
        ([summary[(s,)]["ocs"] for s in systems], 3, False, False),
        ([summary[(s,)]["strict_success"] for s in systems], 1, True, False),
        ([summary[(s,)]["clipscore"] for s in systems], 2, False, False),
        ([summary[(s,)]["dino_i"] for s in systems], 3, False, False),
        ([summary[(s,)]["lpips"] for s in systems], 3, False, True),
        ([summary[(s,)]["fail_RPE"] + summary[(s,)]["fail_CI"] for s in systems], 1, True, True),
    ]
    rendered = [mark(vals, digits, pct, lower) for vals, digits, pct, lower in cols]
    # Between-item dispersion is a diagnostic, not a performance metric.
    rendered[4] = [num(v, 3) for v in cols[4][0]]
    for i, s in enumerate(systems):
        cells = " & ".join(col[i] for col in rendered)
        lines.append(f"{label(s)} & {cells} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (out / "main_results.tex").write_text("\n".join(lines))

    # --------------------------------------------------------- domain table --
    dom = summarize(rows, ("system", "domain"))
    dom_by = defaultdict(dict)
    for r in dom:
        dom_by[r["system"]][r["domain"]] = r
    dl = [
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{2.8pt}",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        " & \\multicolumn{2}{c}{Commonsense} & \\multicolumn{2}{c}{Causal} & "
        "\\multicolumn{2}{c}{Multi-step} \\\\",
        "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}",
        "System & CCS & DPS & CCS & DPS & CCS & OCS \\\\",
        "\\midrule",
    ]
    dom_cols = []
    for d in ("commonsense", "causal", "multi_step"):
        dom_cols.append([dom_by[s].get(d, {}).get("ccs", float("nan")) for s in systems])
        dom_cols.append(
            [dom_by[s].get(d, {}).get("ocs" if d == "multi_step" else "dps", float("nan"))
             for s in systems]
        )
    dom_rendered = [mark(vals, 3) for vals in dom_cols]
    for i, s in enumerate(systems):
        row = [label_short(s)] + [col[i] for col in dom_rendered]
        dl.append(" & ".join(row) + " \\\\")
    dl += ["\\bottomrule", "\\end{tabular}"]
    (out / "domain_results.tex").write_text("\n".join(dl))

    # ------------------------------------------------------ failure table ----
    fl = [
        "\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabular}{l" + "c" * len(FAILURE_NAMES) + "}",
        "\\toprule",
        "System & " + " & ".join(k for k in FAILURE_NAMES) + " \\\\",
        "\\midrule",
    ]
    for s in systems:
        d = summary[(s,)]
        fl.append(label_short(s) + " & " + " & ".join(pct(d[f"fail_{k}"], 0) for k in FAILURE_NAMES)
                  + " \\\\")
    fl += ["\\bottomrule", "\\end{tabular}"]
    (out / "failure_table.tex").write_text("\n".join(fl))

    # ------------------------------------------------------- type table ------
    typ = summarize(rows, ("type",))
    tl = ["\\small", "\\begin{tabular}{lccc}", "\\toprule",
          "Task type & CCS & DPS & Contract (\\%) \\\\", "\\midrule"]
    for r in sorted(typ, key=lambda r: r["type"]):
        tl.append(f"{r['type'].replace('_',' ')} & {num(r['ccs'])} & {num(r['dps'])} & "
                  f"{pct(r['strict_success'],0)} \\\\")
    tl += ["\\bottomrule", "\\end{tabular}"]
    (out / "type_table.tex").write_text("\n".join(tl))

    # ------------------------------------------------- significance table ----
    base_key = "qwen_image_edit"
    if base_key in by_sys:
        base = {r["item_id"]: r for r in by_sys[base_key]}
        comp = []
        for s in systems:
            if s == base_key:
                continue
            pairs = [(r["ccs"], base[r["item_id"]]["ccs"]) for r in by_sys[s]
                     if r["item_id"] in base]
            a = [p[0] for p in pairs]
            b = [p[1] for p in pairs]
            mean, lo, hi, p = paired_bootstrap(a, b)
            d = np.array(a) - np.array(b)
            sd = float(d.std(ddof=1))
            comp.append([s, mean, lo, hi, p, float(d.mean() / sd) if sd else float("nan")])
        ranked = sorted(range(len(comp)), key=lambda i: comp[i][4])
        running = 0.0
        for rank, i in enumerate(ranked):
            running = max(running, min(1.0, comp[i][4] * (len(comp) - rank)))
            comp[i].append(running)
        st = ["\\scriptsize", "\\setlength{\\tabcolsep}{2.5pt}",
              "\\begin{tabular}{lcccc}", "\\toprule",
              "System & $\\Delta$CCS & 95\\% CI & $d_z$ & $p_{\\mathrm{Holm}}$ \\\\",
              "\\midrule"]
        for s, mean, lo, hi, p, dz, ph in comp:
            star = "$^{***}$" if ph < 0.001 else "$^{**}$" if ph < 0.01 else "$^{*}$" if ph < 0.05 else ""
            st.append(f"{label_short(s)} & {mean:+.3f}{star} & "
                      f"[{lo:+.3f}, {hi:+.3f}] & {dz:+.2f} & "
                      f"{('$<$0.001' if ph < 0.001 else f'{ph:.3f}')} \\\\")
        st += ["\\bottomrule", "\\end{tabular}"]
        (out / "stats_table.tex").write_text("\n".join(st))

    # ----------------------------------------------------- framing table -----
    fr_path = config.RESULTS / "analysis" / "framing.json"
    if fr_path.exists():
        fr = json.loads(fr_path.read_text())
        ft = ["\\scriptsize", "\\setlength{\\tabcolsep}{2.5pt}",
              "\\begin{tabular}{lccc}", "\\toprule",
              "System & Agreement (\\%) & $\\Delta$CCS & $p$ \\\\",
              "\\midrule"]
        for s in ("instructpix2pix", "qwen_image_edit", "qwen_image_edit__cot"):
            v = fr.get("systems", {}).get(s)
            if not v:
                continue
            ft.append(
                f"{label_short(s)} & {100*v['verdict_agreement']:.1f} & "
                f"{v['delta_ccs']:+.3f} & {v['delta_p']:.3f} \\\\")
        ft += ["\\bottomrule", "\\end{tabular}"]
        (out / "framing_table.tex").write_text("\n".join(ft))

    # --------------------------------------------------- sensitivity table ---
    sn_path = config.RESULTS / "analysis" / "sensitivity.json"
    if sn_path.exists():
        sn = json.loads(sn_path.read_text())
        rows = [("Crop margin", "0.00 (tight)", sn["axes"]["pad"]["0.0"]["qwen_image_edit"]),
                ("", "0.12 (default)", None),
                ("", "0.30 (loose)", sn["axes"]["pad"]["0.30"]["qwen_image_edit"]),
                ("Judge temperature", "0.0 (default)", None),
                ("", "0.3", sn["axes"]["temp"]["0.3"]["qwen_image_edit"])]
        st = ["\\footnotesize", "\\setlength{\\tabcolsep}{3pt}",
              "\\begin{tabular}{llccc}", "\\toprule",
              "Knob & Setting & Agree. & $\\Delta$CCS & $p$ \\\\", "\\midrule"]
        for knob, setting, v in rows:
            if v is None:
                st.append(f"{knob} & {setting} & --- & --- & --- \\\\")
            else:
                p = "<0.001" if v["p"] < 0.001 else f"{v['p']:.2f}"
                st.append(f"{knob} & {setting} & {100*v['agreement']:.0f}\\% & "
                          f"{v['delta_ccs']:+.3f} & {p} \\\\")
        st += ["\\bottomrule", "\\end{tabular}"]
        (out / "sensitivity_table.tex").write_text("\n".join(st))

    # ---------------------------------------------------- fidelity table ----
    fd_path = config.RESULTS / "analysis" / "fidelity.json"
    if fd_path.exists():
        fd = json.loads(fd_path.read_text())
        rows_fd = sorted(fd["rows"], key=lambda r: r["frechet_alexnet"])
        lines_fd = ["\\footnotesize", "\\setlength{\\tabcolsep}{5pt}",
                    "\\begin{tabular}{@{}lr@{}}", "\\toprule",
                    "System & FD$_{\\mathrm{AlexNet}}\\downarrow$ \\\\", "\\midrule"]
        for r in rows_fd:
            lines_fd.append(f"{label_short(r['system'])} & {r['frechet_alexnet']:,.0f} \\\\")
        lines_fd += ["\\bottomrule", "\\end{tabular}"]
        (out / "fidelity_table.tex").write_text("\n".join(lines_fd))

    # ------------------------------------------ Qwen main-backbone multiseed ----
    qm_path = config.RESULTS / "analysis" / "qwen_multiseed.json"
    if qm_path.exists():
        qm = json.loads(qm_path.read_text())
        conditions = [
            ("base", "Base"),
            ("cot", "+CoT"),
            ("oracle", "+Oracle"),
            ("scaffold_full", "+Scaffold"),
        ]
        cols = [("tcs", "TCS"), ("dps", "DPS"), ("nps", "NPS"), ("ccs", "CCS")]
        mt = ["\\scriptsize", "\\setlength{\\tabcolsep}{1.5pt}",
              "\\begin{tabular}{@{}lcccc@{}}", "\\toprule",
              "Condition & TCS & DPS & NPS & CCS \\\\", "\\midrule"]
        for condition, name in conditions:
            cells = []
            for metric, _ in cols:
                value = qm["metrics"][condition][metric]
                cells.append(
                    f"${value['mean']:.3f}\\pm "
                    f"{value['std_across_seeds_population']:.3f}$"
                )
            mt.append(f"{name} & {' & '.join(cells)} \\\\")
        mt += ["\\bottomrule", "\\end{tabular}"]
        (out / "multiseed_table.tex").write_text("\n".join(mt))

        seeds = [str(s) for s in qm["seeds"]]
        st = ["\\scriptsize", "\\setlength{\\tabcolsep}{2.5pt}",
              "\\begin{tabular}{@{}lcccccc@{}}", "\\toprule",
              "Condition & $s_1$ & $s_2$ & $s_3$ & Mean & SD & 95\\% CI \\\\",
              "\\midrule"]
        for condition, name in conditions:
            ccs = qm["metrics"][condition]["ccs"]
            seed_cells = " & ".join(f"{ccs['seed_means'][s]:.3f}" for s in seeds)
            lo, hi = ccs["ci95_item_clustered"]
            st.append(
                f"{name} & {seed_cells} & {ccs['mean']:.3f} & "
                f"{ccs['std_across_seeds_population']:.3f} & "
                f"[{lo:.3f}, {hi:.3f}] \\\\"
            )
        st += ["\\bottomrule", "\\end{tabular}"]
        (out / "multiseed_seeds_table.tex").write_text("\n".join(st))

    # ------------------------------------------------------ taxonomy table ---
    from .taxonomy import TASK_TYPES

    tl2 = ["\\small", "\\setlength{\\tabcolsep}{4pt}",
           "\\begin{tabular}{llp{6.0cm}ccc}", "\\toprule",
           "Domain & Type & Definition & Nodes & Steps & Effects \\\\", "\\midrule"]
    for domain, name in (("commonsense", "Commonsense"), ("causal", "Causal"),
                         ("multi\\-step", "Multi-step")):
        keys = [k for k, v in TASK_TYPES.items() if v.domain == domain.replace("\\-", "_")]
        for i, k in enumerate(keys):
            t = TASK_TYPES[k]
            first = f"\\multirow{{{len(keys)}}}{{*}}{{{name}}}" if i == 0 else ""
            tl2.append(
                f"{first} & {t.name_en} & {t.definition} & $\\geq{t.min_nodes}$ & "
                f"$\\geq{t.min_chain}$ & $\\geq{t.min_effects}$ \\\\"
            )
        tl2.append("\\midrule")
    tl2 = tl2[:-1] + ["\\bottomrule", "\\end{tabular}"]
    (out / "taxonomy_table.tex").write_text("\n".join(tl2))

    print(f"tables -> {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

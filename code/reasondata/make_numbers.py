"""Generate paper/numbers.tex: every quantitative claim in the paper is a macro.

This keeps the prose and the tables in sync with the artefacts in ``results/``.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .bench import read_jsonl
from .judge_agreement import load_probes
from .runs import label
from .stats import kappa, paired_bootstrap, spearman


def fmt(x, digits=2, pct=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "--"
    return f"{100*x:.{digits}f}" if pct else f"{x:.{digits}f}"


def boot_spearman(x, y, n_boot: int = 5000, seed: int = 0) -> tuple[float, float]:
    """95% bootstrap interval for a Spearman correlation on a small sample."""

    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(idx.tolist())) < 4:
            continue
        v = spearman(list(x[idx]), list(y[idx]))
        if not np.isnan(v):
            vals.append(v)
    if len(vals) < 100:
        return float("nan"), float("nan")
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--human", default=str(config.RESULTS / "human_eval" / "ratings.jsonl"))
    ap.add_argument("--out", default=str(config.ROOT / "paper" / "numbers.tex"))
    args = ap.parse_args()

    items = read_jsonl(config.BENCH_DIR / args.bench)
    rows = read_jsonl(Path(args.scores))
    from .runs import FINAL_SYSTEMS

    rows = [r for r in rows if r["system"] in FINAL_SYSTEMS]
    by_sys = defaultdict(list)
    for r in rows:
        by_sys[r["system"]].append(r)
    by_sys_item = {s: {r["item_id"]: r for r in rs} for s, rs in by_sys.items()}

    def mean(s, key, valid_only=True):
        rs = by_sys.get(s, [])
        return float(np.mean([r[key] for r in rs])) if rs else float("nan")

    macros: dict[str, str] = {}
    macros["NITEMS"] = str(len(items))
    # The primary table was generated before the newer sensitivity studies; its
    # manifests, not the current default sampling seed, are authoritative.
    primary_manifest = config.RESULTS / "qwen_image_edit" / "base" / "manifest.jsonl"
    if primary_manifest.exists():
        primary_seeds = Counter(
            r.get("seed") for r in read_jsonl(primary_manifest)
            if r.get("status") == "ok" and r.get("seed") is not None
        )
        macros["SEEDVALUE"] = str(primary_seeds.most_common(1)[0][0])
    else:
        macros["SEEDVALUE"] = str(config.SEED)
    counts = defaultdict(int)
    for it in items:
        counts[it["type"]] += 1
    macros["PERITEM"] = str(min(counts.values())) if counts else "--"
    macros["PERDOMAIN"] = str(len(items) // 3)
    macros["MEANCHAIN"] = fmt(np.mean([i["meta"]["chain_length"] for i in items]), 2)
    macros["MEANNODES"] = fmt(np.mean([i["meta"]["num_nodes"] for i in items]), 2)
    macros["MEANDEPTH"] = fmt(np.mean([i["meta"]["depth"] for i in items]), 2)
    macros["MEANEFF"] = fmt(np.mean([i["meta"]["num_effects"] for i in items]), 2)
    diff = defaultdict(int)
    for i in items:
        diff[i["meta"]["difficulty"]] += 1
    macros["DIFFEASY"] = str(diff["easy"])
    macros["DIFFMED"] = str(diff["medium"])
    macros["DIFFHARD"] = str(diff["hard"])
    srcs = defaultdict(int)
    for i in items:
        srcs[i["source"]["dataset"]] += 1
    macros["DATASPLIT"] = " / ".join(str(v) for _, v in sorted(srcs.items()))

    base, cot = "qwen_image_edit", "qwen_image_edit__cot"
    scaf, orac = "qwen_image_edit__scaffold_full", "qwen_image_edit__oracle"
    macros["QUABASE"] = fmt(mean(base, "qua"), 0, pct=True)
    macros["BASECONTRACT"] = fmt(100 * float(np.mean([r["strict_success"]
                                                      for r in by_sys.get(base, [])])), 0)
    macros["TCSDPSGAP"] = fmt(100 * (mean(base, "tcs") - mean(base, "dps")), 1)
    macros["CCSBASE"] = fmt(mean(base, "ccs"))
    macros["CCSCOT"] = fmt(mean(cot, "ccs"))
    macros["DPSGAP"] = fmt(100 * (mean(cot, "dps") - mean(base, "dps")), 1)
    macros["NPSGAP"] = fmt(100 * (mean(cot, "nps") - mean(base, "nps")), 1)
    macros["NPSLOSS"] = fmt(abs(100 * (mean(cot, "nps") - mean(base, "nps"))), 1)
    macros["CCSORACLE"] = fmt(mean(orac, "ccs"))
    macros["DPSORACLE"] = fmt(mean(orac, "dps"))
    if by_sys.get(orac):
        fail_share = 1 - float(np.mean([r["strict_success"] for r in by_sys[orac]]))
        macros["ORACLEGAP"] = f"{100*fail_share:.0f}"
    else:
        macros["ORACLEGAP"] = "--"
    # "complete contract" == every causal probe answers yes (strict_success).
    # ``success`` is the weaker criterion used by the failure attributor (see
    # attribute_failure: it tolerates one in four effects/preserved facts failing)
    # and is reported as "No Error" in the failure-attribution table.
    best = max((np.mean([r["strict_success"] for r in rs]) for rs in by_sys.values()), default=0)
    macros["BESTSUCC"] = fmt(best, 0, pct=True)
    for tag, s in (("BASE", base), ("COT", cot), ("ORAC", orac),
                   ("SCAF", scaf)):
        vals = [r["strict_success"] for r in by_sys.get(s, [])]
        macros[f"{tag}CONTRACT"] = fmt(100 * float(np.mean(vals)), 1) if vals else "--"
    lh = [r for r in rows if r["type"] == "long_horizon"]
    macros["LONGHORIZONCONTRACT"] = (
        fmt(100 * np.mean([r["strict_success"] for r in lh]), 0) if lh else "--"
    )
    macros["LONGHORIZONCCS"] = (
        fmt(float(np.mean([r["ccs"] for r in lh])), 3) if lh else "--"
    )
    macros["BASENPS"] = fmt(mean(base, "nps"))
    macros["ORACLENPS"] = fmt(mean(orac, "nps"))
    macros["TCSORACLE"] = fmt(mean(orac, "tcs"))
    for s, tag in ((base, "BASE"), (orac, "ORAC")):
        rs = by_sys.get(s, [])
        for key in ("IUE", "GE", "RPE", "CI", "PQE"):
            share = np.mean([r["failure"] == key for r in rs]) if rs else float("nan")
            macros[f"{tag}{key}"] = fmt(100 * share, 0)
        never = np.mean([r["failure"] in ("IUE", "GE") for r in rs]) if rs else float("nan")
        macros[f"{tag}NEVER"] = fmt(100 * never, 0)

    # Item-level contract-rate tests. The main CCS family is corrected in
    # ``stats_table``; this separately tests the binary strict-contract outcome.
    def exact_mcnemar(a: dict[str, dict], b: dict[str, dict]) -> tuple[float, int, int]:
        common = sorted(set(a) & set(b))
        right = sum((not a[i]["strict_success"]) and b[i]["strict_success"] for i in common)
        left = sum(a[i]["strict_success"] and (not b[i]["strict_success"]) for i in common)
        n = right + left
        if n == 0:
            return 1.0, right, left
        tail = sum(math.comb(n, j) for j in range(min(right, left) + 1))
        return min(1.0, 2 * tail / (2 ** n)), right, left

    if base in by_sys_item:
        contract_tests = {}
        for s in FINAL_SYSTEMS:
            if s == base or s not in by_sys_item:
                continue
            p, right, left = exact_mcnemar(by_sys_item[base], by_sys_item[s])
            contract_tests[s] = p
        ranked = sorted(contract_tests, key=contract_tests.get)
        running = 0.0
        adjusted = {}
        for rank, s in enumerate(ranked, 1):
            running = max(running, min(1.0, contract_tests[s] * (len(ranked) - rank + 1)))
            adjusted[s] = running
        for tag, s in (("COT", cot), ("ORAC", orac), ("SCAF", scaf)):
            if s in adjusted:
                macros[f"{tag}CONTP"] = (
                    "<0.001" if adjusted[s] < 0.001 else fmt(adjusted[s], 3)
                )

    # chain-length analysis: CCS of three-step vs four-step items
    def ccs_at(s: str, length: int) -> float:
        rs = [r for r in by_sys.get(s, [])
              if r.get("chain_length") == length and r.get("ccs") is not None]
        return float(np.mean([r["ccs"] for r in rs])) if rs else float("nan")

    chain_counts = Counter(r["chain_length"] for r in by_sys.get(base, []))
    # NB: macro names may not end in a digit (TeX would read \CHAINN2 as \CHAINN + "2").
    macros["CHAINLOW"] = str(chain_counts.get(2, 0))
    macros["CHAINMID"] = str(chain_counts.get(3, 0))
    macros["CHAINHIGH"] = str(chain_counts.get(4, 0))
    for s, name in ((base, "CHAINDROPBASE"), (cot, "CHAINDROPCOT"),
                    (orac, "CHAINDROPORAC"), (scaf, "CHAINDROPSCAF")):
        drop = ccs_at(s, 3) - ccs_at(s, 4)
        macros[name] = fmt(drop) if not np.isnan(drop) else "--"
    macros["SCAFRATE"] = "--"
    try:
        req = read_jsonl(config.RESULTS / "qwen_image_edit" / "scaffold_requests.jsonl")
        macros["SCAFRATE"] = fmt(100 * len(req) / max(1, len(items)), 0)
    except FileNotFoundError:
        pass
    for key, name in (("dps", "SCAFDPS"), ("nps", "SCAFNPS"), ("ocs", "SCAFOCS")):
        if by_sys.get(scaf) and by_sys.get(cot):
            a = np.array([r[key] for r in by_sys[scaf] if r[key] is not None])
            b = np.array([r[key] for r in by_sys[cot] if r[key] is not None])
            macros[name] = fmt(100 * (a.mean() - b.mean()), 1)
        else:
            macros[name] = "--"

    # paired test scaffold/cot and cot/base
    try:
        for a_sys, b_sys, name in ((cot, base, "COTP"), (scaf, cot, "SCAFPP"),
                                   (orac, cot, "ORACP")):
            common = sorted(set(by_sys_item.get(a_sys, {})) & set(by_sys_item.get(b_sys, {})))
            if len(common) > 20:
                a = [by_sys_item[a_sys][i]["ccs"] for i in common]
                b = [by_sys_item[b_sys][i]["ccs"] for i in common]
                _, _, _, p = paired_bootstrap(a, b)
                macros[name] = f"{p:.3f}"
            else:
                macros[name] = "--"
        for a_sys, b_sys, key, name in ((scaf, cot, "dps", "SCAFDPSP"),
                                        (scaf, cot, "ocs", "SCAFOCSP"),
                                        (scaf, cot, "nps", "SCAFNPSP"),
                                        (scaf, cot, "tcs", "SCAFTCSP"),
                                        (cot, base, "dps", "COTDPSP"),
                                        (cot, base, "nps", "COTNPSP"),
                                        (cot, base, "tcs", "COTTCSP"),
                                        (orac, base, "nps", "ORACNPSP")):
            common = sorted(set(by_sys_item.get(a_sys, {})) & set(by_sys_item.get(b_sys, {})))
            common = [i for i in common if by_sys_item[a_sys][i][key] is not None
                      and by_sys_item[b_sys][i][key] is not None]
            if len(common) > 20:
                a = [by_sys_item[a_sys][i][key] for i in common]
                b = [by_sys_item[b_sys][i][key] for i in common]
                _, _, _, p = paired_bootstrap(a, b)
                macros[name] = f"{p:.4f}" if p > 0 else "<0.0001"
            else:
                macros[name] = "--"
    except Exception:  # noqa: BLE001
        pass

    # human audit
    human_path = Path(args.human)
    if human_path.exists():
        hr = read_jsonl(human_path)
        macros["NHUMAN"] = str(len(hr))
        macros["NHUMANRATERS"] = "1"
        macros["NHUMANSYSTEMS"] = str(len({h["system"] for h in hr}))
        pairs_ccs = [(by_sys_item[h["system"]][h["item_id"]]["ccs"], float(h["logical"]))
                     for h in hr if h["item_id"] in by_sys_item.get(h["system"], {})]
        pairs_clip = [(by_sys_item[h["system"]][h["item_id"]].get("clipscore", np.nan),
                       float(h["instruction"]))
                      for h in hr if h["item_id"] in by_sys_item.get(h["system"], {})]
        macros["HUMSCCS"] = fmt(spearman([x for x, _ in pairs_ccs], [y for _, y in pairs_ccs]), 3)
        macros["HUMSCLIP"] = fmt(spearman([x for x, _ in pairs_clip], [y for _, y in pairs_clip]), 3)
        for tag, pairs in (("HUMSCCS", pairs_ccs), ("HUMSCLIP", pairs_clip)):
            lo, hi = boot_spearman([x for x, _ in pairs], [y for _, y in pairs])
            macros[tag + "LO"] = fmt(lo, 3)
            macros[tag + "HI"] = fmt(hi, 3)
        auto_f = [by_sys_item[h["system"]][h["item_id"]]["failure"] for h in hr
                  if h["item_id"] in by_sys_item.get(h["system"], {})]
        man_f = [h["manual_failure"] for h in hr
                 if h["item_id"] in by_sys_item.get(h["system"], {})]
        macros["HUMACC"] = fmt(np.mean([a == b for a, b in zip(auto_f, man_f)]), 0, pct=True)
        macros["HUMKAPPA"] = fmt(kappa(auto_f, man_f), 2)
    else:
        macros.update({"NHUMAN": "--", "NHUMANRATERS": "--", "NHUMANSYSTEMS": "--",
                       "HUMSCCS": "--", "HUMSCLIP": "--",
                       "HUMSCCSLO": "--", "HUMSCCSHI": "--",
                       "HUMSCLIPLO": "--", "HUMSCLIPHI": "--",
                       "HUMACC": "--", "HUMKAPPA": "--"})

    # second-backbone control (108-item stratified subset, two backbones)
    sec_names = [f"SEC{b}{c}{f}" for b in ("QWEN", "FLUX")
                 for c in ("BASE", "COT", "ORACLE", "SCAF")
                 for f in ("TCS", "DPS", "NPS", "CCS", "CONTRACT")] + ["SECN"]
    sb_path = config.RESULTS / "analysis" / "second_backbone.json"
    cond_of = {"BASE": "base", "COT": "+CoT", "ORACLE": "+Oracle-SCM", "SCAF": "+CausalScaffold"}
    if sb_path.exists():
        sb = json.loads(sb_path.read_text())
        have = {(c["backbone"], c["condition"]): c for c in sb["conditions"]}
        macros["SECN"] = str(sb.get("n_items", "--"))
        for bkey, bname in (("QWEN", "Qwen-Image-Edit"), ("FLUX", "FLUX.1-Kontext")):
            for ckey, cname in cond_of.items():
                row = have.get((bname, cname))
                for fkey in ("TCS", "DPS", "NPS", "CCS", "CONTRACT"):
                    name = f"SEC{bkey}{ckey}{fkey}"
                    if not row:
                        macros[name] = "--"
                    elif fkey == "CONTRACT":
                        macros[name] = fmt(row["contract"], 0, pct=True)
                    else:
                        macros[name] = fmt(row[fkey.lower()], 2)
    else:
        for name in sec_names:
            macros[name] = "--"

    # distribution-level fidelity (Fréchet distance in AlexNet feature space)
    fd_path = config.RESULTS / "analysis" / "fidelity.json"
    if fd_path.exists():
        rows_fd = json.loads(fd_path.read_text())["rows"]
        if rows_fd:
            lo = min(rows_fd, key=lambda r: r["frechet_alexnet"])
            hi = max(rows_fd, key=lambda r: r["frechet_alexnet"])
            macros["FDBEST"] = f"{lo['frechet_alexnet']:,.0f}"
            macros["FDWORST"] = f"{hi['frechet_alexnet']:,.0f}"
    else:
        macros.update({"FDBEST": "--", "FDWORST": "--"})

    # judge agreement
    api = load_probes(str(config.RESULTS / "probes_api_*.jsonl"))

    # quality-probe bands (yes / no / unclear), reported explicitly in the paper
    qua_base = [v for v in api.values()
                if v.get("kind") == "qua" and v.get("system") == "qwen_image_edit"]
    qua_all = [v for v in api.values() if v.get("kind") == "qua"]
    if qua_base:
        nb = len(qua_base)
        for tag, ans in (("QUABASEYES", "yes"), ("QUABASENO", "no"), ("QUAUNCBASE", "unclear")):
            macros[tag] = fmt(sum(1 for v in qua_base if v.get("answer") == ans) / nb, 1, pct=True)
    if qua_all:
        macros["QUAUNCALL"] = fmt(
            sum(1 for v in qua_all if v.get("answer") == "unclear") / len(qua_all), 1, pct=True)
        per = {}
        for v in qua_all:
            per.setdefault(v.get("system"), []).append(v.get("answer") == "yes")
        rates = [sum(x) / len(x) for s, x in per.items() if len(x) >= 100]
        if rates:
            macros["QUAMIN"] = fmt(min(rates), 1, pct=True)
            macros["QUAMAX"] = fmt(max(rates), 1, pct=True)

    # prefer the full local replication over the older stratified subset
    full = sorted((config.RESULTS).glob("probes_local_full_shard*.jsonl"))
    loc = load_probes(str(config.RESULTS / "probes_local_full_shard*.jsonl") if full
                      else str(config.RESULTS / "probes_local_sub*.jsonl"))
    common = sorted(set(api) & set(loc))
    if common:
        a = [api[p]["answer"] for p in common]
        b = [loc[p]["answer"] for p in common]
        macros["JUDGEACC"] = fmt(np.mean([x == y for x, y in zip(a, b)]), 0, pct=True)
        macros["JUDGEKAPPA"] = fmt(kappa(a, b), 2)
        macros["JUDGEN"] = str(len(common))
    else:
        macros.update({"JUDGEACC": "--", "JUDGEKAPPA": "--", "JUDGEN": "--"})

    # full local replication: agreement plus the scores it induces
    rep_path = config.RESULTS / "analysis" / "replication.json"
    if rep_path.exists():
        rep = json.loads(rep_path.read_text())
        macros["LOCALN"] = str(rep["n_shared_probes"])
        macros["LOCALACC"] = fmt(rep["verdict_agreement"], 0, pct=True)
        macros["LOCALKAPPA"] = fmt(rep["verdict_kappa"], 2)
        macros["LOCALRHO"] = fmt(rep["ccs_spearman"], 2)
        macros["LOCALMAXDELTA"] = fmt(rep["ccs_max_abs_delta"], 3)
        macros["LOCALMEANDELTA"] = fmt(rep["ccs_mean_abs_delta"], 3)
        macros["LOCALNO"] = fmt(100 * rep["answer_mix_local"]["no"], 0)
        macros["LOCALUNCLEAR"] = fmt(100 * rep["answer_mix_local"]["unclear"], 0)
        macros["APINO"] = fmt(100 * rep["answer_mix_api"]["no"], 0)
        macros["APIUNCLEAR"] = fmt(100 * rep["answer_mix_api"]["unclear"], 0)
        macros["LOCALNPSACC"] = fmt(100 * rep["agreement_by_kind"]["nps"]["accuracy"], 0)
        macros["LOCALQUAACC"] = fmt(100 * rep["agreement_by_kind"]["qua"]["accuracy"], 0)
        macros["LOCALBEST"] = fmt(100 * rep["best_contract_local"], 0)
        macros["LOCALORACGAP"] = fmt(100 * rep["oracle_contract_fail_local"], 0)
        macros["LOCALTCSDPSGAP"] = fmt(100 * rep["tcs_minus_dps_base_local"], 1)
    else:
        macros.update({"LOCALN": "--", "LOCALACC": "--", "LOCALKAPPA": "--",
                       "LOCALRHO": "--", "LOCALMAXDELTA": "--", "LOCALMEANDELTA": "--",
                       "LOCALNO": "--", "LOCALUNCLEAR": "--", "APINO": "--",
                       "APIUNCLEAR": "--", "LOCALNPSACC": "--", "LOCALQUAACC": "--",
                       "LOCALBEST": "--", "LOCALORACGAP": "--", "LOCALTCSDPSGAP": "--"})

    # counterfactual control
    cf_path = config.RESULTS / "analysis" / "counterfactual.json"
    if cf_path.exists():
        cj = json.loads(cf_path.read_text())
        pool = cj["pooled"]
        pairs = cj["pairs"]
        macros["CFN"] = str(pool["n"])
        macros["CFDISC"] = fmt(100 * pool["discrimination"], 0)
        macros["CFDELTA"] = fmt(pool["ccs_delta"], 3)
        macros["CFSURFACE"] = fmt(100 * pool["surface_compliance"], 0)
        macros["CFCI"] = fmt(100 * pool["ci_cf"], 0)
        macros["CFCIBASE"] = fmt(100 * pool["ci_positive"], 0)
        macros["CFGATEDELTA"] = fmt(min((p["ccs_delta"] for p in pairs.values()),
                                        default=float("nan")), 3)
        macros["CFSYSTEMS"] = str(len(pairs))
        macros["CFSUBN"] = str(pool["n_pos_success"])
        macros["CFSUBCCS"] = fmt(pool["ccs_cf_given_pos_success"])
        macros["CFSUBFAIL"] = fmt(100 * pool["cf_fail_given_pos_success"], 0)
        macros["CFDPSGIVENPOS"] = fmt(pool["dps_given_tcs_positive"])
        macros["CFDPSGIVENCF"] = fmt(pool["dps_given_tcs_cf"])
        for key, tag in (("tcs", "TCS"), ("dps", "DPS"), ("nps", "NPS")):
            macros[f"CF{tag}CF"] = fmt(float(np.mean([p[f"{key}_cf"] for p in
                                                      pairs.values()])))
            macros[f"CF{tag}POS"] = fmt(float(np.mean([p[f"{key}_positive"] for p in
                                                       pairs.values()])))
    else:
        macros.update({"CFN": "--", "CFDISC": "--", "CFDELTA": "--", "CFSURFACE": "--",
                       "CFCI": "--", "CFCIBASE": "--", "CFGATEDELTA": "--",
                       "CFSYSTEMS": "--",
                       "CFSUBN": "--", "CFSUBCCS": "--", "CFSUBFAIL": "--",
                       "CFDPSGIVENPOS": "--", "CFDPSGIVENCF": "--",
                       **{f"CF{t}CF": "--" for t in ("TCS", "DPS", "NPS")},
                       **{f"CF{t}POS": "--" for t in ("TCS", "DPS", "NPS")}})
    # surface control: reasoning items vs their paired surface analogues
    sc_path = config.RESULTS / "analysis" / "surface_compare.json"
    if sc_path.exists():
        sc = json.loads(sc_path.read_text())
        pool = sc["pooled"]
        macros["SURFN"] = str(pool["n"])
        macros["SURFDELTA"] = fmt(pool["delta_ccs"], 3)
        macros["SURFWIN"] = fmt(100 * pool["win_rate"], 0)
        macros["SURFCCSREAS"] = fmt(pool["reasoning_ccs"])
        macros["SURFCCSSURF"] = fmt(pool["surface_ccs"])
        macros["SURFCONREAS"] = fmt(100 * pool["reasoning_contract"], 0)
        macros["SURFCONSURF"] = fmt(100 * pool["surface_contract"], 0)
        for k, tag in (("tcs", "TCS"), ("dps", "DPS"), ("nps", "NPS")):
            macros[f"SURF{tag}REAS"] = fmt(pool["components"][k]["reasoning"])
            macros[f"SURF{tag}SURF"] = fmt(pool["components"][k]["surface"])
        q = sc["pairs"].get("qwen_image_edit")
        if q:
            macros["SURFQWENREAS"] = fmt(q["reasoning"]["ccs"])
            macros["SURFQWENSURF"] = fmt(q["surface"]["ccs"])
            macros["SURFQWENDELTA"] = fmt(q["delta_ccs"], 3)
            macros["SURFQWENCONREAS"] = fmt(100 * q["contract_reasoning"], 0)
            macros["SURFQWENCONSURF"] = fmt(100 * q["contract_surface"], 0)
            macros["SURFQWENWIN"] = fmt(100 * q["win_rate"], 0)
            macros["SURFQWENCI"] = (
                f"[{q['delta_ci'][0]:+.3f}, {q['delta_ci'][1]:+.3f}]"
                if q.get("delta_ci") else "--"
            )
            macros["SURFQWENP"] = (
                "<0.0001" if q.get("delta_p", 1) < 0.0001 else fmt(q["delta_p"], 3)
            ) if q.get("delta_p") is not None else "--"
        p2 = sc["pairs"].get("instructpix2pix")
        if p2:
            macros["SURFCLASSICWIN"] = fmt(100 * p2["win_rate"], 0)
            macros["SURFCLASSICDELTA"] = fmt(p2["delta_ccs"], 3)
            macros["SURFCLASSICCONREAS"] = fmt(100 * p2["contract_reasoning"], 0)
            macros["SURFCLASSICCONSURF"] = fmt(100 * p2["contract_surface"], 0)
            macros["SURFCLASSICCI"] = (
                f"[{p2['delta_ci'][0]:+.3f}, {p2['delta_ci'][1]:+.3f}]"
                if p2.get("delta_ci") else "--"
            )
            macros["SURFCLASSICP"] = (
                "<0.0001" if p2.get("delta_p", 1) < 0.0001 else fmt(p2["delta_p"], 3)
            ) if p2.get("delta_p") is not None else "--"
    else:
        macros.update({k: "--" for k in
                       ("SURFN", "SURFDELTA", "SURFWIN", "SURFCCSREAS", "SURFCCSSURF",
                        "SURFCONREAS", "SURFCONSURF", "SURFQWENREAS", "SURFQWENSURF",
                        "SURFQWENDELTA", "SURFQWENCONREAS", "SURFQWENCONSURF",
                        "SURFQWENWIN", "SURFCLASSICWIN", "SURFCLASSICDELTA",
                        "SURFCLASSICCONREAS", "SURFCLASSICCONSURF",
                        "SURFQWENCI", "SURFQWENP", "SURFCLASSICCI", "SURFCLASSICP")
                       | {f"SURF{t}{side}": "--" for t in ("TCS", "DPS", "NPS")
                          for side in ("REAS", "SURF")}})

    # cross-benchmark: GEdit-Bench's own protocol against the contract
    cb_path = config.RESULTS / "analysis" / "crossbench.json"
    if cb_path.exists():
        cb = json.loads(cb_path.read_text())
        rows = {r["system"]: r for r in cb["rows"]}
        macros["CBN"] = str(max(r["n"] for r in cb["rows"]))
        macros["CBSYSTEMS"] = str(len(cb["rows"]))
        macros["CBRHO"] = fmt(cb["spearman_follows_vs_ccs"], 2)
        macros["CBCLIPRHO"] = fmt(cb["spearman_clip_vs_ccs"], 2)
        macros["CBDINORHO"] = fmt(cb["spearman_dino_vs_ccs"], 2)
        corr = cb.get("correlations", {})
        for key, tag in (("follows", "FOLLOW"), ("clip", "CLIP"),
                         ("dino", "DINO"), ("lpips", "LPIPS")):
            value = corr.get(key, {}).get("exact_permutation_p")
            macros[f"CB{tag}P"] = fmt(value, 3) if value is not None else "--"
        for key, tag in (("qwen_image_edit", "QWEN"), ("instructpix2pix", "CLASSIC"),
                         ("sdxl_inpaint", "SDXL"), ("sd2_inpaint", "SD"),
                         ("sd15_inpaint", "SDONEFIVE"),
                         ("flux_fill", "FLUX")):
            r = rows.get(key)
            if not r:
                continue
            macros[f"CB{tag}FOLLOW"] = fmt(100 * r["follows"], 0)
            macros[f"CB{tag}DINO"] = fmt(r["dino_i"])
            macros[f"CB{tag}CLIP"] = fmt(r["clipscore"], 1)
            macros[f"CB{tag}CCS"] = fmt(r["reason_edit_ccs"], 2)
        if "instructpix2pix" in rows and "sdxl_inpaint" in rows:
            macros["CBGAP"] = fmt(rows["instructpix2pix"]["reason_edit_ccs"]
                                  - rows["sdxl_inpaint"]["reason_edit_ccs"], 2)
    else:
        macros.update({k: "--" for k in
                       ("CBN", "CBSYSTEMS", "CBRHO", "CBCLIPRHO", "CBDINORHO",
                        "CBGAP", "CBFOLLOWP", "CBCLIPP", "CBDINOP", "CBLPIPSP")
                       | {f"CB{t}{s}": "--" for t in ("QWEN", "CLASSIC", "SDXL", "SD", "FLUX")
                          for s in ("FOLLOW", "DINO", "CLIP", "CCS")}})

    # paired comparisons against the base editor: effect size, confidence interval
    # and a Holm correction over the family of eight comparisons reported in the
    # main table
    base_key = "qwen_image_edit"
    if base_key in by_sys_item:
        base_rows = by_sys_item[base_key]
        fam = []
        for s, rs in by_sys_item.items():
            if s == base_key:
                continue
            pairs = [(r["ccs"], base_rows[r["item_id"]]["ccs"])
                     for r in rs.values() if r["item_id"] in base_rows]
            if len(pairs) < 5:
                continue
            a = [p[0] for p in pairs]
            b = [p[1] for p in pairs]
            mean, lo, hi, p = paired_bootstrap(a, b)
            d = np.array(a) - np.array(b)
            sd = float(d.std(ddof=1))
            fam.append([s, mean, lo, hi, p, float(d.mean() / sd) if sd else float("nan")])
        ranked = sorted(range(len(fam)), key=lambda i: fam[i][4])
        running = 0.0
        for rank, i in enumerate(ranked):
            running = max(running, min(1.0, fam[i][4] * (len(fam) - rank)))
            fam[i].append(running)
        tags = {"qwen_image_edit__cot": "COT", "qwen_image_edit__oracle": "ORAC",
                "qwen_image_edit__scaffold_full": "SCAF",
                "instructpix2pix": "CLASSIC", "sdxl_inpaint": "SDXL",
                "flux_fill": "FLUX", "sd15_inpaint": "SDONE", "sd2_inpaint": "SDTWO"}
        for s, mean, lo, hi, p, dz, ph in fam:
            tag = tags.get(s)
            if not tag:
                continue
            macros[f"{tag}CCSDELTA"] = f"{mean:+.3f}"
            macros[f"{tag}CCSLO"] = f"{lo:+.3f}"
            macros[f"{tag}CCSHI"] = f"{hi:+.3f}"
            macros[f"{tag}CCSDZ"] = f"{dz:+.2f}"
            macros[f"{tag}CCSHOLM"] = f"{ph:.3f}" if ph >= 0.001 else "<0.001"

    # framing ablation: the identical probes judged on the full frame instead of the
    # region they are about, so the paper's central protocol claim is measured rather
    # than asserted
    fr_path = config.RESULTS / "analysis" / "framing.json"
    framing_tags = ("FRAMINGN", "FRAMINGRECHECK")
    if fr_path.exists():
        fr = json.loads(fr_path.read_text())
        macros["FRAMINGN"] = str(fr.get("n_whole", 0))
        rc = fr.get("region_recheck") or {}
        macros["FRAMINGRECHECK"] = fmt(100 * rc.get("agreement", float("nan")), 1)
        for key, tag in (("qwen_image_edit", "QWEN"), ("instructpix2pix", "CLASSIC")):
            v = fr.get("systems", {}).get(key)
            if not v:
                continue
            ps = v["probe_stats"]
            macros[f"FRAMING{tag}AGREE"] = fmt(100 * v["verdict_agreement"], 0)
            macros[f"FRAMING{tag}TCSR"] = fmt(ps["tcs"]["value_region"])
            macros[f"FRAMING{tag}TCSW"] = fmt(ps["tcs"]["value_whole"])
            macros[f"FRAMING{tag}DPSR"] = fmt(ps["dps"]["value_region"])
            macros[f"FRAMING{tag}DPSW"] = fmt(ps["dps"]["value_whole"])
            macros[f"FRAMING{tag}UNCR"] = fmt(100 * ps["dps"]["unclear_region"], 1)
            macros[f"FRAMING{tag}UNCW"] = fmt(100 * ps["dps"]["unclear_whole"], 1)
            macros[f"FRAMING{tag}DELTA"] = f"{v['delta_ccs']:+.3f}"
            macros[f"FRAMING{tag}P"] = ("<0.001" if v["delta_p"] < 0.001
                                         else f"{v['delta_p']:.3f}")
        framing_tags = tuple(k for k in macros if k.startswith("FRAMING"))
    else:
        macros.update({k: "--" for k in framing_tags})

    # generation-time variance: several seeds of one strong editor on a subset
    ms_path = config.RESULTS / "analysis" / "multiseed.json"
    ms_keys = ["MSEEDN", "MSEEDCCS", "MSEEDSTD", "MSEEDRANGE",
               "MSEEDITEMSTD", "MSEEDRHO"]
    if ms_path.exists():
        ms = json.loads(ms_path.read_text())
        ccs = ms["summary"]["ccs"]
        macros["MSEEDN"] = str(ms["n_items"])
        macros["MSEEDCCS"] = fmt(ccs["mean"], 3)
        macros["MSEEDSTD"] = fmt(ccs["std_across_seeds"], 3)
        macros["MSEEDRANGE"] = fmt(ccs["range_across_seeds"], 3)
        macros["MSEEDITEMSTD"] = fmt(ccs["mean_item_spread"], 3)
        rho = ms.get("min_pairwise_spearman")
        macros["MSEEDRHO"] = fmt(rho, 2) if rho is not None else "--"
    else:
        macros.update({k: "--" for k in ms_keys})

    # Main-backbone multi-seed validation.  Unlike the historical FLUX noise
    # probe above, this uses all four Qwen conditions on the same 108 items.
    qm_path = config.RESULTS / "analysis" / "qwen_multiseed.json"
    qm_metrics = ("tcs", "dps", "nps", "ccs")
    qm_tags = {"base": "BASE", "cot": "COT", "oracle": "ORACLE",
               "scaffold_full": "SCAFFOLD"}
    qm_keys = ["QMSEEDN", "QMSEEDCOUNT", "QMSEEDFIRST", "QMSEEDLAST"]
    for tag in qm_tags.values():
        qm_keys += [f"QM{tag}{metric.upper()}" for metric in qm_metrics]
        qm_keys += [f"QM{tag}CCSSTD", f"QM{tag}CCSLO", f"QM{tag}CCSHI",
                    f"QM{tag}CONTRACT", f"QM{tag}RHO", f"QM{tag}RHOAVG"]
    qm_keys += ["QMSEEDTAUMIN", "QMSEEDPAIRIDENT", "QMSEEDMAXITEMS",
                "QMSEEDMAXSTD",
                "QMSEEDRHOMIN", "QMSEEDRHOMAX", "QMSEEDRHOMEAN",
                "QMJUDGEACC", "QMJUDGEKAPPA", "QMJUDGEMEANABS",
                "QMJUDGEERRORSD", "QMGENINTERACTIONSD"]
    contrast_specs = (
        ("cot_minus_base", "COTBASE", ("tcs", "dps", "nps", "ccs", "strict_success")),
        ("oracle_minus_base", "ORACLEBASE", ("tcs", "dps", "nps", "ccs", "strict_success")),
        ("scaffold_full_minus_cot", "SCAFFOLDCOT", ("tcs", "dps", "nps", "ccs", "strict_success")),
        ("scaffold_full_minus_base", "SCAFFOLDBASE", ("tcs", "dps", "nps", "ccs", "strict_success")),
    )
    for _, tag, contrast_metrics in contrast_specs:
        for metric in contrast_metrics:
            metric_tag = metric.upper().replace("_", "")
            qm_keys += [f"QM{tag}{metric_tag}DELTA",
                        f"QM{tag}{metric_tag}POS",
                        f"QM{tag}{metric_tag}NEG"]
    if qm_path.exists():
        qm = json.loads(qm_path.read_text())
        qm_seeds = qm["seeds"]
        macros["QMSEEDN"] = str(qm["n_items"])
        macros["QMSEEDCOUNT"] = str(len(qm_seeds))
        macros["QMSEEDFIRST"] = str(min(qm_seeds))
        macros["QMSEEDLAST"] = str(max(qm_seeds))
        for condition, tag in qm_tags.items():
            met = qm["metrics"][condition]
            for metric in qm_metrics:
                macros[f"QM{tag}{metric.upper()}"] = fmt(met[metric]["mean"], 3)
            ccs = met["ccs"]
            macros[f"QM{tag}CCSSTD"] = fmt(ccs["std_across_seeds_population"], 3)
            macros[f"QM{tag}CCSLO"] = fmt(ccs["ci95_item_clustered"][0], 3)
            macros[f"QM{tag}CCSHI"] = fmt(ccs["ci95_item_clustered"][1], 3)
            macros[f"QM{tag}CONTRACT"] = fmt(100 * met["strict_success"]["mean"], 1)
            rhos = [p["spearman"] for p in qm["pairwise_spearman_items"][condition]]
            macros[f"QM{tag}RHO"] = fmt(min(rhos), 2) if rhos else "--"
            macros[f"QM{tag}RHOAVG"] = fmt(float(np.mean(rhos)), 2) if rhos else "--"
        stability = qm["ranking_stability"]
        macros["QMSEEDTAUMIN"] = fmt(stability["minimum_kendall_tau"], 2)
        n_pairs = len(stability["pairwise"])
        n_ident = sum(p["identical_order"] for p in stability["pairwise"])
        macros["QMSEEDPAIRIDENT"] = f"{n_ident}/{n_pairs}"
        all_rhos = [
            p["spearman"]
            for condition in qm_tags
            for p in qm["pairwise_spearman_items"][condition]
        ]
        macros["QMSEEDRHOMIN"] = fmt(min(all_rhos), 2)
        macros["QMSEEDRHOMAX"] = fmt(max(all_rhos), 2)
        macros["QMSEEDRHOMEAN"] = fmt(float(np.mean(all_rhos)), 2)
        spread = max(
            qm["metrics"][condition]["ccs"]["mean_item_spread"]
            for condition in qm_tags
        )
        macros["QMSEEDMAXITEMS"] = fmt(spread, 3)
        macros["QMSEEDMAXSTD"] = fmt(max(
            qm["metrics"][condition]["ccs"]["std_across_seeds_population"]
            for condition in qm_tags
        ), 3)
        pv = qm["judge_repeat"].get("probe_verdicts") or {}
        macros["QMJUDGEACC"] = fmt(100 * pv["exact_agreement"], 1) if "exact_agreement" in pv else "--"
        macros["QMJUDGEKAPPA"] = fmt(pv["cohen_kappa"], 2) if "cohen_kappa" in pv else "--"
        judge_rows = qm["judge_repeat"].get("score_rows") or []
        macros["QMJUDGEMEANABS"] = (
            fmt(float(np.mean([r["mean_abs_delta_ccs"] for r in judge_rows])), 3)
            if judge_rows else "--"
        )
        judge_var = qm["judge_repeat"].get("estimated_judge_error_variance")
        macros["QMJUDGEERRORSD"] = fmt(math.sqrt(judge_var), 3) if judge_var is not None else "--"
        interaction_sd = [
            v["observed_item_x_seed_variance"] ** 0.5
            for v in qm["generation_vs_judge"].values()
        ]
        macros["QMGENINTERACTIONSD"] = fmt(max(interaction_sd), 3)
        for contrast, tag, contrast_metrics in contrast_specs:
            for metric in contrast_metrics:
                result = qm["condition_contrasts"][contrast][metric]
                metric_tag = metric.upper().replace("_", "")
                macros[f"QM{tag}{metric_tag}DELTA"] = (
                    f"{result['mean_delta']:+.3f}"
                )
                macros[f"QM{tag}{metric_tag}POS"] = (
                    f"{result['positive_seeds']}/{len(qm_seeds)}"
                )
                macros[f"QM{tag}{metric_tag}NEG"] = (
                    f"{result['negative_seeds']}/{len(qm_seeds)}"
                )
    else:
        macros.update({k: "--" for k in qm_keys})

    # protocol sensitivity: the same probes re-judged under a tighter / looser crop
    # and a non-zero temperature
    sens_path = config.RESULTS / "analysis" / "sensitivity.json"
    sens_keys = ["SENSTIGHTAGREE", "SENSTIGHTCCS", "SENSTIGHTP",
                 "SENSLOSEAGREE", "SENSLOSECCS", "SENSLOSEP",
                 "SENSTEMPAGREE", "SENSTEMPCCS", "SENSTEMPP", "SENSMAXDELTA"]
    if sens_path.exists():
        sn = json.loads(sens_path.read_text())
        def _q(axis, setting, key):
            return sn["axes"][axis][setting]["qwen_image_edit"][key]
        macros["SENSTIGHTAGREE"] = fmt(100 * _q("pad", "0.0", "agreement"), 0)
        macros["SENSTIGHTCCS"] = f"{_q('pad', '0.0', 'delta_ccs'):+.3f}"
        macros["SENSTIGHTP"] = f"{_q('pad', '0.0', 'p'):.2f}"
        macros["SENSLOSEAGREE"] = fmt(100 * _q("pad", "0.30", "agreement"), 0)
        macros["SENSLOSECCS"] = f"{_q('pad', '0.30', 'delta_ccs'):+.3f}"
        macros["SENSLOSEP"] = f"{_q('pad', '0.30', 'p'):.2f}"
        macros["SENSTEMPAGREE"] = fmt(100 * _q("temp", "0.3", "agreement"), 0)
        macros["SENSTEMPCCS"] = f"{_q('temp', '0.3', 'delta_ccs'):+.3f}"
        macros["SENSTEMPP"] = ("<0.001" if _q("temp", "0.3", "p") < 0.001
                               else f"{_q('temp', '0.3', 'p'):.2f}")
        deltas = [abs(v["delta_ccs"])
                  for axis in sn["axes"].values() for st in axis.values()
                  for v in st.values()]
        macros["SENSMAXDELTA"] = f"{max(deltas):.3f}"
    else:
        macros.update({k: "--" for k in sens_keys})

    # repeat-run stability of the judge: verdicts that change between two judging
    # passes of the same system, and the resulting per-item CCS movement
    repeat = load_probes(str(config.RESULTS / "probes_api_scaffold.jsonl"))
    allp = load_probes(str(config.RESULTS / "probes_api_all.jsonl"))
    shared = sorted(set(repeat) & set(allp))
    if shared:
        flip = np.mean([repeat[p]["answer"] != allp[p]["answer"] for p in shared])
        by_item: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for p in shared:
            if repeat[p]["kind"] == "qua":
                continue
            by_item[repeat[p]["item_id"]].append((repeat[p]["value"], allp[p]["value"]))
        deltas = [abs(np.mean([a for a, _ in v]) - np.mean([b for _, b in v]))
                  for v in by_item.values() if len(v) >= 5]
        macros["JITTER"] = f"{100*flip:.1f}\\%"
        macros["JITTERCCS"] = f"{np.mean(deltas):.3f}"
        macros["JITTERMAX"] = f"{np.percentile(deltas, 95):.2f}"
        macros["JITTERN"] = str(len(deltas))
    else:
        macros.update({"JITTER": "--", "JITTERCCS": "--", "JITTERMAX": "--"})

    lines = ["% generated by reasondata.make_numbers -- do not edit by hand"]
    for k, v in macros.items():
        # TeX control words are letters only: a digit ends the name, so \FOO2BAR is read
        # as \FOO followed by "2BAR" and the definition breaks silently.
        if not k.isalpha():
            raise SystemExit(f"macro name {k!r} is not letters-only; rename it")
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

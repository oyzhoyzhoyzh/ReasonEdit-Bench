"""Agreement between two judges (or between a judge and the human audit)."""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import config
from .bench import read_jsonl


def load_probes(pattern: str) -> dict:
    """Load probe verdicts, keyed by probe id."""
    out = {}
    paths = [Path(p) for p in sorted(glob.glob(pattern))] if "*" in pattern \
        else [Path(pattern)]
    for p in paths:
        if p.exists():
            for r in read_jsonl(p):
                out[r["pid"]] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", default=str(config.RESULTS / "analysis" / "judge_agreement.json"))
    args = ap.parse_args()

    A, B = load_probes(args.a), load_probes(args.b)
    common = sorted(set(A) & set(B))
    agree, both_yes, both_no = 0, 0, 0
    disagree = defaultdict(int)
    by_kind = defaultdict(lambda: [0, 0])
    for pid in common:
        a, b = A[pid]["answer"], B[pid]["answer"]
        by_kind[A[pid]["kind"]][1] += 1
        if a == b:
            agree += 1
            by_kind[A[pid]["kind"]][0] += 1
            both_yes += a == "yes"
            both_no += a == "no"
        else:
            disagree[f"{a}->{b}"] += 1
    n = len(common)
    # Cohen's kappa over the three-way label
    labels = ["yes", "no", "unclear"]
    obs = agree / n if n else float("nan")
    pa = [sum(1 for p in common if A[p]["answer"] == l) / n for l in labels] if n else []
    pb = [sum(1 for p in common if B[p]["answer"] == l) / n for l in labels] if n else []
    pe = sum(x * y for x, y in zip(pa, pb)) if n else float("nan")
    kappa = (obs - pe) / (1 - pe) if n and pe < 1 else float("nan")
    report = {
        "n_common": n, "accuracy": obs, "kappa": kappa,
        "both_yes": both_yes, "both_no": both_no,
        "disagreements": dict(disagree.most_common(10)),
        "by_kind": {k: {"n": v[1], "agree": v[0] / max(1, v[1])}
                    for k, v in by_kind.items()},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

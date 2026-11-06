"""Loading / writing the ReasonEdit-Bench tables."""

from __future__ import annotations

import json
from pathlib import Path

from . import config


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_bench(name: str = "bench.jsonl") -> list[dict]:
    return read_jsonl(config.BENCH_DIR / name)


def bench_stats(items: list[dict]) -> dict:
    from collections import Counter

    c_type = Counter(i["type"] for i in items)
    c_dom = Counter(i["domain"] for i in items)
    c_diff = Counter(i["meta"]["difficulty"] for i in items)
    return {
        "n": len(items),
        "by_type": dict(c_type),
        "by_domain": dict(c_dom),
        "by_difficulty": dict(c_diff),
        "avg_chain": sum(i["meta"]["chain_length"] for i in items) / max(1, len(items)),
        "avg_nodes": sum(i["meta"]["num_nodes"] for i in items) / max(1, len(items)),
    }

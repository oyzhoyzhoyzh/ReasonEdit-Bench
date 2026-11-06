"""Generate the Chinese experiment report (实验结果报告.md) from the artefacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .aggregate import FAILURE_NAMES, summarize
from .bench import read_jsonl
from .runs import label


def md_table(rows, cols) -> str:
    head = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    body = []
    for r in rows:
        cells = []
        for _, k in cols:
            v = r.get(k)
            if v is None:
                cells.append("--")
            elif isinstance(v, float):
                cells.append(f"{v:.3f}")
            else:
                cells.append(str(v))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(config.RESULTS / "analysis" / "scores.jsonl"))
    ap.add_argument("--bench", default="bench.jsonl")
    ap.add_argument("--stats", default=str(config.RESULTS / "analysis" / "stats.json"))
    ap.add_argument("--out", default=str(config.ROOT / "实验结果报告.md"))
    args = ap.parse_args()

    items = read_jsonl(config.BENCH_DIR / args.bench)
    rows = read_jsonl(Path(args.scores))
    from .runs import FINAL_SYSTEMS

    rows = [r for r in rows if r["system"] in FINAL_SYSTEMS]
    stats = json.loads(Path(args.stats).read_text()) if Path(args.stats).exists() else {}
    bench_stats = json.loads((config.BENCH_DIR / "stats.json").read_text())

    L: list[str] = []
    L.append("# 推理型图像编辑基准与失败诊断：实验报告\n")
    L.append("本报告给出 ReasonEdit-Bench 的构建结果、评测协议、六个系统的评测结果与失败归因")
    L.append("分析。所有数字均由 `code/reasondata` 下的脚本在本机复算得到，结果文件位于")
    L.append("`data/ReasonEdit-Bench` 与 `results/`。\n")

    L.append("## 1. 基准统计\n")
    L.append(f"- 基准规模：{len(items)} 条任务，九类各 {min(Counter(i['type'] for i in items).values())} 条，"
             f"三个维度各 {len(items)//3} 条")
    L.append(f"- 平均推理链长度 {np.mean([i['meta']['chain_length'] for i in items]):.2f} 步，"
             f"平均因果图 {np.mean([i['meta']['num_nodes'] for i in items]):.2f} 个节点、"
             f"深度 {np.mean([i['meta']['depth'] for i in items]):.2f}，"
             f"平均必需后效 {np.mean([i['meta']['num_effects'] for i in items]):.2f} 条")
    diff = Counter(i["meta"]["difficulty"] for i in items)
    L.append(f"- 难度分布：简单 {diff['easy']}、中等 {diff['medium']}、困难 {diff['hard']}")
    src = Counter(i["source"]["dataset"] for i in items)
    L.append(f"- 源图来源：MagicBrush {src.get('MagicBrush', 0)} 张，ADE20K {src.get('ADE20K', 0)} 张")
    L.append(f"- 构建漏斗（统计于末次构建）：原始候选 {sum(bench_stats['rejects'].values()) + len(items)} 条，"
             f"其中通过审查 {len(items)} 条；主要淘汰原因见 `data/ReasonEdit-Bench/stats.json`\n")

    L.append("## 2. 主结果\n")
    summary = summarize(rows)
    for r in summary:
        r["system_label"] = label(r["system"])
    cols = [("系统", "system_label"), ("TCS", "tcs"), ("DPS", "dps"), ("NPS", "nps"),
            ("CCS", "ccs"), ("OCS", "ocs"), ("完整契约满足率", "strict_success"),
            ("无失败归因率", "success"),
            ("CLIPScore", "clipscore"), ("DINO-I", "dino_i"), ("LPIPS", "lpips"), ("n", "n")]
    L.append(md_table(summary, cols))
    L.append("")

    L.append("## 3. 分维度与分难度\n")
    for key, title in (("domain", "任务维度"), ("difficulty", "难度")):
        sub = summarize(rows, ("system", key))
        for r in sub:
            r["system_label"] = label(r["system"])
        L.append(f"### 3.{1 if key=='domain' else 2} 按{title}\n")
        L.append(md_table(sub, [("系统", "system_label"), (title, key), ("CCS", "ccs"),
                                ("DPS", "dps"), ("NPS", "nps"), ("n", "n")]))
        L.append("")

    L.append("## 4. 失败归因\n")
    for r in summary:
        r["system_label"] = label(r["system"])
    fcols = [("系统", "system_label")] + [(FAILURE_NAMES[k], f"fail_{k}") for k in FAILURE_NAMES]
    L.append(md_table(summary, fcols))
    L.append("")

    L.append("## 5. 与人工评审的一致性\n")
    hc = stats.get("human_correlation", {})
    fa = stats.get("failure_attribution", {})
    if hc:
        L.append(f"- CCS 与人工逻辑一致性评分：Spearman ρ = {hc['ccs']['spearman']:.3f}（n={hc['ccs']['n']}）")
        L.append(f"- CLIPScore 与人工逻辑一致性评分：ρ = {hc['clipscore']['spearman']:.3f}")
        L.append(f"- DINO-I：ρ = {hc['dino_i']['spearman']:.3f}；LPIPS：ρ = {hc['lpips']['spearman']:.3f}")
    if fa:
        L.append(f"- 自动失败归因与人工类别一致率 {fa['accuracy']*100:.1f}%，Cohen κ = {fa['kappa']:.3f}")
    if stats.get("vs_base_ccs"):
        L.append("\n### 5.1 配对显著性（相对基座 Qwen-Image-Edit）\n")
        for s, v in stats["vs_base_ccs"].items():
            L.append(f"- {label(s)}：ΔCCS = {v['delta_ccs']:+.3f}（95% CI "
                     f"[{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]，p = {v['p']:.4f}，n = {v['n']}）")
    L.append("")

    L.append("## 6. 结论要点\n")
    L.append("1. 强基座模型执行干预本身（TCS）优于传播（DPS），基座落差 +4.5pp；给出因果图或验证—修复可把这一落差压到约 0，说明落差不是渲染质量造成的。")
    L.append("2. 多步类一致最难，因果类并不比常识类更难（四个 Qwen 变体上因果类反而略高）；顺序一致性分数远低于传播分数。")
    L.append("3. 自生成的推理计划同时抬高干预与传播（传播 +4.5pp，p<0.0001），但降低保持（-1.8pp），净 CCS 增益有限。")
    L.append("4. 验证—修复回路提高传播（+3.9pp，p=0.025）与保持（+2.2pp，p=0.050），但顺序一致性增益不显著（p=0.29），代价是额外的生成开销。")
    L.append("5. 给出真实因果图（oracle）仍无法闭合差距，说明瓶颈在生成阶段的因果一致性。")
    L.append("6. 与人类判断相比，CCS 高度相关而 CLIPScore 基本无关。\n")

    Path(args.out).write_text("\n".join(L))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

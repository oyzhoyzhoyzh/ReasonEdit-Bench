#!/usr/bin/env bash
# Third phase: verification-driven repair, assembly and re-judging.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs

echo "building repair requests"
python3 -u -m reasondata.repair --system qwen_image_edit__cot \
    --source-run ${RIE_ROOT}/results/qwen_image_edit/cot \
    --out ${RIE_ROOT}/results/qwen_image_edit/scaffold_requests.jsonl \
    > "$LOG/repair_build.log" 2>&1
cat "$LOG/repair_build.log"

echo "running repair pass on GPU 1"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant scaffold --gpu 1 \
    --plan ${RIE_ROOT}/results/qwen_image_edit/scaffold_requests.jsonl \
    > "$LOG/gen_qwen_repair.log" 2>&1

echo "assembling scaffold system"
python3 -u -m reasondata.assemble > "$LOG/assemble.log" 2>&1
cat "$LOG/assemble.log"

echo "judging the repaired subset"
python3 -u -m reasondata.judge_run --gpu 0 --shard 0/1 --backend local \
    --runs qwen_image_edit__scaffold_full \
    --out ${RIE_ROOT}/results/probes_local_scaffold.jsonl > "$LOG/judge_scaffold.log" 2>&1
echo "scaffold phase finished"

#!/usr/bin/env bash
# Region-grounded probing of every generated image, sharded over both GPUs.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs

python3 -u -m reasondata.judge_run --gpu 0 --shard 0/2 --backend local \
    --out ${RIE_ROOT}/results/probes_local_shard0of2.jsonl > "$LOG/judge0.log" 2>&1 &
P0=$!
python3 -u -m reasondata.judge_run --gpu 1 --shard 1/2 --backend local \
    --out ${RIE_ROOT}/results/probes_local_shard1of2.jsonl > "$LOG/judge1.log" 2>&1 &
P1=$!
wait $P0 $P1
echo "judging finished"

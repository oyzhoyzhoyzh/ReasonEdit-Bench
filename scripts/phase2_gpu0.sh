#!/usr/bin/env bash
# GPU 0 queue: wait for the running base generation, then run the oracle-SCM
# upper bound, then refresh the API judge.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd ${RIE_ROOT}/code || exit 1
LOG=${RIE_ROOT}/logs

echo "[gpu0] waiting for the running generation to finish"
while pgrep -f "reasondata.run_edit --model qwen_image_edit --variant base --gpu 0" > /dev/null; do
    sleep 60
done

echo "[gpu0] Qwen-Image-Edit oracle-SCM (shard 0/2)"
python3 -u -m reasondata.run_edit --model qwen_image_edit --variant oracle --gpu 0 \
    --shard 0/2 --out ${RIE_ROOT}/results/qwen_image_edit/oracle_p0 \
    > "$LOG/gen_qwen_oracle0.log" 2>&1

echo "[gpu0] refreshing the API judge"
python3 -u -m reasondata.judge_run --backend dashscope --model qwen3-vl-plus --shard 0/1 \
    --workers 16 --out ${RIE_ROOT}/results/probes_api_all.jsonl \
    > "$LOG/judge_api2.log" 2>&1

echo "[gpu0] offline replication judge on a stratified subset"
python3 -u -m reasondata.judge_run --backend local --gpu 0 --shard 0/1 \
    --sample-per-system 60 \
    --out ${RIE_ROOT}/results/probes_local_sub.jsonl > "$LOG/judge_sub.log" 2>&1
echo "[gpu0] finished"

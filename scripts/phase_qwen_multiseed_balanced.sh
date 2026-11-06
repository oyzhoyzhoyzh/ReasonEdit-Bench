#!/usr/bin/env bash
# Balanced eight-GPU first pass for the Qwen main-backbone multi-seed study.
set -uo pipefail
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

ROOT="${RIE_ROOT:-${RIE_ROOT}}"
PY="${PYTHON:-python3}"
MODEL="${RIE_QWEN_IMAGE_EDIT_MODEL:-${RIE_QWEN_EDIT_BF16:-${RIE_HF_CACHE:-$HOME/.cache/huggingface}/Qwen/Qwen-Image-Edit-2509-4bit}}"
LOG="$ROOT/logs/qwen_multiseed_b"
mkdir -p "$LOG"

export RIE_ROOT="$ROOT"
export RIE_QWEN_IMAGE_EDIT_MODEL="$MODEL"
export PYTHONPATH="$ROOT/code"

pids=()
for gpu in $(seq 0 7); do
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" -u -m reasondata.run_multiseed_shard \
    --gpu 0 --shard "${gpu}/8" --pairs-file "$ROOT/results/pairs108.txt" \
    --seeds 20260924,20260925,20260926 --variants base,cot,oracle \
    > "$LOG/balanced_gpu${gpu}.log" 2>&1 &
  pids+=("$!")
done

rc=0
for pid in "${pids[@]}"; do
  wait "$pid" || rc=1
done

"$PY" -m reasondata.run_multiseed_shard --gpu 0 --merge \
  --seeds 20260924,20260925,20260926 --variants base,cot,oracle \
  >> "$LOG/merge_first_pass.log" 2>&1
exit "$rc"

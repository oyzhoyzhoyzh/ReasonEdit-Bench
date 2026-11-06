#!/usr/bin/env bash
# Qwen-Image-Edit main-backbone multi-seed validation, first pass.
#
# Runs base, CoT and Oracle-SCM for three seeds over the fixed stratified
# 108-item subset.  Each GPU owns one model instance and processes a queue.
set -uo pipefail
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

ROOT="${RIE_ROOT:-${RIE_ROOT}}"
PY="${PYTHON:-python3}"
MODEL="${RIE_QWEN_IMAGE_EDIT_MODEL:-${RIE_QWEN_EDIT_BF16:-${RIE_HF_CACHE:-$HOME/.cache/huggingface}/Qwen/Qwen-Image-Edit-2509-4bit}}"
SEEDS=(20260924 20260925 20260926)
PAIRS="$(cat "$ROOT/results/pairs108.txt")"
LOG="$ROOT/logs/qwen_multiseed_b"
mkdir -p "$LOG"

export RIE_ROOT="$ROOT"
export RIE_QWEN_IMAGE_EDIT_MODEL="$MODEL"
export PYTHONPATH="$ROOT/code"

run_one() {
  local gpu="$1" seed="$2" variant="$3"
  local out="$ROOT/results/qwen_multiseed_s${seed}/${variant}"
  echo "[gpu $gpu] start seed=$seed variant=$variant $(date -Is)"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" -u -m reasondata.run_edit \
    --model qwen_image_edit --variant "$variant" --gpu 0 \
    --seed "$seed" --pairs "$PAIRS" --bf16 --out "$out" \
    >> "$LOG/s${seed}_${variant}.log" 2>&1
  local rc=$?
  echo "[gpu $gpu] done seed=$seed variant=$variant rc=$rc $(date -Is)"
  return "$rc"
}

run_queue() {
  local gpu="$1"
  shift
  local spec seed variant
  for spec in "$@"; do
    seed="${spec%%:*}"
    variant="${spec#*:}"
    run_one "$gpu" "$seed" "$variant" || return $?
  done
}

# Nine jobs on eight GPUs.  The tenth slot (GPU 0) handles the ninth job after
# its first job, keeping exactly one full model resident per card.
run_queue 0 "20260924:base" "20260926:oracle" & p0=$!
run_queue 1 "20260924:cot" & p1=$!
run_queue 2 "20260924:oracle" & p2=$!
run_queue 3 "20260925:base" & p3=$!
run_queue 4 "20260925:cot" & p4=$!
run_queue 5 "20260925:oracle" & p5=$!
run_queue 6 "20260926:base" & p6=$!
run_queue 7 "20260926:cot" & p7=$!

rc=0
for pid in "$p0" "$p1" "$p2" "$p3" "$p4" "$p5" "$p6" "$p7"; do
  wait "$pid" || rc=1
done
exit "$rc"

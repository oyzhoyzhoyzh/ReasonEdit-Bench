#!/usr/bin/env bash
# Second-backbone control (Review Report M1): rerun the reasoning-augmented
# configurations on FLUX.1-Kontext over the 108-item stratified subset, so the
# separation claim can be checked on a backbone other than Qwen-Image-Edit.
#
#   bash scripts/phase9_second_backbone.sh oracle cot
#
# Outputs land in results/flux_kontext_2nd/<variant>/ and are deliberately kept
# out of results/flux_kontext/ so that the main-table aggregates ignore them.
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT="${RIE_ROOT:-${RIE_ROOT}}"
export RIE_ROOT="$ROOT"
export PYTHONPATH="$ROOT/code"
MODEL="${MODEL:-flux_kontext}"
PAIRS_FILE="${PAIRS_FILE:-$ROOT/results/pairs108.txt}"
PAIRS=$(cat "$PAIRS_FILE")
GPUS=(${GPUS:-0 3 4 5 6 7})
COT_PLAN="$ROOT/results/flux_kontext_2nd_cot_prompts.jsonl"
LOG="$ROOT/logs"

run_variant () {  # $1 = variant, $2.. = gpus
  local variant="$1"; shift
  local gpus=("$@")
  local out="$ROOT/results/flux_kontext_2nd/${variant}"
  local n=${#gpus[@]}
  mkdir -p "$out"
  for k in $(seq 0 $((n - 1))); do
    local extra=""
    if [ "$variant" = "cot" ]; then extra="--plan $COT_PLAN"; fi
    CUDA_VISIBLE_DEVICES="${gpus[$k]}" python -m reasondata.run_edit \
      --model "$MODEL" --variant "$variant" --gpu 0 --shard "${k}/${n}" \
      --pairs "$PAIRS" --bf16 $extra --out "$out" \
      > "$LOG/2nd_${variant}_${k}.log" 2>&1 &
  done
  wait
  echo "$variant done -> $out ($(ls "$out" | wc -l) files)"
}

for v in "$@"; do
  case "$v" in
    oracle) run_variant oracle "${GPUS[@]::3}" ;;
    cot)    run_variant cot    "${GPUS[@]:3:3}" ;;
    *) echo "unknown variant $v" ;;
  esac
done

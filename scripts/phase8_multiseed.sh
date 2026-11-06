#!/usr/bin/env bash
# Generation-time variance: one strong editor, several seeds, one stratified subset.
#
# The main table generates every item once per system, so the paper can only bound
# judge noise (repeat-run jitter) and not generation noise.  This driver generates a
# stratified subset with three different seeds, so the spread of the causal scores
# across seeds can be reported alongside the judge-noise bound.
#
#   bash scripts/phase8_multiseed.sh flux_kontext 1 2 3
#
# Environment: RIE_ROOT (project root), RIE_HF_CACHE (checkpoint root), NPER (items
# per task type, default 12 -> 108 items).
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT="${RIE_ROOT:-${RIE_ROOT}}"
export RIE_ROOT="$ROOT"
export PYTHONPATH="$ROOT/code"
MODEL="${1:-flux_kontext}"
shift || true
SEEDS=("$@")
[ ${#SEEDS[@]} -eq 0 ] && SEEDS=(1 2 3)
NPER="${NPER:-12}"
NPROC="${NPROC:-8}"

PAIRS=$(python - "$ROOT" "$NPER" <<'PY'
import collections, json, sys
root, nper = sys.argv[1], int(sys.argv[2])
sel = collections.defaultdict(list)
for line in open(f"{root}/data/ReasonEdit-Bench/bench.jsonl"):
    if line.strip():
        it = json.loads(line)
        sel[it["type"]].append(it["id"])
ids = []
for t in sorted(sel):
    ids += sorted(sel[t])[:nper]
print(",".join(ids))
PY
)
echo "model=$MODEL seeds=${SEEDS[*]} pairs=$(echo "$PAIRS" | tr ',' '\n' | wc -l) procs=$NPROC"

for SEED in "${SEEDS[@]}"; do
  OUT="$ROOT/results/${MODEL}_s${SEED}/base"
  mkdir -p "$OUT"
  for k in $(seq 0 $((NPROC - 1))); do
    CUDA_VISIBLE_DEVICES="$k" python -m reasondata.run_edit \
      --model "$MODEL" --variant base --gpu 0 --shard "${k}/${NPROC}" \
      --seed "$SEED" --pairs "$PAIRS" --bf16 --out "$OUT" \
      > "$ROOT/logs/multiseed_${MODEL}_s${SEED}_${k}.log" 2>&1 &
  done
  wait
  echo "seed $SEED done -> $OUT"
done

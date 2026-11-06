#!/usr/bin/env bash
# Re-judge the complete benchmark with the open-weight local judge and compare it
# with the API judge used for the paper's main numbers.
#
#   bash scripts/phase4_rejudge_local.sh
#
# Produces:
#   results/probes_local_full_shard{0,1}of2.jsonl   local verdicts (resumable)
#   results/analysis_local/                         scores under the local judge
#   results/analysis/replication.json               agreement + score comparison
#   paper/tables/replication_table.tex              the paper's table
#
# Both GPUs run one shard each.  `--batch-size 8` judges the ~7 probes of an item in
# one forward pass; it is a throughput knob only and reproduces the sequential
# verdicts exactly (~4.5x faster on an RTX 5090).
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$(dirname "$0")/../code" || exit 1
ROOT=${RIE_ROOT}
LOG="$ROOT/logs"
R="$ROOT/results"
SYSTEMS="instructpix2pix,sdxl_inpaint,qwen_image_edit,qwen_image_edit__cot,qwen_image_edit__oracle,qwen_image_edit__scaffold_full"

for gpu in 0 1; do
    python3 -u -m reasondata.judge_run --gpu "$gpu" --shard "$gpu/2" --runs "$SYSTEMS" \
        --backend local --batch-size 8 \
        --out "$R/probes_local_full_shard${gpu}of2.jsonl" \
        > "$LOG/judge_local_full${gpu}.log" 2>&1 &
done
wait

python3 -u -m reasondata.aggregate --probe-pattern "$R/probes_local_full_shard*.jsonl" \
    --out "$R/analysis_local" > /dev/null

python3 -u -m reasondata.replication \
    --api "$R/probes_api_*.jsonl" \
    --local "$R/probes_local_full_shard*.jsonl" \
    --api-summary "$R/analysis/summary.json" \
    --local-summary "$R/analysis_local/summary.json" \
    --out "$R/analysis/replication.json" \
    --table "$ROOT/paper/tables/replication_table.tex"

python3 -u -m reasondata.make_numbers --scores "$R/analysis/scores.jsonl" > /dev/null
echo "re-judged locally; numbers.tex and the replication table refreshed"

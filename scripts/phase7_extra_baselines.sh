#!/usr/bin/env bash
# Add three more backbones (SD1.5-Inpaint, SD2-Inpaint, FLUX.1-Fill) and judge them
# with both judges, so the main table and the replication stay on one judge each.
#
#   bash scripts/phase7_extra_baselines.sh
#
# Produces:
#   results/{sd15_inpaint,sd2_inpaint,flux_fill}/base/   edits
#   results/probes_api_new.jsonl                         API judge (main table)
#   results/probes_local_full_shard{0,1}of2.jsonl        local judge (replication, appended)
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT=${RIE_ROOT}
R="$ROOT/results"
LOG="$ROOT/logs"

# FLUX.1-Fill is run 4-bit; shard it over both cards via CUDA_VISIBLE_DEVICES because a
# 4-bit pipeline ignores the device argument and would otherwise land on cuda:0 twice.
(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=0 setsid nohup \
    python3 -u -m reasondata.run_edit --model flux_fill --variant base --gpu 0 --shard 0/2 \
    > "$LOG/gen_fluxfill0.log" 2>&1 < /dev/null &)
(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=1 setsid nohup \
    python3 -u -m reasondata.run_edit --model flux_fill --variant base --gpu 0 --shard 1/2 \
    > "$LOG/gen_fluxfill1.log" 2>&1 < /dev/null &)
while pgrep -f "run_edit --model flux_fill" > /dev/null; do sleep 30; done

(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=0 setsid nohup \
    python3 -u -m reasondata.run_edit --model sd15_inpaint --variant base --gpu 0 \
    > "$LOG/gen_sd15.log" 2>&1 < /dev/null &)
(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=1 setsid nohup \
    python3 -u -m reasondata.run_edit --model sd2_inpaint --variant base --gpu 0 \
    > "$LOG/gen_sd2.log" 2>&1 < /dev/null &)
while pgrep -f "run_edit --model sd._inpaint" > /dev/null; do sleep 30; done

# reference metrics
(cd "$ROOT/code" && python3 -u -m reasondata.run_auto --gpu 0 --out "$R/auto_metrics.jsonl" \
    > "$LOG/auto_extra.log" 2>&1)

# API judge (CPU/network only) and local judge (one shard per card) run concurrently
(cd "$ROOT/code" && setsid nohup python3 -u -m reasondata.judge_run --backend dashscope \
    --model qwen3-vl-plus --workers 16 --runs flux_fill,sd15_inpaint,sd2_inpaint \
    --out "$R/probes_api_new.jsonl" > "$LOG/judge_api_new.log" 2>&1 < /dev/null &)
for gpu in 0 1; do
    (cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=$gpu setsid nohup \
        python3 -u -m reasondata.judge_run --gpu 0 --shard "$gpu/2" \
        --runs flux_fill,sd15_inpaint,sd2_inpaint --backend local --batch-size 8 \
        --out "$R/probes_local_full_shard${gpu}of2.jsonl" \
        > "$LOG/judge_local_new${gpu}.log" 2>&1 < /dev/null &)
done
while pgrep -f "judge_run --gpu 0 --shard" > /dev/null; do sleep 30; done
while pgrep -f "judge_run --backend dashscope" > /dev/null; do sleep 30; done

# re-score everything and refresh the paper artefacts
cd "$ROOT/code" || exit 1
python3 -u -m reasondata.aggregate --probe-pattern "$R/probes_api_*.jsonl" \
    --out "$R/analysis" > /dev/null
python3 -u -m reasondata.stats --scores "$R/analysis/scores.jsonl" \
    --human "$R/human_eval/ratings.jsonl" --out "$R/analysis" > /dev/null
python3 -u -m reasondata.figures --scores "$R/analysis/scores.jsonl" \
    --human "$R/human_eval/ratings.jsonl" --out "$R/figures" > /dev/null
python3 -u -m reasondata.export_tables --scores "$R/analysis/scores.jsonl" \
    --out "$ROOT/paper/tables" > /dev/null
python3 -u -m reasondata.aggregate --probe-pattern "$R/probes_local_full_shard*.jsonl" \
    --out "$R/analysis_local" > /dev/null
python3 -u -m reasondata.replication --api "$R/probes_api_*.jsonl" \
    --local "$R/probes_local_full_shard*.jsonl" \
    --api-summary "$R/analysis/summary.json" --local-summary "$R/analysis_local/summary.json" \
    --out "$R/analysis/replication.json" --table "$ROOT/paper/tables/replication_table.tex"
python3 -u -m reasondata.make_numbers --scores "$R/analysis/scores.jsonl" > /dev/null
python3 -u -m reasondata.make_report --scores "$R/analysis/scores.jsonl" \
    --stats "$R/analysis/stats.json" > /dev/null
echo "extra baselines finished; tables, figures and numbers refreshed"

#!/usr/bin/env bash
# Surface-edit control: build one surface analogue per reasoning item (same photograph,
# same target object, same preserved propositions), edit it with the same systems, and
# measure the reasoning-versus-surface gap.
#
#   bash scripts/phase6_surface_control.sh
#
# Produces:
#   data/ReasonEdit-Bench/surface.jsonl            the control subset
#   results/<model>/surface/                       surface edits
#   results/probes_surface_shard{0,1}of2.jsonl     local verdicts (resumable)
#   results/analysis_surface/                      scores under the local judge
#   results/analysis/surface_compare.json          the paired gap
#   paper/tables/surface_table.tex                 the paper's table
set -u
RIE_ROOT="${RIE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT=${RIE_ROOT}
LOG="$ROOT/logs"
R="$ROOT/results"

# 1. draft + adversarially review the control items (API, cached to JSONL)
(cd "$ROOT/code" && python3 -u -m reasondata.surface --workers 12 --out surface.jsonl \
    > "$LOG/surface_build.log" 2>&1)

# 2. edit them with two systems; one Qwen shard per GPU (the 4-bit pipeline ignores the
#    device argument, so CUDA_VISIBLE_DEVICES is what actually selects the card)
for gpu in 0 1; do
    (cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=$gpu setsid nohup \
        python3 -u -m reasondata.run_edit --model qwen_image_edit --variant surface \
        --bench surface.jsonl --gpu 0 --shard "$gpu/2" \
        > "$LOG/gen_qwen_surface${gpu}.log" 2>&1 < /dev/null &)
done
(cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=1 setsid nohup \
    python3 -u -m reasondata.run_edit --model instructpix2pix --variant surface \
    --bench surface.jsonl --gpu 0 > "$LOG/gen_ip2p_surface.log" 2>&1 < /dev/null &)
while pgrep -f "run_edit --model qwen_image_edit --variant surface" > /dev/null; do
    sleep 60
done

# 3. reference metrics, then local judging (one shard per GPU)
(cd "$ROOT/code" && python3 -u -m reasondata.run_auto --gpu 0 --bench surface.jsonl \
    --out "$R/auto_metrics.jsonl" >> "$LOG/auto_surface.log" 2>&1)
for gpu in 0 1; do
    (cd "$ROOT/code" && CUDA_VISIBLE_DEVICES=$gpu setsid nohup \
        python3 -u -m reasondata.judge_run --gpu 0 --shard "$gpu/2" --bench surface.jsonl \
        --runs qwen_image_edit__surface,instructpix2pix__surface --backend local \
        --batch-size 8 --out "$R/probes_surface_shard${gpu}of2.jsonl" \
        > "$LOG/judge_surface${gpu}.log" 2>&1 < /dev/null &)
done
while pgrep -f "judge_run --gpu 0 --shard" > /dev/null; do sleep 30; done

# 4. score and compare against the reasoning items (local judge on both sides)
cd "$ROOT/code" || exit 1
python3 -u -m reasondata.aggregate --bench surface.jsonl \
    --probe-pattern "$R/probes_surface_shard*.jsonl" \
    --systems qwen_image_edit__surface,instructpix2pix__surface \
    --out "$R/analysis_surface" > /dev/null
python3 -u -m reasondata.surface_compare \
    --reasoning "$R/analysis_local/scores.jsonl" --surface "$R/analysis_surface/scores.jsonl" \
    --out "$R/analysis/surface_compare.json" \
    --table "$ROOT/paper/tables/surface_table.tex"
python3 -u -m reasondata.make_numbers --scores "$R/analysis/scores.jsonl" > /dev/null
echo "surface control finished; numbers.tex and the table refreshed"
